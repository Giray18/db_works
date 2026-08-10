"""The 3 agent tools: list_gold_tables, get_table_schema, run_sql.

run_sql is the only one that touches the warehouse, and the only one that needs to be
trusted with untrusted, LLM-generated SQL text. The validation here is an application-level
second line of defense - the real boundary should be a Unity Catalog grant restricting the
connecting principal to SELECT on workspace.dev_finance_cockpit_gold only (see
rag_agent/README.md "Safety model" for why that's not meaningfully applied by default on a
single-user Free Edition workspace, and what to do about it if this ever runs under a
separate service principal).
"""

import re

import db
from schema_catalog import CATALOG, TABLE_NAMES, get_table, list_tables_summary

ALLOWED_SCHEMA = "workspace.dev_finance_cockpit_gold"
ROW_LIMIT = 500
QUERY_TIMEOUT_S = 30

_DISALLOWED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|COPY|USE)\b",
    re.IGNORECASE,
)
_LEADING_STATEMENT = re.compile(r"^\s*(WITH\b.*?\)\s*SELECT|\s*SELECT)\b", re.IGNORECASE | re.DOTALL)
_TABLE_REF = re.compile(r"\b(?:FROM|JOIN)\s+([`\"\[]?[\w.]+[`\"\]]?)", re.IGNORECASE)
_CTE_NAME = re.compile(r"\b(\w+)\s+AS\s*\(", re.IGNORECASE)
_LIMIT_CLAUSE = re.compile(r"\bLIMIT\s+(\d+)\b", re.IGNORECASE)


def list_gold_tables() -> dict:
    return {"tables": list_tables_summary()}


def get_table_schema(table_name: str) -> dict:
    table = get_table(table_name)
    if table is None:
        return {
            "is_error": True,
            "error": f"Unknown table '{table_name}'. Valid gold table names: {sorted(TABLE_NAMES)}",
        }
    return {
        "name": table.name,
        "kind": table.kind,
        "grain": table.grain,
        "business_description": table.business_description,
        "primary_key": table.primary_key,
        "foreign_keys": [
            {"column": fk.column, "references_table": fk.references_table, "references_column": fk.references_column}
            for fk in table.foreign_keys
        ],
        "columns": [{"name": c.name, "type": c.type, "description": c.description} for c in table.columns],
    }


def _validate_select_only(query: str) -> str | None:
    if ";" in query.rstrip().rstrip(";"):
        return "Statement stacking (multiple ';'-separated statements) is not allowed."
    if not _LEADING_STATEMENT.match(query.strip()):
        return "Only SELECT (optionally with a leading WITH ... CTE) statements are allowed."
    if _DISALLOWED_KEYWORDS.search(query):
        return "Query contains a disallowed DDL/DML keyword (INSERT/UPDATE/DELETE/MERGE/CREATE/DROP/ALTER/TRUNCATE/GRANT/REVOKE/COPY/USE)."
    return None


def _validate_table_allowlist(query: str) -> str | None:
    cte_names = {name.lower() for name in _CTE_NAME.findall(query)}
    for raw_ref in _TABLE_REF.findall(query):
        ref = raw_ref.strip("`\"[] ")
        bare_name = ref.rsplit(".", 1)[-1]
        if bare_name.lower() in cte_names:
            continue
        if bare_name not in TABLE_NAMES:
            return (
                f"Query references table '{ref}', which is not in the allowed gold schema "
                f"({ALLOWED_SCHEMA}). Allowed tables: {sorted(TABLE_NAMES)}"
            )
        if "." in ref:
            prefix = ref.rsplit(".", 1)[0].lower()
            if prefix not in (ALLOWED_SCHEMA.lower(), ALLOWED_SCHEMA.split(".")[-1].lower()):
                return f"Query references '{ref}' outside {ALLOWED_SCHEMA} - only the gold schema is queryable."
    return None


def _enforce_row_cap(query: str) -> str:
    existing = _LIMIT_CLAUSE.search(query)
    if existing:
        limit_value = int(existing.group(1))
        if limit_value > ROW_LIMIT:
            return _LIMIT_CLAUSE.sub(f"LIMIT {ROW_LIMIT}", query)
        return query
    return query.rstrip().rstrip(";") + f" LIMIT {ROW_LIMIT}"


def run_sql(query: str) -> dict:
    error = _validate_select_only(query)
    if error:
        return {"is_error": True, "error": error}
    error = _validate_table_allowlist(query)
    if error:
        return {"is_error": True, "error": error}

    capped_query = _enforce_row_cap(query)
    try:
        columns, rows = db.run_query(capped_query, timeout_s=QUERY_TIMEOUT_S)
    except db.QueryTimeout as e:
        return {"is_error": True, "error": str(e)}
    except Exception as e:  # noqa: BLE001 - genuinely any warehouse/SQL error should be recoverable, not a crash
        return {"is_error": True, "error": f"Query failed: {e}"}

    return {"columns": columns, "rows": rows, "row_count": len(rows)}


TOOL_DEFINITIONS = [
    {
        "name": "list_gold_tables",
        "description": (
            "Lists all gold-layer tables available to query (dimensions, facts, and KPI "
            "views), each with its grain and a one-line business description. Call this "
            "first to orient yourself before asking for a specific table's full schema."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_table_schema",
        "description": (
            "Returns the full column list (with types and descriptions), primary key, and "
            "foreign keys for one gold table. Always call this for every table you plan to "
            "reference in SQL before writing the query - never guess column names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "One of the gold table names returned by list_gold_tables, e.g. fact_invoices.",
                }
            },
            "required": ["table_name"],
        },
    },
    {
        "name": "run_sql",
        "description": (
            "Executes a single read-only SELECT statement against the gold schema "
            f"({ALLOWED_SCHEMA}) and returns the resulting rows. DDL/DML, multiple statements, "
            "and references to any table outside the gold schema are rejected. Results are "
            f"capped at {ROW_LIMIT} rows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": f"A single SELECT (or WITH ... SELECT) statement against {ALLOWED_SCHEMA} tables.",
                }
            },
            "required": ["query"],
        },
    },
]

DISPATCH = {
    "list_gold_tables": lambda **kwargs: list_gold_tables(),
    "get_table_schema": lambda table_name: get_table_schema(table_name),
    "run_sql": lambda query: run_sql(query),
}
