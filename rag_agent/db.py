"""Thin wrapper around databricks-sql-connector for the one shared SQL warehouse.

Auth reuses the same `databricks auth login` OAuth profile the repo already relies on for
`databricks bundle deploy` (see scripts/profile_bronze_delta_tables.py for the same pattern
applied to Databricks Connect) - no separate PAT is needed as long as that profile exists.
"""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from databricks import sql
from databricks.sdk.core import Config

_SERVER_HOSTNAME = os.environ["DATABRICKS_SERVER_HOSTNAME"]
_HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
_TOKEN = os.environ.get("DATABRICKS_TOKEN")  # optional PAT fallback, see rag_agent/README.md
_CONFIG_PROFILE = os.environ.get("DATABRICKS_CONFIG_PROFILE")  # optional, else SDK default resolution

# Sets the session's default catalog/schema to the gold layer so tool-generated SQL can use
# bare table names (e.g. "dim_department") matching schema_catalog.py, not just fully-qualified
# ones - matches resources/schemas.yml's gold_schema.
_CATALOG = os.environ.get("DATABRICKS_CATALOG", "workspace")
_GOLD_SCHEMA = os.environ.get("DATABRICKS_GOLD_SCHEMA", "dev_finance_cockpit_gold")


class QueryTimeout(Exception):
    pass


def _connect():
    if _TOKEN:
        return sql.connect(
            server_hostname=_SERVER_HOSTNAME,
            http_path=_HTTP_PATH,
            access_token=_TOKEN,
            catalog=_CATALOG,
            schema=_GOLD_SCHEMA,
        )
    cfg = Config(profile=_CONFIG_PROFILE) if _CONFIG_PROFILE else Config()
    return sql.connect(
        server_hostname=_SERVER_HOSTNAME,
        http_path=_HTTP_PATH,
        credentials_provider=lambda: cfg.authenticate,
        catalog=_CATALOG,
        schema=_GOLD_SCHEMA,
    )


def run_query(query: str, timeout_s: int = 30) -> tuple[list[str], list[dict]]:
    """Executes `query` against the warehouse. Returns (column_names, rows_as_dicts).

    Raises whatever the connector raises on a SQL error - the caller (tools.run_sql) is
    responsible for turning that into a recoverable tool_result rather than crashing.

    The connector has no built-in per-statement timeout, so this enforces one client-side:
    the query runs on a worker thread, and if it doesn't finish in `timeout_s`, the cursor is
    cancelled (best-effort - a Databricks statement can keep running server-side briefly after
    cancel) and QueryTimeout is raised instead of blocking the caller indefinitely.
    """
    with _connect() as conn:
        with conn.cursor() as cursor:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(cursor.execute, query)
                try:
                    future.result(timeout=timeout_s)
                except FutureTimeoutError:
                    cursor.cancel()
                    raise QueryTimeout(f"Query did not complete within {timeout_s}s and was cancelled.")
            columns = [c[0] for c in cursor.description] if cursor.description else []
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return columns, rows
