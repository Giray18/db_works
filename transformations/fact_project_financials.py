from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_PROJECTS = f"{CATALOG}.{SILVER_SCHEMA}.projects"
SILVER_INVOICES = f"{CATALOG}.{SILVER_SCHEMA}.invoices"
GOLD_DIM_CONTRACT = f"{CATALOG}.{GOLD_SCHEMA}.dim_contract"
GOLD_FACT_CONTRACT_FINANCIALS = f"{CATALOG}.{GOLD_SCHEMA}.fact_contract_financials"
GOLD_FACT_PROJECT_FINANCIALS = f"{CATALOG}.{GOLD_SCHEMA}.fact_project_financials"


def _current(df):
    return df.filter(F.col("__END_AT").isNull())


@dp.table(
    name=GOLD_FACT_PROJECT_FINANCIALS,
    comment="Project financials fact. Grain: one row per project (1:1 with dim_project). "
    "Build realization_pct (SUM(total_paid_amount)/SUM(planned_amount)) and eu_share_pct "
    "(SUM(external_share_amount)/SUM(planned_amount)) as Power BI measures, not stored "
    "columns, so they re-aggregate correctly when sliced by department or year.",
)
def fact_project_financials():
    projects = _current(spark.read.table(SILVER_PROJECTS)).select(
        "project_id", "planned_amount", "city_share_amount", "external_share_amount",
    )

    contracted = (
        spark.read.table(GOLD_FACT_CONTRACT_FINANCIALS)
        .join(spark.read.table(GOLD_DIM_CONTRACT).select("contract_id", "project_id"), "contract_id")
        .groupBy("project_id")
        .agg(
            F.sum("total_contract_value").alias("total_contracted_value"),
            F.count("*").alias("contract_count"),
        )
    )

    # invoices.project_id is a denormalized copy of the real chain
    # (project -> contract -> purchase_order -> invoice), validated by the
    # profiler at 100% containment - safe to roll up directly from it.
    invoices = _current(spark.read.table(SILVER_INVOICES))
    invoiced = invoices.groupBy("project_id").agg(F.sum("invoice_amount").alias("total_invoiced_amount"))
    paid = (
        invoices.filter(F.col("payment_date").isNotNull())
        .groupBy("project_id")
        .agg(F.sum("invoice_amount").alias("total_paid_amount"))
    )

    return (
        projects.join(contracted, "project_id", "left")
        .join(invoiced, "project_id", "left")
        .join(paid, "project_id", "left")
        .withColumn("planned_amount", F.round(F.col("planned_amount"), 2))
        .withColumn("city_share_amount", F.round(F.col("city_share_amount"), 2))
        .withColumn("external_share_amount", F.round(F.col("external_share_amount"), 2))
        .withColumn("total_contracted_value", F.round(F.coalesce(F.col("total_contracted_value"), F.lit(0.0)), 2))
        .withColumn("contract_count", F.coalesce(F.col("contract_count"), F.lit(0)))
        .withColumn("total_invoiced_amount", F.round(F.coalesce(F.col("total_invoiced_amount"), F.lit(0.0)), 2))
        .withColumn("total_paid_amount", F.round(F.coalesce(F.col("total_paid_amount"), F.lit(0.0)), 2))
    )
