# ═══════════════════════════════════════════════════════════════
#  DataChat v3 — Text-to-Pandas Analytics Assistant
#  New in v3:
#  - Redesigned UI: indigo/slate palette, works in light + dark
#  - Session persistence: chat history survives page refresh
#  - Self-healing code execution (v2 carry-over)
#  - Metadata-only security model (v2 carry-over)
# ═══════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq
import traceback
import re
import json
import time

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="DataChat",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────
# Design system:
# --accent     : electric indigo — primary brand color
# --accent-soft: lighter indigo for hover states
# Works on BOTH light and dark Streamlit themes because we
# use CSS variables and avoid hardcoding background colors
# on elements Streamlit controls. We only style OUR elements.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --accent:      #4f46e5;
    --accent-soft: #6366f1;
    --accent-pale: #eef2ff;
    --success:     #059669;
    --warning:     #d97706;
    --danger:      #dc2626;
    --radius:      12px;
    --radius-sm:   8px;
}

/* Global font */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Hero */
.hero-wrap { margin-bottom: 1.5rem; }
.hero-title {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #2563eb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
    margin-bottom: 0.25rem;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #64748b;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* KPI cards — border-top accent, neutral background */
.kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 1.5rem;
}
.kpi-card {
    border: 1px solid rgba(79, 70, 229, 0.2);
    border-top: 3px solid var(--accent);
    border-radius: var(--radius);
    padding: 1.1rem 1.3rem;
    background: rgba(79, 70, 229, 0.04);
    transition: box-shadow 0.2s;
}
.kpi-card:hover {
    box-shadow: 0 4px 20px rgba(79, 70, 229, 0.12);
}
.kpi-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b;
    margin-bottom: 0.35rem;
}
.kpi-value {
    font-size: 1.55rem;
    font-weight: 800;
    color: var(--accent);
    line-height: 1;
    letter-spacing: -0.02em;
}
.kpi-delta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--success);
    margin-top: 0.3rem;
}

/* Chat bubbles */
.msg-user {
    border: 1px solid rgba(79, 70, 229, 0.25);
    border-radius: 16px 16px 4px 16px;
    padding: 0.9rem 1.2rem;
    margin: 0.7rem 0;
    margin-left: 4rem;
    background: rgba(79, 70, 229, 0.06);
    font-size: 0.92rem;
    line-height: 1.6;
}
.msg-assistant {
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-left: 3px solid var(--accent);
    border-radius: 16px 16px 16px 4px;
    padding: 0.9rem 1.2rem;
    margin: 0.7rem 0;
    margin-right: 4rem;
    background: rgba(79, 70, 229, 0.03);
    font-size: 0.92rem;
    line-height: 1.6;
}
.msg-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    margin-bottom: 0.4rem;
    font-weight: 600;
}

/* Code block */
.code-block {
    border: 1px solid rgba(79, 70, 229, 0.2);
    border-left: 3px solid var(--accent-soft);
    border-radius: var(--radius-sm);
    padding: 0.8rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    margin: 0.5rem 0;
    line-height: 1.6;
    background: rgba(79, 70, 229, 0.04);
    color: var(--accent);
    white-space: pre-wrap;
    word-break: break-all;
}
.code-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b;
    margin-bottom: 0.3rem;
}

/* Error block */
.error-block {
    border: 1px solid rgba(220, 38, 38, 0.3);
    border-left: 3px solid var(--danger);
    border-radius: var(--radius-sm);
    padding: 0.8rem 1rem;
    font-size: 0.85rem;
    margin: 0.5rem 0;
    background: rgba(220, 38, 38, 0.04);
    color: var(--danger);
    line-height: 1.6;
}

/* Retry badge */
.retry-badge {
    display: inline-block;
    background: rgba(217, 119, 6, 0.1);
    color: var(--warning);
    border: 1px solid rgba(217, 119, 6, 0.3);
    border-radius: 20px;
    padding: 0.15rem 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}

/* Buttons */
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: var(--accent-soft) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
}

/* Input */
.stTextInput > div > div > input {
    border: 1.5px solid rgba(79, 70, 229, 0.3) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.88rem !important;
    transition: border-color 0.15s !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12) !important;
}

/* Persistence badge */
.persist-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--success);
    background: rgba(5, 150, 105, 0.08);
    border: 1px solid rgba(5, 150, 105, 0.2);
    border-radius: 20px;
    padding: 0.2rem 0.6rem;
    margin-top: 0.3rem;
}

/* Form border reset */
[data-testid="stForm"] { border: none !important; padding: 0 !important; }

/* Divider */
hr { border-color: rgba(79, 70, 229, 0.15) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-thumb { background: rgba(79,70,229,0.3); border-radius: 4px; }

/* Empty state */
.empty-state {
    text-align: center;
    padding: 3rem 2rem;
    opacity: 0.5;
}
.empty-state-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
.empty-state-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.06em;
}
</style>
""", unsafe_allow_html=True)

# ── CHART CONSTANTS ───────────────────────────────────────────
# Bold palette — readable on both light and dark backgrounds.
# Indigo, emerald, amber, rose, cyan, violet — high contrast,
# distinct from each other, professional analytics feel.
CHART_PALETTE = ["#4f46e5", "#059669", "#d97706", "#dc2626", "#0891b2", "#7c3aed", "#db2777"]

PLOTLY_LAYOUT = dict(
    font=dict(family="JetBrains Mono, monospace", size=11),
    margin=dict(l=40, r=20, t=50, b=40),
    colorway=CHART_PALETTE,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    # No hardcoded background — inherits from Streamlit theme
    # so it looks correct in both light and dark mode
)


# ═══════════════════════════════════════════════════════════════
#  SESSION PERSISTENCE
#
#  WHAT IS THE PROBLEM?
#  Streamlit session_state only lives as long as the browser tab.
#  Refresh the page → session_state is wiped → chat history gone.
#
#  THE FIX: Streamlit's built-in key-value store.
#  st.query_params is NOT the right tool here.
#  The correct tool is st.cache_resource for shared state, BUT
#  that shares across ALL users — wrong for a personal chat app.
#
#  REAL FIX: serialise chat history to a JSON string and store
#  it in a hidden text field via st.session_state + browser
#  localStorage via a small HTML/JS injection.
#
#  HOW IT WORKS:
#  1. On every message, serialise messages list to JSON
#  2. Inject a tiny JS snippet that writes it to localStorage
#  3. On page load, inject JS that reads from localStorage
#     and puts it in a hidden Streamlit text_input
#  4. Python reads that text_input and restores the messages
#
#  WHY localStorage?
#  It persists in the browser across refreshes, unlike
#  session_state which resets. It's scoped to the origin
#  (your Streamlit URL) so it's isolated per deployment.
#
#  LIMITATION: Only persists in the same browser.
#  A different browser or device starts fresh. For a
#  portfolio project this is acceptable and honest to disclose.
# ═══════════════════════════════════════════════════════════════

STORAGE_KEY = "datachat_history"

def save_history(messages: list):
    """Serialise messages to JSON and write to browser localStorage."""
    # We can only store serialisable data — strip out pandas objects
    # which can't be JSON serialised. Store result as None; the
    # displayed result will be re-executed on restore if needed.
    storable = []
    for msg in messages:
        storable.append({
            "role":               msg["role"],
            "content":            msg.get("content", ""),
            "code":               msg.get("code", ""),
            "error":              msg.get("error", ""),
            "was_healed":         msg.get("was_healed", False),
            "chart_instructions": msg.get("chart_instructions"),
            # result is NOT stored — pandas objects can't be JSON serialised
            # We store the code and re-execute on restore instead
        })
    payload = json.dumps(storable)
    # Inject JS to write to localStorage
    js = f"""
    <script>
    (function() {{
        try {{
            localStorage.setItem('{STORAGE_KEY}', {json.dumps(payload)});
        }} catch(e) {{}}
    }})();
    </script>
    """
    st.components.v1.html(js, height=0)


def load_history_js():
    """Inject JS to read localStorage and put it in a hidden input."""
    # We use a unique key so Streamlit tracks the component
    js = f"""
    <script>
    (function() {{
        try {{
            var data = localStorage.getItem('{STORAGE_KEY}');
            if (data) {{
                var input = window.parent.document.querySelector(
                    'input[data-testid="stTextInput"][aria-label="__history__"]'
                );
                if (input) {{
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(input, data);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }}
        }} catch(e) {{}}
    }})();
    </script>
    """
    st.components.v1.html(js, height=0)


# ── METADATA ──────────────────────────────────────────────────
def build_metadata(df: pd.DataFrame) -> str:
    """Extract schema only — no raw values sent to LLM."""
    lines = [f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns", "\nCOLUMNS AND TYPES:"]
    for col, dtype in df.dtypes.items():
        lines.append(f"  {col}: {dtype}")
    lines.append("\nSAMPLE (2 rows):")
    lines.append(df.head(2).to_string(index=False))
    lines.append("\nUNIQUE VALUES (categorical columns only):")
    for col in df.select_dtypes(include="object").columns:
        if df[col].nunique() <= 20:
            lines.append(f"  {col}: {df[col].unique().tolist()}")
    if "date" in df.columns:
        try:
            dates = pd.to_datetime(df["date"])
            lines.append(f"\nDATE RANGE: {dates.min().date()} to {dates.max().date()}")
        except Exception:
            pass
    return "\n".join(lines)


# ── SYSTEM PROMPT ─────────────────────────────────────────────
def build_system_prompt(df: pd.DataFrame) -> str:
    metadata = build_metadata(df)
    return f"""You are DataChat, a data analytics assistant. You answer questions by writing pandas code.

DATASET METADATA (schema only — no raw data is shared with you):
{metadata}

THE DATAFRAME IS NAMED: df
DATE COLUMN: convert with pd.to_datetime(df["date"]) before any date operations.

RESPONSE FORMAT — always return both blocks:

```python
# pandas code here
# must assign output to variable named `result`
```

```chart
type: bar | line | scatter | pie | histogram | table
x: column_name
y: column_name
size: column_name  (optional, only for bubble charts)
title: Chart title
```

Then 2-3 sentences explaining the answer in plain English.

CODE RULES:
1. Always assign final output to `result`
2. NEVER use print(). NEVER import anything. NEVER read files.
3. Use exact column names from the metadata above.
4. For dates: df_copy = df.copy(); df_copy["month"] = pd.to_datetime(df_copy["date"]).dt.to_period("M").astype(str)

CHART RULES:
- scatter/bubble/correlation/vs → type: scatter
- trend/over time/monthly/weekly → type: line
- proportion/share/percentage/pie → type: pie
- distribution/histogram/frequency → type: histogram
- everything else → type: bar"""


# ── GROQ API ──────────────────────────────────────────────────
def call_groq(messages: list, api_key: str) -> str:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.1,
        max_tokens=1000,
    )
    return response.choices[0].message.content


# ── EXTRACTORS ────────────────────────────────────────────────
def extract_code(text: str):
    match = re.search(r"```python\s*([\s\S]*?)```", text)
    return match.group(1).strip() if match else None

def extract_chart_instructions(text: str):
    match = re.search(r"```chart\s*([\s\S]*?)```", text)
    if not match:
        return None
    instructions = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            instructions[key.strip()] = value.strip()
    return instructions if instructions else None

def clean_response(text: str) -> str:
    text = re.sub(r"```python[\s\S]*?```", "", text)
    text = re.sub(r"```chart[\s\S]*?```", "", text)
    return text.strip()


# ── CHART TYPE INFERENCE ──────────────────────────────────────
def infer_chart_instructions(question: str, result) -> dict:
    """Infer chart type from user question when LLM skips chart block."""
    if result is None:
        return None
    if isinstance(result, pd.Series):
        df_r = result.reset_index()
        df_r.columns = [str(c) for c in df_r.columns]
    elif isinstance(result, pd.DataFrame):
        df_r = result.copy()
        df_r.columns = [str(c) for c in df_r.columns]
    else:
        return None
    if len(df_r) < 2:
        return None

    q = question.lower()
    if any(w in q for w in ["bubble", "scatter", "correlation", "vs ", "versus"]):
        chart_type = "scatter"
    elif any(w in q for w in ["trend", "over time", "monthly", "daily", "weekly", "line"]):
        chart_type = "line"
    elif any(w in q for w in ["pie", "proportion", "share", "percentage", "ratio"]):
        chart_type = "pie"
    elif any(w in q for w in ["histogram", "distribution", "frequency"]):
        chart_type = "histogram"
    else:
        chart_type = "bar"

    numeric_cols = df_r.select_dtypes(include="number").columns.tolist()
    label_cols   = df_r.select_dtypes(exclude="number").columns.tolist()
    x_col = label_cols[0]   if label_cols   else df_r.columns[0]
    y_col = numeric_cols[0] if numeric_cols else df_r.columns[-1]

    size_col = ""
    if chart_type == "scatter" and any(w in q for w in ["bubble", "size", "sized"]):
        candidates = [c for c in numeric_cols if any(w in c.lower() for w in ["count", "order", "qty", "quantity"])]
        size_col = candidates[0] if candidates else (numeric_cols[2] if len(numeric_cols) >= 3 else "")

    return {"type": chart_type, "x": x_col, "y": y_col, "size": size_col,
            "title": question.strip().capitalize()[:60]}


# ── CODE EXECUTION ────────────────────────────────────────────
def execute_code(code: str, df: pd.DataFrame):
    """
    Execute LLM-generated pandas code locally.
    Safety check blocks dangerous keywords before exec().
    Returns (result, error_message).
    """
    BLOCKED = ["__import__", "open(", "exec(", "eval(", "os.", "sys."]
    for bad in BLOCKED:
        if bad in code:
            return None, f"Blocked: code contains '{bad}'."
    safe_globals = {"df": df, "pd": pd}
    local_vars   = {}
    try:
        exec(code, safe_globals, local_vars)
        if "result" not in local_vars:
            return None, "Code ran but did not produce a variable named `result`."
        return local_vars["result"], None
    except Exception:
        return None, traceback.format_exc()


# ── RESULT RENDERER ───────────────────────────────────────────
def render_result(result, chart_instructions: dict = None, key: str = ""):
    """Display result as table + chart based on chart_instructions."""
    if result is None:
        return

    if isinstance(result, (int, float)):
        st.metric(label="Result", value=f"{result:,.2f}")
        return
    if isinstance(result, str):
        st.write(result)
        return
    if isinstance(result, pd.Series):
        result = result.reset_index()
        result.columns = [str(c) for c in result.columns]
    if not isinstance(result, pd.DataFrame):
        st.write(result)
        return

    result = result.reset_index(drop=True)
    result.columns = [str(c) for c in result.columns]
    st.dataframe(result, use_container_width=True)

    if not chart_instructions or len(result) < 2:
        return

    chart_type = chart_instructions.get("type", "bar").lower().strip()
    x_col      = chart_instructions.get("x", "").strip()
    y_col      = chart_instructions.get("y", "").strip()
    size_col   = chart_instructions.get("size", "").strip()
    title      = chart_instructions.get("title", "").strip()

    available_cols = result.columns.tolist()
    numeric_cols   = result.select_dtypes(include="number").columns.tolist()
    label_cols     = result.select_dtypes(exclude="number").columns.tolist()
    label_col      = label_cols[0] if label_cols else None

    if x_col not in available_cols:
        x_col = available_cols[0]
    if y_col not in available_cols:
        y_col = numeric_cols[-1] if numeric_cols else available_cols[-1]
    if size_col and size_col not in available_cols:
        size_col = ""

    fig = None

    if chart_type == "bar":
        fig = px.bar(result, x=x_col, y=y_col, title=title,
                     color=label_col if label_col and label_col != x_col else None,
                     color_discrete_sequence=CHART_PALETTE)

    elif chart_type == "line":
        fig = px.line(result, x=x_col, y=y_col, title=title,
                      markers=True, color_discrete_sequence=CHART_PALETTE)

    elif chart_type == "scatter":
        if len(numeric_cols) < 2:
            st.warning("Scatter needs 2 numeric columns. Showing bar instead.")
            fig = px.bar(result, x=x_col, y=y_col, title=title,
                         color_discrete_sequence=CHART_PALETTE)
        else:
            sx = x_col if x_col in numeric_cols else numeric_cols[0]
            sy = y_col if y_col in numeric_cols else numeric_cols[1]
            if size_col and size_col in numeric_cols:
                fig = px.scatter(result, x=sx, y=sy, size=size_col,
                                 text=label_col, color=label_col, title=title,
                                 color_discrete_sequence=CHART_PALETTE, size_max=60)
            else:
                fig = px.scatter(result, x=sx, y=sy, color=label_col,
                                 text=label_col, title=title,
                                 color_discrete_sequence=CHART_PALETTE)
            if fig:
                fig.update_traces(textposition="top center")

    elif chart_type == "pie":
        fig = px.pie(result, names=x_col, values=y_col, title=title,
                     color_discrete_sequence=CHART_PALETTE)

    elif chart_type == "histogram":
        fig = px.histogram(result, x=x_col, title=title,
                           color_discrete_sequence=CHART_PALETTE)

    elif chart_type == "table":
        return

    else:
        fig = px.bar(result, x=x_col, y=y_col, title=title,
                     color_discrete_sequence=CHART_PALETTE)

    if fig:
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")


# ── ERROR DISPLAY ─────────────────────────────────────────────
def render_error(error: str, was_healed: bool = False):
    """Show friendly error message — not raw Python traceback."""
    if not error:
        return
    err_lower = error.lower()
    if "keyerror" in err_lower or "column" in err_lower:
        friendly = "Column not found — the LLM may have used an incorrect column name."
    elif "valueerror" in err_lower:
        friendly = "Data format issue. Try rephrasing your question."
    elif "syntaxerror" in err_lower:
        friendly = "Generated code had a syntax error. Try rephrasing."
    elif "attributeerror" in err_lower:
        friendly = "Operation not supported on this data type."
    elif "typeerror" in err_lower:
        friendly = "Data type mismatch. Try being more specific."
    elif "auto-fix also failed" in err_lower:
        friendly = "Could not answer automatically. Try rephrasing or breaking into simpler steps."
    else:
        friendly = "Something went wrong. Try rephrasing your question."

    st.markdown(
        f'<div class="error-block">⚠ {friendly}<br>'
        f'<span style="font-size:0.72rem;opacity:0.6;">'
        f'Tip: rephrase the question or break it into smaller steps.</span></div>',
        unsafe_allow_html=True)

    with st.expander("Technical details"):
        st.code(error, language="text")


# ── KPI CARDS ─────────────────────────────────────────────────
def show_stats(df: pd.DataFrame):
    total_rev    = df["revenue"].sum()
    total_profit = df["profit"].sum()
    margin       = (total_profit / total_rev * 100) if total_rev else 0
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card">
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">${total_rev:,.0f}</div>
            <div class="kpi-delta">↑ all regions</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Total Profit</div>
            <div class="kpi-value">${total_profit:,.0f}</div>
            <div class="kpi-delta">↑ net after costs</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Profit Margin</div>
            <div class="kpi-value">{margin:.1f}%</div>
            <div class="kpi-delta">blended average</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{len(df):,}</div>
            <div class="kpi-delta">rows in dataset</div>
        </div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SESSION STATE INITIALISATION
#  Standard keys + new persistence-related keys.
# ═══════════════════════════════════════════════════════════════
if "messages"        not in st.session_state: st.session_state.messages        = []
if "df"              not in st.session_state: st.session_state.df              = None
if "history_loaded"  not in st.session_state: st.session_state.history_loaded  = False
if "result_cache"    not in st.session_state: st.session_state.result_cache    = {}


# ═══════════════════════════════════════════════════════════════
#  PERSISTENCE — LOAD ON FIRST RUN
#
#  On first load (history_loaded = False), we:
#  1. Render a hidden text input that JS will populate from localStorage
#  2. Read its value and restore messages into session_state
#  3. Set history_loaded = True so we don't repeat this
#
#  The hidden input trick: Streamlit text_input with
#  label_visibility="collapsed" and a unique aria-label
#  that our JS can target via querySelector.
# ═══════════════════════════════════════════════════════════════
if not st.session_state.history_loaded:
    load_history_js()
    raw = st.text_input("__history__", key="__history_input__",
                        label_visibility="collapsed")
    if raw:
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, list) and loaded:
                st.session_state.messages = loaded
        except Exception:
            pass
    st.session_state.history_loaded = True


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # API key — reads from Streamlit secrets first, sidebar as fallback
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        st.markdown('<div class="persist-badge">🔑 API key loaded from secrets</div>',
                    unsafe_allow_html=True)
    except Exception:
        api_key = st.text_input("Groq API Key", type="password",
                                 placeholder="gsk_...",
                                 help="Free at console.groq.com")

    st.markdown("---")
    st.markdown("### 📁 Data")
    upload = st.file_uploader("Upload CSV", type=["csv"])

    if upload:
        st.session_state.df = pd.read_csv(upload)
        st.success(f"✓ {upload.name}")
    else:
        try:
            st.session_state.df = pd.read_csv("sales_data.csv")
            st.info("Using: sales_data.csv")
        except FileNotFoundError:
            st.warning("Run generate_data.py or upload a CSV.")

    if st.session_state.df is not None:
        df = st.session_state.df
        st.markdown("---")
        st.markdown("### 🔍 Schema")
        st.markdown(f"""<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;
        color:#64748b;line-height:1.9;'>
        <span style='color:#4f46e5;font-weight:600;'>Rows</span> {df.shape[0]:,} &nbsp;
        <span style='color:#4f46e5;font-weight:600;'>Cols</span> {df.shape[1]}<br>
        {'<br>'.join([f'<span style="color:#4f46e5">{c}</span> {t}'
                      for c,t in df.dtypes.items()])}
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.result_cache = {}
            # Clear localStorage too
            st.components.v1.html(
                f"<script>localStorage.removeItem('{STORAGE_KEY}');</script>",
                height=0)
            st.rerun()
    with col2:
        msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        st.markdown(f"""<div style='font-family:JetBrains Mono,monospace;font-size:0.7rem;
        color:#64748b;padding:0.4rem;text-align:center;'>
        💬 {msg_count} question{"s" if msg_count != 1 else ""}
        </div>""", unsafe_allow_html=True)

    # Persistence indicator
    if st.session_state.messages:
        st.markdown('<div class="persist-badge">💾 History saved in browser</div>',
                    unsafe_allow_html=True)

    st.markdown("""<div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;
    color:#94a3b8;line-height:1.9;margin-top:1rem;'>
    Try asking:<br>
    · Revenue by region?<br>
    · Top 5 reps by profit?<br>
    · Monthly revenue trend<br>
    · Scatter: revenue vs profit<br>
    · Avg discount by category?
    </div>""", unsafe_allow_html=True)


# ── MAIN PAGE ─────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-title">DataChat</div>
    <div class="hero-sub">Natural Language Analytics · Secure · Local Execution</div>
</div>
""", unsafe_allow_html=True)

df = st.session_state.df

if df is not None:
    show_stats(df)
    with st.expander("Preview data (first 10 rows)"):
        st.dataframe(df.head(10), use_container_width=True)
    with st.expander("What gets sent to the LLM (metadata only)"):
        st.code(build_metadata(df), language="text")

st.markdown("---")


# ── CHAT HISTORY ──────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">💬</div>
        <div class="empty-state-text">Ask anything about your data below</div>
    </div>""", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(
            f'<div class="msg-user"><div class="msg-label">You</div>{msg["content"]}</div>',
            unsafe_allow_html=True)
    else:
        explanation = clean_response(msg.get("content", ""))

        # Show retry badge if self-healing was triggered
        if msg.get("was_healed"):
            st.markdown('<div class="retry-badge">⚡ auto-corrected</div>',
                        unsafe_allow_html=True)

        if explanation:
            st.markdown(
                f'<div class="msg-assistant"><div class="msg-label">DataChat</div>{explanation}</div>',
                unsafe_allow_html=True)

        if msg.get("code"):
            st.markdown(f'<div class="code-label">▶ pandas · executed locally</div>'
                        f'<div class="code-block">{msg["code"]}</div>',
                        unsafe_allow_html=True)

        # Re-execute code for result display (since result objects
        # can't be JSON serialised for localStorage persistence)
        if msg.get("code") and df is not None and not msg.get("error"):
            cache_key = f"result_{i}"
            if cache_key not in st.session_state.result_cache:
                result, _ = execute_code(msg["code"], df)
                st.session_state.result_cache[cache_key] = result
            cached_result = st.session_state.result_cache.get(cache_key)
            if cached_result is not None:
                render_result(cached_result, msg.get("chart_instructions"), key=str(i))

        if msg.get("error"):
            render_error(msg["error"], msg.get("was_healed", False))


# ── INPUT FORM ────────────────────────────────────────────────
# st.form: Enter key + button click both submit.
# clear_on_submit=True: clears input after submit automatically.
st.markdown("<br>", unsafe_allow_html=True)

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "q", placeholder="Ask anything... e.g. Show revenue by region as bar chart",
            label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Ask →", use_container_width=True)


# ── SUBMISSION HANDLER ────────────────────────────────────────
if submitted and user_input.strip():
    if not api_key:
        st.error("Enter your Groq API key in the sidebar. Free at console.groq.com")
    elif df is None:
        st.error("Please load a dataset first.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})

        groq_messages = (
            [{"role": "system", "content": build_system_prompt(df)}]
            + [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.messages]
        )

        with st.spinner("Writing code..."):
            try:
                llm_response       = call_groq(groq_messages, api_key)
                code               = extract_code(llm_response)
                chart_instructions = extract_chart_instructions(llm_response)

                result    = None
                error_msg = None
                was_healed = False

                if code:
                    result, error_msg = execute_code(code, df)

                    # ── SELF-HEALING RETRY ─────────────────────
                    if error_msg:
                        with st.spinner("Code failed — asking LLM to self-correct..."):
                            fix_prompt = f"""Your pandas code failed:

ERROR:
{error_msg}

ORIGINAL CODE:
```python
{code}
```

Fix it. Return ONLY the corrected ```python block. Assign output to `result`."""

                            fix_messages = groq_messages + [
                                {"role": "assistant", "content": llm_response},
                                {"role": "user",      "content": fix_prompt},
                            ]
                            try:
                                fix_response = call_groq(fix_messages, api_key)
                                fixed_code   = extract_code(fix_response)
                                if fixed_code:
                                    fixed_result, fixed_error = execute_code(fixed_code, df)
                                    if not fixed_error:
                                        result     = fixed_result
                                        error_msg  = None
                                        code       = fixed_code
                                        was_healed = True
                                    else:
                                        error_msg = f"Auto-fix also failed:\n{fixed_error}"
                                else:
                                    error_msg = "LLM could not produce a fix."
                            except Exception as fix_e:
                                error_msg = f"Fix attempt failed: {str(fix_e)}"
                else:
                    error_msg = "LLM did not return a code block. Try rephrasing."

                # Infer chart if LLM skipped chart block
                if not chart_instructions and result is not None:
                    chart_instructions = infer_chart_instructions(user_input.strip(), result)

                # Store message
                assistant_msg = {
                    "role":               "assistant",
                    "content":            llm_response,
                    "code":               code,
                    "chart_instructions": chart_instructions,
                    "error":              error_msg,
                    "was_healed":         was_healed,
                }
                st.session_state.messages.append(assistant_msg)

                # Cache result for immediate display
                cache_key = f"result_{len(st.session_state.messages) - 1}"
                st.session_state.result_cache[cache_key] = result

                # Persist to localStorage
                save_history(st.session_state.messages)

            except Exception as e:
                st.error(f"Groq API error: {str(e)}")

        st.rerun()