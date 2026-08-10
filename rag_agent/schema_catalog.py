"""Hand-maintained metadata for the 15 gold tables in workspace.dev_finance_cockpit_gold.

This is the agent's "retrieval corpus": grain, columns/types, keys, FK relationships and
business notes, transcribed from the @dp.table/@dp.materialized_view comments in
transformations/*.py plus column types pulled from information_schema.columns (Spark infers
types at runtime, so they aren't visible in the Python source).

Keep this in sync with transformations/*.py: any column/FK change there must be mirrored here
in the same change, or the agent's tools will describe a schema that no longer matches reality.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ForeignKey:
    column: str
    references_table: str
    references_column: str


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    description: str = ""


@dataclass(frozen=True)
class TableSchema:
    name: str
    kind: str  # "dimension" | "fact" | "kpi_view"
    grain: str
    business_description: str
    columns: list[Column]
    primary_key: str
    foreign_keys: list[ForeignKey] = field(default_factory=list)


CATALOG: dict[str, TableSchema] = {
    t.name: t
    for t in [
        TableSchema(
            name="dim_department",
            kind="dimension",
            grain="One row per department_id.",
            business_description="Department dimension.",
            primary_key="department_id",
            columns=[
                Column("department_id", "string"),
                Column("department_name", "string"),
            ],
        ),
        TableSchema(
            name="dim_supplier",
            kind="dimension",
            grain="One row per supplier_id.",
            business_description="Supplier dimension.",
            primary_key="supplier_id",
            columns=[
                Column("supplier_id", "string"),
                Column("supplier_name", "string"),
                Column("supplier_city", "string"),
            ],
        ),
        TableSchema(
            name="dim_cpv",
            kind="dimension",
            grain="One row per cpv_code.",
            business_description="CPV (Common Procurement Vocabulary) procurement-category dimension.",
            primary_key="cpv_code",
            columns=[
                Column("cpv_code", "string"),
                Column("cpv_description", "string"),
            ],
        ),
        TableSchema(
            name="dim_date",
            kind="dimension",
            grain="One row per calendar day, 2020-01-01 to 2035-12-31.",
            business_description=(
                "Calendar dimension. Relate any fact date column (issue_date, due_date, "
                "payment_date, signature_date, order_date, ...) to this table's date column "
                "for calendar breakdowns (year/quarter/month/day-of-week)."
            ),
            primary_key="date",
            columns=[
                Column("date", "date"),
                Column("year", "int"),
                Column("quarter", "int"),
                Column("month", "int"),
                Column("month_name", "string"),
                Column("day", "int"),
                Column("day_of_week_name", "string"),
                Column("is_weekend", "boolean"),
            ],
        ),
        TableSchema(
            name="dim_project",
            kind="dimension",
            grain="One row per project_id.",
            business_description=(
                "Project dimension. Carries its own year column (the project's budget/planning "
                "year) - useful for a 'this year' filter on facts that don't carry year directly."
            ),
            primary_key="project_id",
            foreign_keys=[
                ForeignKey("department_id", "dim_department", "department_id"),
                ForeignKey("cpv_code", "dim_cpv", "cpv_code"),
            ],
            columns=[
                Column("project_id", "string"),
                Column("project_name", "string"),
                Column("project_status", "string"),
                Column("funding_source", "string"),
                Column("funding_type", "string"),
                Column("eu_program", "string"),
                Column("year", "int", "The project's budget/planning year."),
                Column("department_id", "string"),
                Column("cpv_code", "string"),
            ],
        ),
        TableSchema(
            name="dim_contract",
            kind="dimension",
            grain="One row per contract_id.",
            business_description=(
                "Contract dimension. Dollar measures live in fact_contract_financials, not here. "
                "current_deadline = coalesce(latest signed annex deadline, original contract_deadline)."
            ),
            primary_key="contract_id",
            foreign_keys=[
                ForeignKey("project_id", "dim_project", "project_id"),
                ForeignKey("procedure_id", "dim_procedure", "procedure_id"),
                ForeignKey("supplier_id", "dim_supplier", "supplier_id"),
            ],
            columns=[
                Column("contract_id", "string"),
                Column("project_id", "string"),
                Column("budget_item_id", "string"),
                Column("procedure_id", "string"),
                Column("supplier_id", "string"),
                Column("signature_date", "date"),
                Column("contract_deadline", "date", "Original contract deadline before any annex."),
                Column("contract_status", "string"),
                Column("current_deadline", "date", "Effective deadline after applying any signed annex."),
            ],
        ),
        TableSchema(
            name="dim_procedure",
            kind="dimension",
            grain="One row per procedure_id.",
            business_description="Procurement procedure dimension.",
            primary_key="procedure_id",
            foreign_keys=[
                ForeignKey("project_id", "dim_project", "project_id"),
                ForeignKey("cpv_code", "dim_cpv", "cpv_code"),
            ],
            columns=[
                Column("evidence_number", "string"),
                Column("procedure_id", "string"),
                Column("project_id", "string"),
                Column("procedure_type", "string"),
                Column("publication_date", "date"),
                Column("selection_decision_date", "date"),
                Column("procedure_status", "string"),
                Column("cpv_code", "string"),
                Column("planned_quarter", "string"),
            ],
        ),
        TableSchema(
            name="fact_invoices",
            kind="fact",
            grain="One row per invoice_id.",
            business_description=(
                "Invoice fact. issue_date/due_date/payment_date each relate to dim_date - pick "
                "one when joining, since Power BI only allows one active date relationship per fact."
            ),
            primary_key="invoice_id",
            foreign_keys=[
                ForeignKey("purchase_order_id", "fact_purchase_orders", "purchase_order_id"),
                ForeignKey("contract_id", "dim_contract", "contract_id"),
                ForeignKey("project_id", "dim_project", "project_id"),
            ],
            columns=[
                Column("invoice_id", "string"),
                Column("purchase_order_id", "string"),
                Column("contract_id", "string"),
                Column("project_id", "string"),
                Column("issue_date", "date"),
                Column("due_date", "date"),
                Column("payment_date", "date", "Null if not yet paid."),
                Column("invoice_amount", "double"),
                Column("currency", "string"),
                Column("payment_status", "string", "Croatian label, e.g. 'Placeno' (Paid)."),
                Column("invoice_status", "string"),
                Column("days_late", "int", "datediff(payment_date, due_date); null if unpaid."),
            ],
        ),
        TableSchema(
            name="fact_purchase_orders",
            kind="fact",
            grain="One row per purchase_order_id.",
            business_description="Purchase order fact. order_date relates to dim_date.",
            primary_key="purchase_order_id",
            foreign_keys=[
                ForeignKey("contract_id", "dim_contract", "contract_id"),
                ForeignKey("project_id", "dim_project", "project_id"),
            ],
            columns=[
                Column("purchase_order_id", "string"),
                Column("contract_id", "string"),
                Column("project_id", "string"),
                Column("order_date", "date"),
                Column("order_amount", "double"),
                Column("order_description", "string"),
            ],
        ),
        TableSchema(
            name="fact_contract_financials",
            kind="fact",
            grain="One row per contract_id (1:1 with dim_contract).",
            business_description=(
                "total_contract_value = contract_amount + total_annex_adjustments - the "
                "contract consolidation rule. Join dim_contract for project/supplier context."
            ),
            primary_key="contract_id",
            foreign_keys=[ForeignKey("contract_id", "dim_contract", "contract_id")],
            columns=[
                Column("contract_id", "string"),
                Column("contract_amount", "double", "Original signed contract amount."),
                Column("total_annex_adjustments", "double", "Sum of amount changes from signed annexes."),
                Column("annex_count", "bigint"),
                Column("total_contract_value", "double", "contract_amount + total_annex_adjustments."),
            ],
        ),
        TableSchema(
            name="fact_procurement_bids",
            kind="fact",
            grain="One row per bid_id (every bid, not just the winner).",
            business_description=(
                "Every bid, not just the winner - use to analyze win rate and competitiveness "
                "by supplier via is_awarded."
            ),
            primary_key="bid_id",
            foreign_keys=[
                ForeignKey("procedure_id", "dim_procedure", "procedure_id"),
                ForeignKey("supplier_id", "dim_supplier", "supplier_id"),
            ],
            columns=[
                Column("bid_id", "string"),
                Column("procedure_id", "string"),
                Column("supplier_id", "string"),
                Column("bid_amount", "double"),
                Column("bid_status", "string"),
                Column("is_awarded", "boolean", "True for the single winning bid of a procedure."),
            ],
        ),
        TableSchema(
            name="fact_procurement_performance",
            kind="fact",
            grain="One row per procedure_id (1:1 with dim_procedure).",
            business_description=(
                "procurement_savings = estimated_value - awarded_bid_amount, the procurement "
                "savings KPI at raw grain. Do not average a derived savings_pct across rows - "
                "recompute as SUM(procurement_savings)/SUM(estimated_value) when aggregating "
                "(e.g. by department or year); this table has no year column of its own, join "
                "dim_project via dim_procedure.project_id for a year filter."
            ),
            primary_key="procedure_id",
            foreign_keys=[
                ForeignKey("procedure_id", "dim_procedure", "procedure_id"),
                ForeignKey("awarded_supplier_id", "dim_supplier", "supplier_id"),
            ],
            columns=[
                Column("procedure_id", "string"),
                Column("estimated_value", "double"),
                Column("awarded_supplier_id", "string"),
                Column("awarded_bid_amount", "double"),
                Column("bid_count", "bigint"),
                Column("procurement_savings", "double", "estimated_value - awarded_bid_amount."),
            ],
        ),
        TableSchema(
            name="fact_project_financials",
            kind="fact",
            grain="One row per project_id (1:1 with dim_project).",
            business_description=(
                "Raw amounts only - realization_pct (SUM(total_paid_amount)/SUM(planned_amount)) "
                "and eu_share_pct (SUM(external_share_amount)/SUM(planned_amount)) are not "
                "stored here so they re-aggregate correctly when sliced by department/year; "
                "compute them in the query if needed, or use mv_project_realization_kpi which "
                "already carries them at the per-project grain."
            ),
            primary_key="project_id",
            foreign_keys=[ForeignKey("project_id", "dim_project", "project_id")],
            columns=[
                Column("project_id", "string"),
                Column("planned_amount", "int"),
                Column("city_share_amount", "int"),
                Column("external_share_amount", "int", "EU/external funding portion of planned_amount."),
                Column("total_contracted_value", "double"),
                Column("contract_count", "bigint"),
                Column("total_invoiced_amount", "double"),
                Column("total_paid_amount", "double"),
            ],
        ),
        TableSchema(
            name="mv_procurement_savings_kpi",
            kind="kpi_view",
            grain="One row per procedure_id. Denormalized: joins procedure/project/department/cpv/supplier.",
            business_description=(
                "Procurement savings KPI, denormalized for direct dashboard/SQL use. "
                "savings_pct is safe to read directly AT THIS GRAIN (one row per procedure), "
                "but if rolling several rows up (e.g. by department or year), recompute as "
                "SUM(procurement_savings)/SUM(estimated_value) rather than averaging savings_pct. "
                "Has no year column directly - join dim_project (via project_id) or dim_procedure "
                "(via selection_decision_date) for a year filter."
            ),
            primary_key="procedure_id",
            foreign_keys=[
                ForeignKey("project_id", "dim_project", "project_id"),
                ForeignKey("department_id", "dim_department", "department_id"),
                ForeignKey("cpv_code", "dim_cpv", "cpv_code"),
            ],
            columns=[
                Column("procedure_id", "string"),
                Column("evidence_number", "string"),
                Column("project_id", "string"),
                Column("project_name", "string"),
                Column("department_id", "string"),
                Column("department_name", "string"),
                Column("cpv_code", "string"),
                Column("cpv_description", "string"),
                Column("estimated_value", "double"),
                Column("awarded_bid_amount", "double"),
                Column("awarded_supplier_name", "string"),
                Column("procurement_savings", "double"),
                Column("savings_pct", "double", "Pre-computed; do not average across rows, see grain note above."),
                Column("bid_count", "bigint"),
            ],
        ),
        TableSchema(
            name="mv_project_realization_kpi",
            kind="kpi_view",
            grain="One row per project_id. Denormalized: joins project/department.",
            business_description=(
                "Project realization % KPI, denormalized for direct dashboard/SQL use. "
                "realization_pct/contracted_pct/eu_share_pct are safe to read directly AT THIS "
                "GRAIN (one row per project), but if rolling several rows up (e.g. by "
                "department), recompute as SUM(total_paid_amount)/SUM(planned_amount) etc. "
                "rather than averaging these columns. Does carry a year column directly."
            ),
            primary_key="project_id",
            foreign_keys=[ForeignKey("department_id", "dim_department", "department_id")],
            columns=[
                Column("project_id", "string"),
                Column("project_name", "string"),
                Column("project_status", "string"),
                Column("department_id", "string"),
                Column("department_name", "string"),
                Column("funding_source", "string"),
                Column("eu_program", "string"),
                Column("year", "int"),
                Column("planned_amount", "int"),
                Column("city_share_amount", "int"),
                Column("external_share_amount", "int"),
                Column("total_contracted_value", "double"),
                Column("contract_count", "bigint"),
                Column("total_invoiced_amount", "double"),
                Column("total_paid_amount", "double"),
                Column("realization_pct", "double", "Pre-computed; do not average across rows, see grain note above."),
                Column("contracted_pct", "double", "Pre-computed; do not average across rows, see grain note above."),
                Column("eu_share_pct", "double", "Pre-computed; do not average across rows, see grain note above."),
            ],
        ),
    ]
}


def list_tables_summary() -> list[dict]:
    return [
        {
            "name": t.name,
            "kind": t.kind,
            "grain": t.grain,
            "business_description": t.business_description,
        }
        for t in CATALOG.values()
    ]


def get_table(table_name: str) -> TableSchema | None:
    return CATALOG.get(table_name)


TABLE_NAMES: frozenset[str] = frozenset(CATALOG.keys())
