"""
app.py
-------
AI SQL Query Generator + Data Explainer
A Streamlit app that lets business users ask questions in plain English and
get back SQL, an explanation, validated results, business insights, and
query-optimization suggestions.

Run:
    streamlit run app.py
"""

import os
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent / "src"))

from schema_explainer import get_schema, schema_to_prompt_context, schema_to_plain_english
from query_validator import validate_sql
from sql_generator import generate_sql, suggest_optimizations
from insights_generator import generate_insight

load_dotenv()

DB_PATH = str(Path(__file__).parent / "database" / "store.db")

st.set_page_config(page_title="AI SQL Query Generator", page_icon="🧠", layout="wide")

# ---------------------------------------------------------------- sidebar --
with st.sidebar:
    st.title("🧠 AI SQL Query Generator")
    st.caption("Business teams need data insights but may not know SQL.")

    if not Path(DB_PATH).exists():
        st.error("Database not found. Run: `python database/create_db.py`")
        st.stop()

    st.subheader("📋 Database schema")
    schema_tables = get_schema(DB_PATH)
    st.markdown(schema_to_plain_english(schema_tables))

    st.divider()
    st.subheader("💡 Example questions")
    examples = [
        "Find customers who purchased twice but haven't purchased in 90 days.",
        "What is the total revenue by city?",
        "Which 5 customers spent the most money overall?",
        "How many orders were cancelled or refunded in the last 60 days?",
        "Show monthly order volume for the last 6 months.",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["question"] = ex

    st.divider()
    if not os.environ.get("GROQ_API_KEY"):
        st.warning("No GROQ_API_KEY found. Add one to a `.env` file (see .env.example).")

# ------------------------------------------------------------------ main --
st.header("Ask a question about your data")
question = st.text_input(
    "e.g. Find customers who purchased twice but haven't purchased in 90 days.",
    key="question",
)
run = st.button("Generate & Run ▶", type="primary")

if run and question.strip():
    schema_context = schema_to_prompt_context(schema_tables)

    # 1. Generate SQL -------------------------------------------------
    with st.spinner("AI is writing the SQL query..."):
        try:
            t0 = time.time()
            result = generate_sql(question, schema_context)
            gen_time = time.time() - t0
        except RuntimeError as e:
            st.error(str(e))
            st.stop()

    sql = result["sql"].strip()

    st.subheader("1️⃣ Generated SQL")
    st.code(sql, language="sql")
    st.caption(f"Generated in {gen_time:.1f}s")

    st.subheader("2️⃣ Query explanation")
    st.write(result["explanation"])
    if result.get("assumptions"):
        st.info(f"**Assumptions made:** {result['assumptions']}")

    # 2. Validate -------------------------------------------------------
    st.subheader("3️⃣ Validation")
    validation = validate_sql(sql, DB_PATH)
    if not validation.is_valid:
        for err in validation.errors:
            st.error(f"❌ {err}")
        st.stop()
    else:
        st.success("✅ Query passed safety and schema checks (read-only, valid tables/columns).")
        for w in validation.warnings:
            st.warning(f"⚠️ {w}")

    # 3. Execute ----------------------------------------------------------
    st.subheader("4️⃣ Results")
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn)
    except sqlite3.Error as e:
        st.error(f"SQL execution error: {e}")
        st.stop()

    st.dataframe(df, use_container_width=True)
    st.caption(f"{len(df)} row(s) returned.")

    # 4. Business insights --------------------------------------------
    st.subheader("5️⃣ Business insights")
    if os.environ.get("GROQ_API_KEY"):
        with st.spinner("Summarizing the results..."):
            try:
                insight = generate_insight(
                    question, sql, list(df.columns), list(df.itertuples(index=False, name=None))
                )
                st.write(insight)
            except RuntimeError as e:
                st.error(str(e))
    else:
        st.info("Add an GROQ_API_KEY to see AI-generated business insights here.")

    # 5. Optimization suggestions --------------------------------------
    with st.expander("⚙️ Advanced: query validation & optimization suggestions"):
        try:
            plan_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
            plan_text = "\n".join(str(r) for r in plan_rows)
            st.code(plan_text or "No plan detail available.", language="text")
            if os.environ.get("GROQ_API_KEY"):
                with st.spinner("Checking for optimization opportunities..."):
                    tips = suggest_optimizations(sql, plan_text)
                    st.write(tips)
        except sqlite3.Error as e:
            st.warning(f"Could not generate query plan: {e}")

    conn.close()

elif run:
    st.warning("Please enter a question first.")
