from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

GOLD_FACT_INVOICES = f"{CATALOG}.{GOLD_SCHEMA}.fact_invoices"
GOLD_DIM_PROJECT = f"{CATALOG}.{GOLD_SCHEMA}.dim_project"
GOLD_DIM_DEPARTMENT = f"{CATALOG}.{GOLD_SCHEMA}.dim_department"
GOLD_MV_AVG_PAYMENT_DELAY_KPI = f"{CATALOG}.{GOLD_SCHEMA}.mv_avg_payment_delay_kpi"


@dp.materialized_view(
    name=GOLD_MV_AVG_PAYMENT_DELAY_KPI,
    comment="Average invoice payment delay KPI, denormalized for direct dashboard/SQL use. "
    "Grain: one row per department, paid invoices only (payment_date IS NOT NULL) - "
    "departments with no paid invoices are excluded, not zero-filled.",
)
def mv_avg_payment_delay_kpi():
    invoices = spark.read.table(GOLD_FACT_INVOICES).filter(F.col("payment_date").isNotNull())
    project = spark.read.table(GOLD_DIM_PROJECT).select("project_id", "department_id")
    department = spark.read.table(GOLD_DIM_DEPARTMENT)

    return (
        invoices.join(project, "project_id", "left")
        .join(department, "department_id", "left")
        .groupBy("department_id", "department_name")
        .agg(
            F.count("invoice_id").alias("paid_invoice_count"),
            F.round(F.avg("days_late"), 2).alias("avg_days_late"),
        )
        .select("department_id", "department_name", "paid_invoice_count", "avg_days_late")
    )
