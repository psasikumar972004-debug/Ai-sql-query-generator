"""
sql_generator.py
------------------
The core "AI" component of the project. Takes a plain-English business
question and, using the Groq API (free tier), produces:
    - a syntactically correct, schema-aware SQL query
    - a plain-English explanation of what the query does

The prompt gives the model the exact database schema (from
schema_explainer.py) so it cannot hallucinate table or column names, and
instructs it to return strict JSON so the rest of the app can parse it
reliably.
"""

import json
import os
import re
from groq import Groq

MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert SQL analyst assistant embedded in a business
intelligence tool. Business users who do NOT know SQL will ask you questions in
plain English about a database. You must:

1. Write a single, correct, read-only SQLite SELECT query that answers the question.
2. Only use the tables and columns given in the schema below - never invent any.
3. Prefer clear, well-formatted SQL with meaningful use of JOIN, WHERE, GROUP BY,
   and date functions where appropriate.
4. Never write INSERT, UPDATE, DELETE, DROP, ALTER, or any statement that is not
   a SELECT.

Database schema:
{schema}

Respond ONLY with valid JSON (no markdown fences, no commentary) in this exact
shape:
{{
  "sql": "<the SQL query, single statement, ending in a semicolon>",
  "explanation": "<2-3 sentence plain-English explanation of what the query does>",
  "assumptions": "<any assumptions you made to interpret the question, or empty string>"
}}
"""


def _get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Copy .env.example to .env and add your free key from "
            "https://console.groq.com/keys"
        )
    return Groq(api_key=api_key)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def generate_sql(question: str, schema_context: str) -> dict:
    """Call the LLM to translate a natural-language question into SQL.

    Returns a dict: {"sql": str, "explanation": str, "assumptions": str}
    Raises RuntimeError with a friendly message on any failure.
    """
    client = _get_client()
    system = SYSTEM_PROMPT.format(schema=schema_context)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"AI service call failed: {e}")

    raw_text = response.choices[0].message.content or ""
    cleaned = _strip_code_fences(raw_text)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RuntimeError(f"Model did not return valid JSON. Raw response:\n{raw_text}")

    for key in ("sql", "explanation"):
        if key not in parsed:
            raise RuntimeError(f"Model response missing required field '{key}'.")

    parsed.setdefault("assumptions", "")
    return parsed


def suggest_optimizations(sql: str, explain_plan: str) -> str:
    """Ask the LLM to review a query + its SQLite EXPLAIN QUERY PLAN output
    and suggest concrete optimizations (indexes, rewrites, etc.)."""
    client = _get_client()
    prompt = f"""Here is a SQL query and its SQLite EXPLAIN QUERY PLAN output.

Query:
{sql}

EXPLAIN QUERY PLAN:
{explain_plan}

In 2-4 short bullet points, suggest concrete optimizations (e.g. indexes to
add, query rewrites, avoiding SELECT *). If the query is already efficient,
say so briefly. Respond in plain text, no markdown headers."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()


if __name__ == "__main__":
    from schema_explainer import get_schema, schema_to_prompt_context

    schema = schema_to_prompt_context(get_schema("database/store.db"))
    result = generate_sql(
        "Find customers who purchased twice but haven't purchased in 90 days.",
        schema,
    )
    print(json.dumps(result, indent=2))
