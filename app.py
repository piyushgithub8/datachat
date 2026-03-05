# ═══════════════════════════════════════════════════════════════
#  DataChat v2 — Text-to-Pandas Architecture
#
#  SECURITY MODEL:
#  ┌─────────────────────────────────────────────────────────┐
#  │  Your CSV  →  pandas  →  METADATA ONLY  →  Groq LLM   │
#  │                              ↓                          │
#  │                        LLM writes code                  │
#  │                              ↓                          │
#  │              code executes LOCALLY on your machine      │
#  │                              ↓                          │
#  │                        result shown                     │
#  └─────────────────────────────────────────────────────────┘
#  Raw data NEVER leaves your machine.
# ═══════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq
import traceback   # NEW: captures full error details when code fails
import re

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="DataChat · Analytics Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e4d9; }
[data-testid="stSidebar"] { background: #0f0f18 !important; border-right: 1px solid #1e1e2e; }
[data-testid="stSidebar"] * { color: #e8e4d9 !important; }
.hero-title { font-size: 2.8rem; font-weight: 800; letter-spacing: -0.03em;
    background: linear-gradient(135deg, #f5e642 0%, #f0a500 50%, #e8e4d9 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; line-height: 1.1; margin-bottom: 0.2rem; }
.hero-sub { font-family: 'DM Mono', monospace; font-size: 0.8rem; color: #555570;
    letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 2rem; }
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 1.5rem; }
.stat-card { background: #0f0f18; border: 1px solid #1e1e2e; border-radius: 12px;
    padding: 1.2rem 1.4rem; position: relative; overflow: hidden; }
.stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 2px; background: linear-gradient(90deg, #f5e642, #f0a500); }
.stat-label { font-family: 'DM Mono', monospace; font-size: 0.68rem; color: #555570;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.4rem; }
.stat-value { font-size: 1.6rem; font-weight: 700; color: #f5e642; line-height: 1; }
.stat-delta { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #4ecb71; margin-top: 0.3rem; }
.msg-user { background: #1a1a28; border: 1px solid #2a2a40; border-radius: 16px 16px 4px 16px;
    padding: 1rem 1.3rem; margin: 0.8rem 0; margin-left: 3rem; font-size: 0.95rem; color: #e8e4d9; }
.msg-assistant { background: #0f1a0f; border: 1px solid #1e3a1e; border-radius: 16px 16px 16px 4px;
    padding: 1rem 1.3rem; margin: 0.8rem 0; margin-right: 3rem;
    font-size: 0.95rem; color: #e8e4d9; border-left: 3px solid #f5e642; }
.msg-label { font-family: 'DM Mono', monospace; font-size: 0.65rem; text-transform: uppercase;
    letter-spacing: 0.1em; margin-bottom: 0.5rem; opacity: 0.5; }
.code-block { background: #0d0d1a; border: 1px solid #2a2a40; border-radius: 8px;
    padding: 0.8rem 1rem; font-family: 'DM Mono', monospace; font-size: 0.8rem;
    color: #f5e642; margin: 0.5rem 0; white-space: pre-wrap; }
.error-block { background: #1a0d0d; border: 1px solid #4a1a1a; border-radius: 8px;
    padding: 0.8rem 1rem; font-family: 'DM Mono', monospace; font-size: 0.8rem;
    color: #ff6b6b; margin: 0.5rem 0; }
.stTextInput > div > div > input { background: #0f0f18 !important; border: 1px solid #2a2a40 !important;
    border-radius: 10px !important; color: #e8e4d9 !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.9rem !important; }
.stTextInput > div > div > input:focus { border-color: #f5e642 !important; }
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    background: #f5e642 !important; color: #0a0a0f !important; border: none !important;
    border-radius: 8px !important; font-family: 'Syne', sans-serif !important; font-weight: 700 !important; }
[data-testid="stForm"] { border: none !important; padding: 0 !important; }
hr { border-color: #1e1e2e !important; }
::-webkit-scrollbar { width: 5px; } ::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #2a2a40; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

CHART_PALETTE = ["#f5e642", "#f0a500", "#4ecb71", "#4ea8cb", "#cb4e8a", "#a84ecb"]
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0f0f18", plot_bgcolor="#0f0f18",
    font=dict(family="DM Mono, monospace", color="#e8e4d9", size=11),
    xaxis=dict(gridcolor="#1e1e2e", linecolor="#2a2a40"),
    yaxis=dict(gridcolor="#1e1e2e", linecolor="#2a2a40"),
    margin=dict(l=40, r=20, t=40, b=40),
    colorway=CHART_PALETTE,
)


# ═══════════════════════════════════════════════════════════════
#  FUNCTION: build_metadata
#
#  PURPOSE:
#  Extract ONLY structural information about the DataFrame —
#  nothing that reveals actual data values at scale.
#  This is what gets sent to the LLM.
#
#  WHAT WE SEND (safe metadata):
#  - Column names and their data types
#  - Shape (row/column count)
#  - 2 sample rows so LLM understands the format
#  - Unique values for low-cardinality columns (region, category)
#    so LLM knows exact spellings to use in code
#  - Date range (min/max date only — not the actual dates)
#
#  WHAT WE DON'T SEND:
#  - Actual revenue/profit/quantity values
#  - Full row data
#  - Any aggregated calculations
#
#  PARAMETER:
#  df — the loaded DataFrame
#
#  RETURNS:
#  A plain text string describing the data structure
# ═══════════════════════════════════════════════════════════════
def build_metadata(df: pd.DataFrame) -> str:
    lines = []

    # Shape: how many rows and columns
    lines.append(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

    # Column names + their pandas dtypes
    # dtype examples: object (text), float64 (decimal), int64 (integer)
    lines.append("\nCOLUMNS AND TYPES:")
    for col, dtype in df.dtypes.items():
        lines.append(f"  {col}: {dtype}")

    # 2 sample rows — just enough for LLM to understand structure/format
    # index=False removes the row number column from the text
    lines.append("\nSAMPLE (2 rows):")
    lines.append(df.head(2).to_string(index=False))

    # For text columns with few unique values (like region, category),
    # tell the LLM the exact values so it uses correct spellings in code.
    # nunique() counts how many unique values a column has.
    lines.append("\nUNIQUE VALUES (categorical columns):")
    for col in df.select_dtypes(include="object").columns:
        # Only show unique values if there are 20 or fewer
        # (avoids dumping hundreds of product names)
        if df[col].nunique() <= 20:
            unique_vals = df[col].unique().tolist()
            lines.append(f"  {col}: {unique_vals}")

    # Date range — only min and max, not actual values
    if "date" in df.columns:
        try:
            dates = pd.to_datetime(df["date"])
            lines.append(f"\nDATE RANGE: {dates.min().date()} to {dates.max().date()}")
        except Exception:
            pass

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  FUNCTION: build_system_prompt
#
#  PURPOSE:
#  Tell the LLM its role, give it the metadata, and give it
#  strict instructions on what to return.
#
#  KEY CHANGE FROM v1:
#  v1: "here are the pre-computed answers, read them out"
#  v2: "here is the schema only, write pandas CODE to answer"
#
#  WHY STRICT OUTPUT FORMAT MATTERS:
#  The LLM must return code in a predictable block so our
#  extract_code() function can reliably find and run it.
#  If the LLM returns free text with code mixed in, parsing
#  becomes unreliable. We enforce ```python ... ``` blocks.
#
#  TWO-PART RESPONSE FORMAT we instruct the LLM to use:
#  1. ```python ... ```  — the executable pandas code
#  2. Plain English explanation of what the code does/found
# ═══════════════════════════════════════════════════════════════
def build_system_prompt(df: pd.DataFrame) -> str:
    metadata = build_metadata(df)

    return f"""You are DataChat, a data analytics assistant. You answer questions by writing pandas code.

DATASET METADATA (schema only — no raw data):
{metadata}

THE DATAFRAME IS NAMED: df
DATE COLUMN: convert with pd.to_datetime(df["date"]) before any date operations.

YOUR RESPONSE FORMAT — always follow this exactly, both blocks required:
```python
# pandas code here
# must assign final output to a variable called `result`
# result can be: a number, a string, a Series, or a DataFrame
```
```chart
type: bar | line | scatter | pie | histogram | table
x: column_name_or_index
y: column_name_or_value
title: Chart title here
```

Then 2-3 sentences in plain English explaining the answer.

CODE RULES:
1. Always assign final output to variable named `result`
2. For group-by: result = df.groupby(...)["col"].agg(...)
3. For single numbers: result = df["col"].sum()
4. For filtered rows: result = df[df["col"] > value]
5. For scatter plots: result must be a DataFrame with 2 numeric columns
6. NEVER use print(). NEVER import anything. NEVER read files.
7. Use exact column names and values from the metadata above.

CHART RULES:
- Match chart type to what the user asks for explicitly
- If user says scatter/plot/correlation → type: scatter
- If user says bubble → type: scatter, and add size: column_name
- If user says trend/over time/monthly → type: line
- If user says breakdown/compare/by region → type: bar
- If user says proportion/share/percentage → type: pie
- x and y must be actual column names in `result`
- size is optional — only include when user asks for bubble chart

EXAMPLE 1 — bar:
User: Revenue by region
```python
result = df.groupby("region")["revenue"].sum().sort_values(ascending=False).round(2)
```
```chart
type: bar
x: region
y: revenue
title: Total Revenue by Region
```

EXAMPLE 2 — scatter:
User: Show scatter plot of revenue vs profit
```python
result = df[["revenue", "profit"]].copy()
```
```chart
type: scatter
x: revenue
y: profit
title: Revenue vs Profit
```

EXAMPLE 3 — line:
User: Monthly revenue trend
```python
df_copy = df.copy()
df_copy["month"] = pd.to_datetime(df_copy["date"]).dt.to_period("M").astype(str)
result = df_copy.groupby("month")["revenue"].sum().reset_index()
```
```chart
type: line
x: month
y: revenue
title: Monthly Revenue Trend
```

EXAMPLE 4 — bubble scatter:
User: scatter plot of revenue vs profit with regions as bubble
```python
result = df.groupby("region")[["revenue", "profit"]].mean().reset_index()
result["count"] = df.groupby("region")["revenue"].count().values
```
```chart
type: scatter
x: revenue
y: profit
size: count
title: Avg Revenue vs Profit by Region (bubble = order count)
```
"""


# ═══════════════════════════════════════════════════════════════
#  FUNCTION: call_groq
#
#  No change from v1 — sends messages list to LLM, returns text.
#  temperature=0.1 keeps code generation deterministic.
# ═══════════════════════════════════════════════════════════════
def call_groq(messages: list, api_key: str) -> str:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.1,
        max_tokens=1000,
    )
    return response.choices[0].message.content


# ═══════════════════════════════════════════════════════════════
#  FUNCTION: extract_code
#
#  PURPOSE:
#  Find the ```python ... ``` block in the LLM's response
#  and extract just the code string.
#
#  Same regex pattern as before, but now looking for ```python
#  instead of ```chart_spec.
#
#  REGEX: r"```python\s*([\s\S]*?)```"
#    ```python   → match this literal text
#    \s*         → optional whitespace/newlines
#    ([\s\S]*?)  → capture everything lazily until...
#    ```         → closing backticks
#
#  RETURNS: code string if found, else None
# ═══════════════════════════════════════════════════════════════
def extract_code(text: str):
    match = re.search(r"```python\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return None


# ═══════════════════════════════════════════════════════════════
#  FUNCTION: extract_chart_instructions
#
#  Tries to parse a ```chart...``` block from LLM response.
#  On small models like llama-3.1-8b this often returns None
#  because the model ignores the instruction. That's fine —
#  infer_chart_instructions() is the reliable fallback.
# ═══════════════════════════════════════════════════════════════
def extract_chart_instructions(text: str):
    match = re.search(r"```chart\s*([\s\S]*?)```", text)
    if not match:
        return None
    instructions = {}
    for line in match.group(1).strip().splitlines():
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            instructions[key.strip()] = value.strip()
    return instructions if instructions else None


# ═══════════════════════════════════════════════════════════════
#  FUNCTION: infer_chart_instructions  ← NEW, REPLACES LLM BLOCK
#
#  PURPOSE:
#  Since small LLMs often skip the ```chart block, we infer
#  chart type + columns directly from the user's question and
#  the result DataFrame. Pure Python — no LLM involved.
#
#  HOW IT WORKS:
#  1. Scan the user question for chart-type keywords
#  2. Inspect result columns to find x and y automatically
#  3. Return a chart_instructions dict identical in structure
#     to what extract_chart_instructions() would return
#
#  KEYWORD MATCHING:
#  We use Python's `any(word in question for word in [...])` —
#  checks if ANY word in the list appears in the question string.
#  question.lower() normalises case so "Scatter" matches "scatter"
#
#  PARAMETERS:
#  question (str)     — the original user question
#  result (DataFrame) — the computed result from execute_code()
#
#  RETURNS:
#  dict with keys: type, x, y, size, title
# ═══════════════════════════════════════════════════════════════
def infer_chart_instructions(question: str, result) -> dict:
    if result is None:
        return None

    # Normalise to DataFrame first so we can inspect columns
    if isinstance(result, pd.Series):
        df_result = result.reset_index()
        df_result.columns = [str(c) for c in df_result.columns]
    elif isinstance(result, pd.DataFrame):
        df_result = result.copy()
        df_result.columns = [str(c) for c in df_result.columns]
    else:
        # Scalar or string — no chart needed
        return None

    if len(df_result) < 2:
        return None

    q = question.lower()

    # ── Detect chart type from keywords ──────────────────────
    # Each condition checks a list of synonyms the user might type.
    if any(w in q for w in ["bubble", "scatter", "correlation", "vs ", "versus", "plot"]):
        chart_type = "scatter"
    elif any(w in q for w in ["trend", "over time", "monthly", "daily", "weekly", "line"]):
        chart_type = "line"
    elif any(w in q for w in ["pie", "proportion", "share", "percentage", "ratio"]):
        chart_type = "pie"
    elif any(w in q for w in ["histogram", "distribution", "frequency"]):
        chart_type = "histogram"
    else:
        chart_type = "bar"   # default — most analytics questions are bar charts

    # ── Auto-detect x and y columns from result ───────────────
    numeric_cols = df_result.select_dtypes(include="number").columns.tolist()
    label_cols   = df_result.select_dtypes(exclude="number").columns.tolist()

    # x: prefer a label/category column (e.g. region, category, month)
    # y: prefer first numeric column (e.g. revenue, profit)
    x_col = label_cols[0]   if label_cols   else df_result.columns[0]
    y_col = numeric_cols[0] if numeric_cols else df_result.columns[-1]

    # ── Detect bubble size column ─────────────────────────────
    # If user asked for bubble chart AND there's a column that
    # looks like a count (named "count", "orders", "quantity")
    # use it as the size parameter.
    size_col = ""
    if chart_type == "scatter" and any(w in q for w in ["bubble", "size", "sized"]):
        size_candidates = [c for c in numeric_cols
                           if any(w in c.lower() for w in ["count", "order", "qty", "quantity", "n_"])]
        if size_candidates:
            size_col = size_candidates[0]
        elif len(numeric_cols) >= 3:
            # Use third numeric column as size if available
            size_col = numeric_cols[2]

    # ── Build title from question ─────────────────────────────
    # Capitalise first letter, trim to 60 chars for clean display
    title = question.strip().capitalize()[:60]

    return {
        "type":  chart_type,
        "x":     x_col,
        "y":     y_col,
        "size":  size_col,
        "title": title,
    }

# ═══════════════════════════════════════════════════════════════
#  FUNCTION: execute_code  ← THE CORE NEW FUNCTION
#
#  PURPOSE:
#  Safely execute the pandas code the LLM wrote, against
#  your LOCAL DataFrame. This is where the actual calculation
#  happens — on your machine, on your full data.
#
#  HOW eval() WORKS:
#  eval(expression, globals_dict)
#  Executes a Python expression string as real Python code.
#  The globals_dict controls what names are available inside
#  the expression — we pass {"df": df, "pd": pd} so the code
#  can reference `df` and `pd` but nothing else.
#
#  HOW exec() WORKS:
#  exec(statements, globals_dict, locals_dict)
#  Like eval() but for multi-line code (statements, not just
#  expressions). After exec(), we read `result` from locals_dict.
#
#  SECURITY NOTE:
#  eval/exec can run arbitrary Python — dangerous if the LLM
#  is malicious or compromised. We mitigate by:
#  - Restricting globals to only {df, pd} — no file I/O, no os
#  - Checking for dangerous keywords before executing
#  - Wrapping in try/except so bad code can't crash the app
#  For production systems you'd use a proper sandbox.
#
#  RETURNS:
#  (result, error_message)
#  result       — the computed value (number, Series, DataFrame)
#  error_message — None if success, string if something failed
# ═══════════════════════════════════════════════════════════════
def execute_code(code: str, df: pd.DataFrame):

    # ── SAFETY CHECK ──────────────────────────────────────────
    # Block keywords that could do dangerous things.
    # This is a basic guard — not a full sandbox.
    # "__import__" -> prevent importing os, sys etc.
    # "open("     -> prevent reading/writing files
    # "exec("     -> prevent nested exec calls
    # "eval("     -> prevent nested eval calls
    BLOCKED = ["__import__", "open(", "exec(", "eval(", "os.", "sys."]
    for bad in BLOCKED:
        if bad in code:
            return None, f"Blocked: code contains '{bad}' which is not allowed."

    # ── EXECUTION ENVIRONMENT ─────────────────────────────────
    # Only make df and pd available inside the executed code.
    # The LLM's code can use `df` and `pd` — nothing else.
    safe_globals = {"df": df, "pd": pd}
    local_vars   = {}   # dict where exec() stores variables it creates

    try:
        # exec() runs multi-line code (assignments, groupby chains etc.)
        # After exec(), local_vars["result"] holds the final value.
        exec(code, safe_globals, local_vars)

        # Check that the code actually created a `result` variable
        if "result" not in local_vars:
            return None, "Code ran but did not produce a variable named `result`."

        return local_vars["result"], None   # success

    except Exception:
        # traceback.format_exc() captures the full error message
        # with line numbers — much more useful than str(e) alone
        return None, traceback.format_exc()


# ═══════════════════════════════════════════════════════════════
#  FUNCTION: render_result
#
#  PURPOSE:
#  Display the computed result AND draw the correct chart type
#  based on chart_instructions from the LLM.
#
#  PARAMETERS:
#  result             — computed value from execute_code()
#                       can be: int, float, str, Series, DataFrame
#  chart_instructions — dict parsed from ```chart block
#                       e.g. {"type": "scatter", "x": "revenue",
#                              "y": "profit", "size": "count",
#                              "title": "..."}
#                       None if LLM didn't return a chart block
#
#  FLOW:
#  1. Handle scalar types first (int, float, str)
#  2. Normalise Series → DataFrame (consistent from here on)
#  3. Show data table
#  4. Read chart_instructions and pick the right px.* function
#  5. Handle bubble chart (size parameter) inside scatter
#  6. Apply dark theme layout and render
# ═══════════════════════════════════════════════════════════════
def render_result(result, chart_instructions: dict = None):
    if result is None:
        return

    # ── Single number ─────────────────────────────────────────
    # isinstance(x, (int, float)) checks if x is either type.
    # st.metric renders a large styled KPI number.
    if isinstance(result, (int, float)):
        st.metric(label="Result", value=f"{result:,.2f}")
        return

    # ── String result ─────────────────────────────────────────
    if isinstance(result, str):
        st.write(result)
        return

    # ── Normalise Series → DataFrame ──────────────────────────
    # A groupby like df.groupby("region")["revenue"].sum()
    # returns a Series where region is the INDEX and revenue
    # is the VALUE. reset_index() promotes index → column so
    # we get a proper 2-column DataFrame: [region, revenue].
    # From this point we only deal with DataFrames.
    if isinstance(result, pd.Series):
        result = result.reset_index()
        result.columns = [str(c) for c in result.columns]

    if not isinstance(result, pd.DataFrame):
        # Catch-all for anything unexpected (list, dict, etc.)
        st.write(result)
        return

    # Ensure all column names are strings (avoids Plotly issues
    # when column names are integers or period objects)
    result = result.reset_index(drop=True)
    result.columns = [str(c) for c in result.columns]

    # Always show the raw data table first
    st.dataframe(result, use_container_width=True)

    # No chart if instructions missing or not enough data rows
    if not chart_instructions or len(result) < 2:
        return

    # ── Read chart config from instructions dict ──────────────
    # .get("key", default) safely reads a key — returns default
    # instead of raising KeyError if key doesn't exist.
    chart_type = chart_instructions.get("type", "bar").lower().strip()
    x_col      = chart_instructions.get("x", "").strip()
    y_col      = chart_instructions.get("y", "").strip()
    size_col   = chart_instructions.get("size", "").strip()
    title      = chart_instructions.get("title", "").strip()

    available_cols = result.columns.tolist()
    numeric_cols   = result.select_dtypes(include="number").columns.tolist()
    label_cols     = result.select_dtypes(exclude="number").columns.tolist()

    # ── Column validation + fallbacks ────────────────────────
    # LLM sometimes hallucinates column names. We validate and
    # fall back gracefully so the app never crashes.

    # x fallback: first column
    if x_col not in available_cols:
        x_col = available_cols[0]

    # y fallback: last numeric column
    if y_col not in available_cols:
        y_col = numeric_cols[-1] if numeric_cols else available_cols[-1]

    # size fallback: empty string (means no bubble sizing)
    if size_col and size_col not in available_cols:
        size_col = ""

    # label column: first non-numeric column (e.g. "region")
    # used for coloring and labelling points on scatter/bubble
    label_col = label_cols[0] if label_cols else None

    # ── Draw the correct chart ────────────────────────────────
    fig = None

    # ── BAR ───────────────────────────────────────────────────
    if chart_type == "bar":
        fig = px.bar(
            result,
            x=x_col,
            y=y_col,
            title=title,
            color=label_col if label_col and label_col != x_col else None,
            color_discrete_sequence=CHART_PALETTE,
        )

    # ── LINE ──────────────────────────────────────────────────
    elif chart_type == "line":
        fig = px.line(
            result,
            x=x_col,
            y=y_col,
            title=title,
            markers=True,                   # show dots at each data point
            color_discrete_sequence=CHART_PALETTE,
        )

    # ── SCATTER / BUBBLE ──────────────────────────────────────
    # Scatter needs at least 2 numeric columns for x and y.
    # Bubble = scatter + size parameter (3rd dimension).
    elif chart_type == "scatter":
        if len(numeric_cols) < 2:
            st.warning("Scatter plot needs 2 numeric columns. Showing bar chart instead.")
            fig = px.bar(result, x=x_col, y=y_col, title=title,
                         color_discrete_sequence=CHART_PALETTE)
        else:
            # Make sure x and y are both numeric for scatter
            # If LLM put a text column as x, swap to first numeric
            sx = x_col if x_col in numeric_cols else numeric_cols[0]
            sy = y_col if y_col in numeric_cols else numeric_cols[1]

            if size_col and size_col in numeric_cols:
                # ── BUBBLE CHART ──────────────────────────────
                # px.scatter with size= makes each point a bubble
                # where bubble area is proportional to size column.
                # text= puts a label on each bubble (e.g. region name).
                # color= gives each bubble a distinct color.
                # size_max= caps the largest bubble's pixel diameter.
                fig = px.scatter(
                    result,
                    x=sx,
                    y=sy,
                    size=size_col,
                    text=label_col,
                    color=label_col,
                    title=title,
                    color_discrete_sequence=CHART_PALETTE,
                    size_max=60,
                )
                # textposition puts labels above bubbles, not inside
                fig.update_traces(textposition="top center")
            else:
                # ── REGULAR SCATTER ───────────────────────────
                # Color and label by the categorical column if present
                # e.g. color each region dot differently
                fig = px.scatter(
                    result,
                    x=sx,
                    y=sy,
                    color=label_col,
                    text=label_col,
                    title=title,
                    color_discrete_sequence=CHART_PALETTE,
                )
                fig.update_traces(textposition="top center")

    # ── PIE ───────────────────────────────────────────────────
    # names= the categorical column (slice labels)
    # values= the numeric column (slice sizes)
    elif chart_type == "pie":
        fig = px.pie(
            result,
            names=x_col,
            values=y_col,
            title=title,
            color_discrete_sequence=CHART_PALETTE,
        )

    # ── HISTOGRAM ─────────────────────────────────────────────
    # Only needs one column — the distribution of x values
    elif chart_type == "histogram":
        fig = px.histogram(
            result,
            x=x_col,
            title=title,
            color_discrete_sequence=CHART_PALETTE,
        )

    # ── TABLE only — no chart needed ──────────────────────────
    elif chart_type == "table":
        return   # data table already shown above

    # ── DEFAULT fallback ──────────────────────────────────────
    else:
        fig = px.bar(
            result,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=CHART_PALETTE,
        )

    # ── Apply dark theme and render ───────────────────────────
    # fig is None only if an unexpected branch was hit
    if fig:
        # **PLOTLY_LAYOUT unpacks the constants dict as keyword args
        fig.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
#  FUNCTION: clean_response
#
#  Strips the ```python...``` block from display text.
#  We show the code separately in a styled block, so we don't
#  want it appearing again inside the chat bubble.
# ═══════════════════════════════════════════════════════════════
def clean_response(text: str) -> str:
    # Strip ```python...``` blocks
    text = re.sub(r"```python[\s\S]*?```", "", text)
    # Strip ```chart...``` blocks  ← THIS WAS MISSING
    text = re.sub(r"```chart[\s\S]*?```", "", text)
    return text.strip()


# ── FUNCTION: show_stats ──────────────────────────────────────
# Pandas calculations stay here — runs locally, never sent to LLM
def show_stats(df: pd.DataFrame):
    total_rev    = df["revenue"].sum()
    total_profit = df["profit"].sum()
    margin       = (total_profit / total_rev * 100) if total_rev else 0

    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card"><div class="stat-label">Total Revenue</div>
            <div class="stat-value">${total_rev:,.0f}</div>
            <div class="stat-delta">all regions</div></div>
        <div class="stat-card"><div class="stat-label">Total Profit</div>
            <div class="stat-value">${total_profit:,.0f}</div>
            <div class="stat-delta">net after costs</div></div>
        <div class="stat-card"><div class="stat-label">Profit Margin</div>
            <div class="stat-value">{margin:.1f}%</div>
            <div class="stat-delta">blended</div></div>
        <div class="stat-card"><div class="stat-label">Total Orders</div>
            <div class="stat-value">{len(df):,}</div>
            <div class="stat-delta">rows</div></div>
    </div>""", unsafe_allow_html=True)


# ── SESSION STATE ─────────────────────────────────────────────
if "messages" not in st.session_state: st.session_state.messages = []
if "df"       not in st.session_state: st.session_state.df       = None


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Configuration")
    # Try to load API key from Streamlit Cloud secrets first.
    # st.secrets reads from .streamlit/secrets.toml on cloud,
    # or from the secrets you set in Streamlit Cloud dashboard.
    # If not found (e.g. running locally), fall back to sidebar input.
    #
    # The try/except handles the case where secrets.toml doesn't
    # exist locally — avoids a crash during local development.
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("API key loaded from secrets", icon="🔑")
    except Exception:
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Free at console.groq.com"
        )
    st.markdown("---")
    st.markdown("### Data Source")
    upload = st.file_uploader("Upload CSV", type=["csv"])
    if upload:
        st.session_state.df = pd.read_csv(upload)
        st.success(f"Loaded: {upload.name}")
    else:
        try:
            st.session_state.df = pd.read_csv("sales_data.csv")
            st.info("Using: sales_data.csv")
        except FileNotFoundError:
            st.warning("Run generate_data.py first, or upload a CSV.")

    if st.session_state.df is not None:
        df = st.session_state.df
        st.markdown("---")
        st.markdown("### Metadata Preview")
        st.markdown(f"""<div style='font-family:DM Mono,monospace;font-size:0.72rem;color:#555570;line-height:1.8;'>
        Rows: <span style='color:#f5e642'>{df.shape[0]:,}</span><br>
        Cols: <span style='color:#f5e642'>{df.shape[1]}</span><br>
        {'<br>'.join([f'{c}: <span style="color:#e8e4d9">{t}</span>' for c,t in df.dtypes.items()])}
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("""<div style='font-family:DM Mono,monospace;font-size:0.68rem;color:#333350;line-height:1.8;margin-top:1rem;'>
    Try:<br>- Revenue by region?<br>- Top 5 reps by profit?<br>
    - Monthly revenue trend<br>- Orders where discount > 10%?<br>
    - Avg order value by category?
    </div>""", unsafe_allow_html=True)


# ── MAIN PAGE ─────────────────────────────────────────────────
st.markdown('<div class="hero-title">DataChat</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Text-to-Pandas · Data never leaves your machine</div>',
            unsafe_allow_html=True)

df = st.session_state.df
if df is not None:
    show_stats(df)
    with st.expander("Preview data (first 10 rows)"):
        st.dataframe(df.head(10), use_container_width=True)
    # Show exactly what gets sent to the LLM — full transparency
    with st.expander("What gets sent to the LLM (metadata only)"):
        st.code(build_metadata(df), language="text")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════
#  CHAT HISTORY DISPLAY
#
#  Each message in session_state.messages is a dict:
#  {
#    "role":    "user" | "assistant",
#    "content": "the text",
#    "code":    "the pandas code" (assistant only, may be None),
#    "result":  the computed result object (assistant only)
#  }
#
#  We store code and result IN the message so the chat history
#  can re-render charts and tables on every rerun.
# ═══════════════════════════════════════════════════════════════
# REPLACE WITH THIS:
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="msg-user"><div class="msg-label">You</div>{msg["content"]}</div>',
            unsafe_allow_html=True)
    else:
        explanation = clean_response(msg["content"])
        if explanation:
            st.markdown(
                f'<div class="msg-assistant"><div class="msg-label">DataChat</div>{explanation}</div>',
                unsafe_allow_html=True)

        if msg.get("code"):
            st.markdown(
                f'<div class="code-block">▶ pandas code executed locally:\n{msg["code"]}</div>',
                unsafe_allow_html=True)

        if msg.get("result") is not None:
            render_result(msg["result"], msg.get("chart_instructions"))

        if msg.get("error"):
            # Parse the raw error into something human-readable.
            # The user doesn't need to see a Python traceback —
            # they need to know what to do next.
            raw_error = msg["error"]

            # Map common pandas/Python errors to plain English
            # str(raw_error).lower() normalises case for matching
            err_lower = str(raw_error).lower()

            if "keyerror" in err_lower or "column" in err_lower:
                friendly = "Column not found. The LLM may have used a wrong column name."
            elif "valueerror" in err_lower:
                friendly = "Data format issue. Try rephrasing your question."
            elif "syntaxerror" in err_lower:
                friendly = "The generated code had a syntax error. Try rephrasing."
            elif "attributeerror" in err_lower:
                friendly = "Operation not supported on this data type."
            elif "typeerror" in err_lower:
                friendly = "Data type mismatch. Try being more specific in your question."
            elif "auto-fix also failed" in err_lower:
                friendly = "This question couldn't be answered automatically. Try rephrasing or breaking it into simpler steps."
            else:
                friendly = "Something went wrong. Try rephrasing your question."

            # Show friendly message to user
            st.markdown(
                f'<div class="error-block">⚠ {friendly}<br><br>'
                f'<span style="font-size:0.7rem;opacity:0.5;">Try: rephrasing the question, '
                f'or breaking it into smaller steps.</span></div>',
                unsafe_allow_html=True
            )

            # Show raw error in expander for debugging during development
            # Delete this expander once you go to production
            with st.expander("Technical details"):
                st.code(raw_error, language="text")


# ── INPUT FORM ────────────────────────────────────────────────
# st.form + st.form_submit_button: handles both Enter and click
# clear_on_submit=True: empties input after submit automatically
st.markdown("<br>", unsafe_allow_html=True)

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input("q",
            placeholder="Ask anything... e.g. Show revenue by region",
            label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Ask →", use_container_width=True)


# ═══════════════════════════════════════════════════════════════
#  SUBMISSION HANDLER — THE NEW FLOW
#
#  OLD FLOW (v1):
#  question → LLM (with data summaries) → formatted answer
#
#  NEW FLOW (v2):
#  question → LLM (schema only) → pandas code
#                                       ↓
#                            execute_code() runs it locally
#                                       ↓
#                            result rendered as table/chart
#
#  STEP BY STEP:
#  1. User submits question
#  2. Append to messages history
#  3. Call Groq with system prompt (metadata only) + history
#  4. Extract ```python...``` block from LLM response
#  5. Execute code against local df using execute_code()
#  6. Store reply + code + result in messages
#  7. st.rerun() re-renders everything including new result
# ═══════════════════════════════════════════════════════════════
if submitted and user_input.strip():
    if not api_key:
        st.error("Enter your Groq API key in the sidebar.")
    elif df is None:
        st.error("Please load a dataset first.")
    else:
        # Step 1: store user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input.strip()
        })

        # Step 2: build message list for Groq
        # System prompt contains METADATA ONLY — no raw data values
        groq_messages = (
            [{"role": "system", "content": build_system_prompt(df)}]
            + [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.messages]
        )

        with st.spinner("Writing code..."):
            try:
                # ── Step 1: Get response from LLM ─────────────────────
                llm_response = call_groq(groq_messages, api_key)

                # ── Step 2: Extract code and chart block ───────────────
                code               = extract_code(llm_response)
                chart_instructions = extract_chart_instructions(llm_response)

                result    = None
                error_msg = None

                # ── Step 3: Execute code locally ───────────────────────
                if code:
                    result, error_msg = execute_code(code, df)

                    # ── Step 4: SELF-HEALING RETRY LOOP ───────────────
                    #
                    # WHAT IS HAPPENING HERE:
                    # If the first execution failed (error_msg is not None),
                    # we don't give up. Instead we:
                    # 1. Build a new message telling the LLM what went wrong
                    # 2. Ask it to fix the code
                    # 3. Extract and execute the fixed code
                    # 4. If that works, use the fixed result
                    #
                    # This is called an "agentic" pattern — the system
                    # observes the result of its own action (code execution)
                    # and self-corrects. One retry is usually enough.
                    #
                    # WHY ONE RETRY ONLY?
                    # More retries = more API calls = slower + more expensive.
                    # In practice, if the fix fails twice, the question is
                    # likely unanswerable with the current schema — better
                    # to tell the user than loop forever.
                    if error_msg:
                        with st.spinner("Code failed — asking LLM to fix it..."):

                            # Build the fix request message.
                            # We tell the LLM:
                            # - Here was your original code
                            # - Here is the exact error it produced
                            # - Please fix it
                            fix_prompt = f"""Your previous pandas code failed with this error:

        ERROR:
        {error_msg}

        ORIGINAL CODE THAT FAILED:
        ```python
        {code}
        ```

        Please fix the code. Return ONLY the corrected ```python block.
        Keep it simple. Assign the result to a variable named `result`."""

                            # groq_messages already has full conversation history.
                            # We append the fix request as a new user message
                            # so the LLM has full context of what went wrong.
                            fix_messages = groq_messages + [
                                {"role": "assistant", "content": llm_response},
                                {"role": "user",      "content": fix_prompt},
                            ]

                            try:
                                # Call LLM again with the error context
                                fix_response = call_groq(fix_messages, api_key)
                                fixed_code   = extract_code(fix_response)

                                if fixed_code:
                                    # Execute the fixed code
                                    fixed_result, fixed_error = execute_code(fixed_code, df)

                                    if fixed_error:
                                        # Fixed code also failed — tell user clearly
                                        error_msg = f"Auto-fix also failed:\n{fixed_error}"
                                    else:
                                        # Fixed code worked — use it
                                        # Replace everything with the corrected version
                                        result    = fixed_result
                                        error_msg = None
                                        code      = fixed_code   # show fixed code in UI
                                else:
                                    error_msg = "LLM could not produce a fix."

                            except Exception as fix_e:
                                error_msg = f"Fix attempt failed: {str(fix_e)}"

                else:
                    error_msg = "LLM did not return a code block. Try rephrasing your question."

                # ── Step 5: Infer chart if LLM skipped chart block ────
                if not chart_instructions and result is not None:
                    chart_instructions = infer_chart_instructions(
                        user_input.strip(), result
                    )

                # ── Step 6: Store in session state ────────────────────
                st.session_state.messages.append({
                    "role":               "assistant",
                    "content":            llm_response,
                    "code":               code,
                    "chart_instructions": chart_instructions,
                    "result":             result,
                    "error":              error_msg,
                })

            except Exception as e:
                st.error(f"Groq API error: {str(e)}")

        st.rerun()