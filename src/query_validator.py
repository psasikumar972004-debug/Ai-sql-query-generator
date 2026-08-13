"""
query_validator.py
--------------------
Validates AI-generated SQL before it is ever executed against the database.

Two layers of protection:
  1. Safety layer  - blocks any statement that could mutate or damage data
                      (INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/ATTACH ...).
                      Only a single read-only SELECT statement is allowed.
  2. Schema layer   - checks that every table referenced in the query
                       actually exists in the connected database, catching
                       hallucinated table/column names before execution.
"""

import re
import sqlite3
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML, Name

BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "ATTACH", "DETACH", "REPLACE", "CREATE", "PRAGMA", "VACUUM",
}


class ValidationResult:
    def __init__(self, is_valid: bool, errors=None, warnings=None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self):
        return self.is_valid


def _extract_table_names(sql: str) -> set[str]:
    """Best-effort extraction of table names following FROM / JOIN."""
    tables = set()
    tokens = sqlparse.parse(sql)[0].flatten()
    token_list = list(tokens)
    for i, tok in enumerate(token_list):
        if tok.ttype is Keyword and tok.value.upper() in ("FROM", "JOIN"):
            # walk forward to find the next identifier-like token
            for nxt in token_list[i + 1:]:
                if nxt.is_whitespace:
                    continue
                if nxt.ttype in (Name,) or nxt.ttype.__repr__().startswith("Token.Literal.String"):
                    name = nxt.value.strip('`"[]')
                    if name and name.upper() not in BLOCKED_KEYWORDS:
                        tables.add(name.lower())
                break
    return tables


def validate_sql(sql: str, db_path: str) -> ValidationResult:
    errors = []
    warnings = []

    if not sql or not sql.strip():
        return ValidationResult(False, ["Empty query generated."])

    # 1. Must be a single statement
    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True)]
    if len(statements) != 1:
        errors.append("Only a single SQL statement is allowed.")

    stmt = statements[0] if statements else None
    first_token = stmt.token_first(skip_cm=True) if stmt else None

    # 2. Must be a SELECT (read-only)
    if not first_token or first_token.ttype is not DML or first_token.value.upper() != "SELECT":
        errors.append("Only SELECT statements are permitted. The AI attempted a non-read-only query.")

    # 3. No blocked keywords anywhere in the statement (defense in depth)
    upper_sql = sql.upper()
    for kw in BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper_sql):
            errors.append(f"Blocked keyword detected: {kw}")

    # 4. No multiple statements via semicolon injection
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        errors.append("Statement chaining (multiple statements) is not allowed.")

    if errors:
        return ValidationResult(False, errors, warnings)

    # 5. Schema validation - do the referenced tables actually exist?
    try:
        conn = sqlite3.connect(db_path)
        real_tables = {
            row[0].lower()
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
    except sqlite3.Error as e:
        return ValidationResult(False, [f"Could not read schema: {e}"])

    referenced = _extract_table_names(sql)
    unknown = referenced - real_tables
    if unknown:
        errors.append(f"Query references unknown table(s): {', '.join(unknown)}")

    # 6. Soft warning: no LIMIT on a SELECT * can be slow on large tables
    if "select *" in sql.lower() and "limit" not in sql.lower():
        warnings.append("Consider adding a LIMIT clause for large result sets.")

    return ValidationResult(len(errors) == 0, errors, warnings)


if __name__ == "__main__":
    tests = [
        "SELECT * FROM customers LIMIT 10;",
        "DROP TABLE customers;",
        "SELECT * FROM customers; DELETE FROM orders;",
        "SELECT * FROM not_a_real_table;",
    ]
    for t in tests:
        r = validate_sql(t, "database/store.db")
        print(t, "->", "VALID" if r else f"INVALID: {r.errors}")
