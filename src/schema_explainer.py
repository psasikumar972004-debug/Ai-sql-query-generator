"""
schema_explainer.py
--------------------
Introspects a SQLite database and produces:
  1. A machine-readable schema description (fed to the LLM as context so it
     never "hallucinates" table/column names).
  2. A plain-English explanation of the schema for business users who don't
     know SQL.
"""

import sqlite3
from dataclasses import dataclass, field


@dataclass
class ColumnInfo:
    name: str
    type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references: str = ""


@dataclass
class TableInfo:
    name: str
    columns: list = field(default_factory=list)
    row_count: int = 0


def get_schema(db_path: str) -> list[TableInfo]:
    """Introspect the SQLite database and return structured schema info."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    tables = []
    for (table_name,) in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall():
        cols = []
        fk_map = {
            row[3]: f"{row[2]}.{row[4]}"
            for row in cur.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
        }
        for row in cur.execute(f"PRAGMA table_info({table_name})").fetchall():
            col_name = row[1]
            cols.append(
                ColumnInfo(
                    name=col_name,
                    type=row[2],
                    is_primary_key=bool(row[5]),
                    is_foreign_key=col_name in fk_map,
                    references=fk_map.get(col_name, ""),
                )
            )
        row_count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        tables.append(TableInfo(name=table_name, columns=cols, row_count=row_count))

    conn.close()
    return tables


def schema_to_prompt_context(tables: list[TableInfo]) -> str:
    """Compact schema description used inside the LLM prompt (keeps token
    usage low and gives the model exact, unambiguous table/column names)."""
    lines = []
    for t in tables:
        col_descs = []
        for c in t.columns:
            tag = ""
            if c.is_primary_key:
                tag = " [PK]"
            elif c.is_foreign_key:
                tag = f" [FK -> {c.references}]"
            col_descs.append(f"{c.name} ({c.type}){tag}")
        lines.append(f"Table {t.name} ({t.row_count} rows): " + ", ".join(col_descs))
    return "\n".join(lines)


def schema_to_plain_english(tables: list[TableInfo]) -> str:
    """Human-readable schema explanation for non-technical users."""
    out = []
    for t in tables:
        pk = next((c.name for c in t.columns if c.is_primary_key), "id")
        fks = [c for c in t.columns if c.is_foreign_key]
        desc = f"**{t.name}** — holds {t.row_count} records. Each row is uniquely identified by `{pk}`."
        if fks:
            links = ", ".join(f"`{c.name}` links to {c.references}" for c in fks)
            desc += f" It connects to other tables through: {links}."
        cols = ", ".join(f"`{c.name}`" for c in t.columns)
        desc += f" Columns: {cols}."
        out.append(desc)
    return "\n\n".join(out)


if __name__ == "__main__":
    schema = get_schema("database/store.db")
    print("--- Prompt context ---")
    print(schema_to_prompt_context(schema))
    print("\n--- Plain English ---")
    print(schema_to_plain_english(schema))
