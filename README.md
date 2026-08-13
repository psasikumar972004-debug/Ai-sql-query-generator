# 🧠 AI SQL Query Generator + Data Explainer

Turn plain-English business questions into validated SQL, run them, and get
back a business-readable insight — no SQL knowledge required.

> **Business problem:** Business teams need data insights but may not know SQL.
> They either wait on an analyst for every question, or don't ask the question
> at all. This project shows how an LLM can sit between a non-technical user
> and a database, safely.

---

## 🎥 Demo

**User asks:**
> "Find customers who purchased twice but haven't purchased in 90 days."

**The app returns:**
1. A generated, schema-aware SQL query
2. A plain-English explanation of the query
3. A validation report (safety checks + schema checks)
4. The actual query results, run against a live SQLite database
5. A 3–5 sentence business insight with a suggested next action
6. Optional query-optimization suggestions (EXPLAIN QUERY PLAN reviewed by the AI)

![App screenshot placeholder](screenshots/demo_1.png)
*(Add your own screenshots here after running the app — see [Screenshots](#-screenshots) below)*

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   User question   │────▶│  Schema Explainer  │────▶│   SQL Generator   │
│  (plain English)  │     │  (introspects DB)  │     │  (Groq API)     │
└─────────────────┘     └──────────────────┘     └─────────┬─────────┘
                                                             │ generated SQL
                                                             ▼
                                                   ┌───────────────────┐
                                                   │  Query Validator   │
                                                   │ (safety + schema)  │
                                                   └─────────┬─────────┘
                                                             │ validated SQL
                                                             ▼
                                                   ┌───────────────────┐
                                                   │  SQLite Database   │
                                                   │  (execute query)   │
                                                   └─────────┬─────────┘
                                                             │ result rows
                                                             ▼
                                                   ┌───────────────────┐
                                                   │ Insights Generator │
                                                   │  (Groq API)      │
                                                   └───────────────────┘
```

**Why the validator matters:** an LLM can occasionally hallucinate a column
name or, worse, write a destructive statement. Every generated query is
checked against the *real* database schema and restricted to read-only
`SELECT` statements before it is ever executed — the AI never gets direct
write access to the database.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Natural language → SQL** | Ask a question in plain English, get back a correct SQLite query |
| **Query explanation** | Every query comes with a 2–3 sentence explanation of what it does |
| **Database schema understanding** | The AI is given the real schema (tables, columns, keys) so it never invents column names |
| **Query validation** | Blocks destructive statements (DROP/DELETE/UPDATE/etc.), enforces single read-only SELECT, checks tables exist |
| **Business insights** | Converts raw result rows into a plain-English takeaway with a suggested next action |
| **Query optimization suggestions** | Runs `EXPLAIN QUERY PLAN` and has the AI suggest indexes/rewrites |
| **Example question shortcuts** | One-click example queries in the sidebar for quick demos |

---

## 🛠️ Tech stack

- **Python 3.10+**
- **Streamlit** — interactive web UI
- **SQLite** — lightweight, zero-setup sample database
- **Groq API (Llama 3.3 70B)** — natural language understanding, SQL generation, insight generation
- **sqlparse** — SQL parsing for the safety/validation layer
- **pandas** — result formatting and display

**Skills demonstrated:** SQL · Python · LLM prompt engineering · database schema
design · data validation/safety patterns · analytics automation · Streamlit app development

---

## 📁 Project structure

```
ai-sql-query-generator/
├── app.py                      # Streamlit app (entry point)
├── requirements.txt
├── .env.example                 # Template for your API key
├── database/
│   ├── create_db.py             # Generates the sample SQLite database
│   └── store.db                 # Sample e-commerce database (60 customers, ~176 orders)
├── src/
│   ├── schema_explainer.py      # Introspects DB schema, explains it in plain English
│   ├── query_validator.py       # Safety + schema validation for AI-generated SQL
│   ├── sql_generator.py         # Natural language → SQL via Groq API
│   └── insights_generator.py    # Result rows → business insight via Groq API
├── screenshots/                 # App screenshots for this README
└── .streamlit/config.toml       # UI theme
```

---

## 🚀 Setup & run locally

1. **Clone the repo**
   ```bash
   git clone https://github.com/<your-username>/ai-sql-query-generator.git
   cd ai-sql-query-generator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your free Groq API key**
   ```bash
   cp .env.example .env
   # then edit .env and paste your key from https://console.groq.com/keys (free, no card required)
   ```

4. **Generate the sample database** (already included, but you can regenerate it)
   ```bash
   python database/create_db.py
   ```

5. **Run the app**
   ```bash
   streamlit run app.py
   ```

6. Open the local URL Streamlit prints (usually `http://localhost:8501`) and
   try one of the example questions in the sidebar.

---

## 🗄️ Sample database schema

```sql
customers (customer_id PK, name, email, city, signup_date)
orders    (order_id PK, customer_id FK -> customers, order_date, amount, status)
```

Synthetic data is generated with a fixed random seed so results are
reproducible: 60 customers across 7 Indian cities, and ~176 orders spread
across the last 400 days with realistic status values (`completed`,
`cancelled`, `refunded`).

---

## 🔒 Safety design

This is the part of the project I'd highlight most in an interview — letting
an LLM generate SQL against a real database is only safe if you constrain it:

- The AI is only ever asked for a **single SELECT statement**
- Every generated query is parsed with `sqlparse` and checked for blocked
  keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, etc.)
- Statement chaining via semicolons is rejected outright
- Every table referenced in the query is checked against the live schema —
  if the AI references a table that doesn't exist, the query is rejected
  before execution, not after

---

## 🧩 Example questions to try

- "Find customers who purchased twice but haven't purchased in 90 days."
- "What is the total revenue by city?"
- "Which 5 customers spent the most money overall?"
- "How many orders were cancelled or refunded in the last 60 days?"
- "Show monthly order volume for the last 6 months."

---

## 📸 Screenshots

Add screenshots of the running app here before publishing to GitHub:

1. Run `streamlit run app.py`
2. Ask a question and take a screenshot of the full result flow (SQL →
   explanation → validation → results → insight)
3. Save the image(s) into the `screenshots/` folder
4. Reference them in this README, e.g. `![Query flow](screenshots/query_flow.png)`

---

## 🔮 Future enhancements

- Support for PostgreSQL/MySQL in addition to SQLite
- Query history and saved reports
- Chart generation alongside table results
- User authentication and role-based table access
- Caching identical questions to reduce API calls

---

## 👤 Author

**Sasikumar** — B.Tech Information Technology, Data Analytics & Data Science aspirant
[LinkedIn](#) · [GitHub](#)

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
