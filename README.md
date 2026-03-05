# DataChat — Natural Language Analytics Assistant

A Streamlit application that lets you query a sales dataset using plain English. Type a question, get back a result table and a chart. No SQL, no formulas.

Built as part of my transition from BI/Analytics into AI Engineering.

---

## Why I built this

I have spent three years working with data in Databricks and Snowflake — writing SQL, building dashboards, and helping business teams understand their numbers. The question I kept hearing was: *"Can I just ask it in plain English?"*

This project is my attempt to answer that properly. Not with a wrapper that dumps your data into an LLM and hopes for the best, but with an architecture that keeps your data local and uses the LLM only for what it is actually good at — understanding language and writing code.

---

## How it works

The application follows a Text-to-Pandas pattern:

1. When you upload a CSV, the app extracts only the schema — column names, data types, a two-row sample, and the date range. No actual values leave your machine.
2. That metadata is sent to a Groq-hosted LLaMA 3.1 model along with your question.
3. The model writes a pandas expression to answer the question.
4. The app executes that code locally against your full dataset.
5. The result is displayed as a table and auto-rendered as a chart.

The LLM never sees your revenue figures, customer names, or any row-level data. It only sees the structure of the data — enough to write correct pandas code, nothing more.

---

## Self-healing execution

One problem I ran into early: LLMs occasionally write pandas code that fails — wrong column name, incorrect method chain, type mismatch. The naive solution is to show an error and stop.

Instead, I built a retry loop. When the first execution fails, the app sends the error message back to the LLM alongside the original code and asks it to fix the issue. In most cases this resolves the problem without the user seeing anything. If the retry also fails, a plain-English error message is shown — not a raw Python traceback.

This pattern — observing the result of an action and self-correcting — is referred to as an agentic loop. It is a common pattern in production AI systems and something I wanted to understand by building it from scratch rather than using a framework that abstracts it away.

---

## Architecture

```
User question
     ↓
Schema extraction (pandas)       ← runs locally
     ↓
System prompt + metadata         ← only this goes to the API
     ↓
Groq API / LLaMA 3.1             ← writes pandas code
     ↓
Code extraction (regex)
     ↓
Local execution (exec)           ← runs locally on full dataset
     ↓
[if error] → retry with error context → re-execute
     ↓
Result rendered as table + chart
```

---

## Tech stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| LLM API | Groq (LLaMA 3.1 8B Instant) |
| Data | Pandas |
| Charts | Plotly Express |
| Language | Python 3.11 |

---

## What I learned building this

**Prompt engineering is more constrained than I expected.** Smaller models like LLaMA 3.1 8B do not reliably follow complex multi-block output formats. I originally asked the model to return both a pandas code block and a chart specification block. The chart block was frequently skipped. The fix was to infer chart type from the user's question in Python rather than depending on the model to output it — a reminder that the simpler the model's task, the more reliable the output.

**Security decisions have to be made deliberately.** The metadata-only approach was a conscious choice, not an afterthought. Sending a full CSV to an external API creates a data exposure risk that would be unacceptable in any real analytics context. Separating what the LLM needs to know (structure) from what it does not need to know (values) is a pattern I intend to carry into future projects.

**Local code execution needs guardrails.** Using Python's `exec()` to run LLM-generated code is powerful but carries risk. I implemented a basic safety check that blocks keywords like `__import__`, `open()`, and `os.` before execution. This is not a production-grade sandbox, but it demonstrates awareness of the attack surface.

---

## Running locally

```bash
# Clone the repository
git clone https://github.com/piyushgithub8/datachat.git
cd datachat

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Generate sample data
python generate_data.py

# Run the app
streamlit run app.py
```

You will need a Groq API key. Free accounts are available at [console.groq.com](https://console.groq.com). Add it in the sidebar when the app opens.

---

## Sample questions to try

- What is total revenue by region?
- Show me a scatter plot of revenue vs profit by region as bubbles
- Which sales rep generated the most profit in 2024?
- What is the average discount given per product category?
- Show monthly revenue trend as a line chart
- How many orders had a discount greater than 15%?

---

## What is next

This project handles structured CSV data. The next version will connect to a Snowflake warehouse and generate SQL instead of pandas — closer to how analytics teams actually work.

I am also building a separate RAG pipeline for querying unstructured documents, which covers the other dominant pattern in AI engineering work.
