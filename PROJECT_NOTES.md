# Project Notes — AI SQL Query Generator & Data Explainer

This document covers what the project does, how it was built end-to-end, the
real issues encountered while building and deploying it, and its honest
limitations. Useful for interview prep — recruiters often ask "what went
wrong and how did you fix it" more than "what went right."

---

## 1. Brief explanation

**The problem:** Business teams need answers from data but usually don't
know SQL, so every question becomes a request to an analyst. That's slow
for the business and repetitive for the analyst.

**The solution:** A web app where a user types a question in plain English
(e.g. *"Find customers who purchased twice but haven't purchased in 90
days"*) and the app:

1. Reads the real database schema so it knows exactly what tables/columns exist
2. Sends the question + schema to an LLM, which writes a SQL query and explains it
3. Validates that query for safety before running it (read-only, no destructive commands, only real tables)
4. Executes it against the database and shows the results
5. Sends the results back to the LLM to generate a plain-English business insight
6. Optionally reviews the query's execution plan and suggests optimizations

**In one sentence for an interview:** *"It's a safety-first natural language
interface to SQL — the AI writes the query, but a validation layer makes
sure it's never destructive and only touches real tables before anything
runs."*

---

## 2. Complete roadmap (how it was actually built)

| Phase | What was done |
|---|---|
| 1. Problem scoping | Picked the exact use case from the assignment brief: NL question in, SQL + explanation + insights out |
| 2. Database design | Designed a small e-commerce schema (`customers`, `orders`) with a foreign key relationship, generated realistic synthetic data with a fixed random seed for reproducibility |
| 3. Schema introspection | Built a module that reads the live SQLite schema (tables, columns, keys) and turns it into both a compact prompt-context string and a human-readable explanation |
| 4. AI SQL generation | Built a prompt that forces the model to only use real schema elements and return strict JSON (query + explanation + assumptions) |
| 5. Safety validation | Built a validator using `sqlparse` that rejects anything that isn't a single read-only SELECT, blocks destructive keywords, and checks referenced tables actually exist |
| 6. Business insights | Built a second AI call that takes the query results and produces a plain-English summary with a suggested next action |
| 7. Query optimization | Added `EXPLAIN QUERY PLAN` output review by the AI for optimization suggestions |
| 8. UI | Built the Streamlit front end tying all of the above together, with example-question shortcuts |
| 9. Provider migration | Originally built against Anthropic's Claude API, migrated to Google Gemini, then migrated again to Groq — all because of cost/access issues (see Issues below). This required no changes to the database, validator, or UI — only the two AI-calling modules needed edits, which is itself a useful design lesson (keep the LLM provider isolated behind a small interface) |
| 10. Local environment setup | Solved a series of Windows-specific environment issues (see below) to get it running end-to-end locally |
| 11. Documentation & publishing | Wrote the README, this notes file, and pushed to GitHub for the portfolio |

---

## 3. Main issues encountered (and how each was solved)

### Issue 1: `pandas` failed to install on Python 3.13
**Symptom:** `pip install -r requirements.txt` tried to compile pandas from
source using Meson and failed because Visual Studio build tools weren't
installed.
**Cause:** The pinned pandas version (`2.2.2`) predates full Python 3.13
support, so pip couldn't find a pre-built wheel and fell back to compiling
from source.
**Fix:** Changed `requirements.txt` to use `>=` version ranges instead of
pinned `==` versions, so pip installs the newest compatible pre-built wheel
instead of trying to compile an old one.

### Issue 2: Virtual environment creation failed with `Access is denied`
**Symptom:** `python -m venv venv` failed partway through with a
`WinError 5` on a file inside `venv\Include`.
**Cause:** The project folder was inside OneDrive's synced Desktop folder.
OneDrive actively locks files mid-sync, which conflicts with Python writing
many small files quickly during venv creation.
**Fix:** Moved the project entirely outside OneDrive (to `C:\Projects\...`).
This is a generally good practice for any local dev environment — keep
code you're actively running outside of cloud-sync folders.

### Issue 3: `(venv)` not appearing / packages installing to the wrong place
**Symptom:** After "activating" the venv, the prompt didn't show `(venv)`,
and packages ended up in the system Python instead.
**Cause:** Using the wrong activation command for the terminal type
(PowerShell needs `.\venv\Scripts\Activate.ps1`, not
`venv\Scripts\activate`), or running commands in a different Command Prompt
window than the one where the venv was activated.
**Fix:** Confirmed terminal type first, used the correct activation syntax,
and made sure every subsequent command (`pip install`, `streamlit run`) ran
in that same activated window.

### Issue 4: `ModuleNotFoundError` even after installing the package
**Symptom:** `pip install -r requirements.txt` reported success, but
running the app still said the module wasn't found.
**Cause:** Same root cause as Issue 3 — `pip install` and `streamlit run`
were run in two different terminal sessions, one with the venv active and
one without.
**Fix:** Always `cd` into the project folder and activate the venv fresh in
a single continuous terminal session before installing or running anything.

### Issue 5: Anthropic Claude API required payment setup
**Symptom:** Creating an API key on the Anthropic console asked for billing
details before issuing a key.
**Cause:** Anthropic's API doesn't currently offer a no-card free tier.
**Fix:** Migrated the two AI-calling modules to use a provider with a
genuinely free tier instead (first tried Google Gemini, settled on Groq).
Because the LLM-calling logic was isolated into just two files
(`sql_generator.py`, `insights_generator.py`), this migration didn't touch
the database, validator, or UI code at all.

### Issue 6: Wrong API key format pasted into `.env`
**Symptom:** The app reported the API key as missing even though a value
was present in `.env`.
**Cause:** A token copied from the wrong part of a Google page (an OAuth
session token, not the actual API key) was pasted in — it didn't match the
provider's real key format.
**Fix:** Went back to the provider's dedicated "API Keys" page and copied
the key using the page's own copy button, and verified the key's expected
prefix (e.g. Groq keys start with `gsk_`) before saving it.

### Issue 7: `.env` file accidentally saved as `.env.txt`
**Symptom:** The app couldn't find any environment variables at all.
**Cause:** Notepad silently appends `.txt` to files that don't already have
a recognized extension when saved through "Save As," and Windows hides
extensions by default so this went unnoticed.
**Fix:** Created and edited the file entirely from Command Prompt (`copy
.env.example .env`, then `notepad .env`), which avoids the Save As dialog
entirely, and turned on "File name extensions" in File Explorer's View tab
as a safety check.

---

## 4. Limitations of this project (be upfront about these in interviews)

- **Sample data only:** the database is synthetic data generated with a
  fixed random seed, not a real production dataset. It's designed to be
  small and reproducible for demo purposes, not to reflect real-world data
  volume or messiness.
- **Single database engine:** only SQLite is supported. Real business data
  usually lives in PostgreSQL, MySQL, or a cloud warehouse — supporting
  those would need a different connection layer and possibly different SQL
  dialect handling in the validator.
- **No user authentication or row-level access control:** anyone using the
  app can query any table. A production version would need to restrict
  which tables/columns a given user's role can see.
- **No conversation memory:** each question is handled independently: the
  app doesn't remember earlier questions in the session, so follow-ups like
  "now break that down by city" wouldn't work without re-stating context.
- **Free-tier rate limits:** Groq's free tier has request-per-minute limits,
  so heavy concurrent use would hit throttling — fine for a portfolio demo,
  not yet production-scale.
- **Validator is pattern-based, not a full SQL parser guarantee:** the
  safety layer catches the common destructive patterns and unknown tables,
  but a sufficiently unusual SQL construct could theoretically slip past
  simple keyword/table checks. A production system would likely also run
  queries against a read-only database user/role as a second layer of
  defense, not rely on the validator alone.
- **No automated test suite:** the modules were manually tested during
  development, but there isn't a `pytest` suite yet to catch regressions
  automatically.
- **No caching:** identical questions re-call the AI API every time, which
  is slower and more costly than caching repeated queries would be.

---

## 5. Possible next steps to address these limitations

- Add a read-only database user/role as a second enforcement layer, independent of the Python-side validator
- Support PostgreSQL/MySQL via a pluggable connection layer
- Add basic session-based conversation memory for follow-up questions
- Add a `pytest` suite covering the validator's edge cases and the schema explainer
- Add response caching for repeated identical questions
- Add role-based table/column access restrictions
- Swap in a production-grade LLM provider with higher rate limits once the project needs to scale beyond a personal demo
