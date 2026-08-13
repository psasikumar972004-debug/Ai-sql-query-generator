"""
insights_generator.py
-----------------------
Takes the results of an executed SQL query and asks the LLM to summarize
them as a short, decision-useful business insight - the part that turns a
table of numbers into something a non-technical stakeholder can act on.
"""

import os
from groq import Groq

MODEL_NAME = "llama-3.3-70b-versatile"


def generate_insight(question: str, sql: str, columns: list[str], rows: list[tuple]) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. Get a free key at "
            "https://console.groq.com/keys"
        )

    client = Groq(api_key=api_key)

    preview_rows = rows[:20]
    table_preview = " | ".join(columns) + "\n"
    table_preview += "\n".join(" | ".join(str(v) for v in r) for r in preview_rows)

    prompt = f"""A business user asked: "{question}"

This SQL was run to answer it:
{sql}

It returned {len(rows)} row(s). Here is a preview of the results (up to 20 rows):

{table_preview}

Write a short business insight (3-5 sentences) that:
- Directly answers the original question in plain English
- Highlights the key number(s) or pattern in the data
- Suggests one concrete, actionable next step for the business team

Do not restate the SQL. Write for someone with no technical background."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()
