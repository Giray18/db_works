from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_INVOICES = f"{CATALOG}.{SILVER_SCHEMA}.invoices"
GOLD_FACT_INVOICES = f"{CATALOG}.{GOLD_SCHEMA}.fact_invoices"


@dp.table(
    name=GOLD_FACT_INVOICES,
    comment="Invoice fact. Grain: one row per invoice. FKs: purchase_order_id -> "
    "fact_purchase_orders, contract_id -> dim_contract, project_id -> dim_project. "
    "issue_date/due_date/payment_date each relate to dim_date - pick one active path "
    "through the drill hierarchy in the Power BI model to avoid ambiguous relationships "
    "(e.g. via purchase_order_id -> dim_contract -> dim_project -> dim_department, "
    "rather than also having contract_id/project_id active at the same time).",
)
def fact_invoices():
    return (
        spark.read.table(SILVER_INVOICES)
        .filter(F.col("__END_AT").isNull())
        .withColumn("invoice_amount", F.round(F.col("invoice_amount"), 2))
        .select(
            "invoice_id", "purchase_order_id", "contract_id", "project_id",
            "issue_date", "due_date", "payment_date", "invoice_amount", "currency",
            "payment_status", "invoice_status", "days_late",
        )
    )
