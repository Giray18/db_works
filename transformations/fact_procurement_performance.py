from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_PROCUREMENT_PLAN = f"{CATALOG}.{SILVER_SCHEMA}.procurement_plan"
SILVER_PROCUREMENT_PROCEDURES = f"{CATALOG}.{SILVER_SCHEMA}.procurement_procedures"
GOLD_FACT_PROCUREMENT_BIDS = f"{CATALOG}.{GOLD_SCHEMA}.fact_procurement_bids"
GOLD_FACT_PROCUREMENT_PERFORMANCE = f"{CATALOG}.{GOLD_SCHEMA}.fact_procurement_performance"


def _current(df):
    return df.filter(F.col("__END_AT").isNull())


@dp.table(
    name=GOLD_FACT_PROCUREMENT_PERFORMANCE,
    comment="Procurement performance fact. Grain: one row per procedure (1:1 with "
    "dim_procedure). procurement_savings = estimated_value - awarded_bid_amount, the "
    "procurement savings KPI. Build savings_pct as a Power BI measure "
    "(SUM(procurement_savings)/SUM(estimated_value)), not a stored column, so it "
    "re-aggregates correctly when sliced.",
)
def fact_procurement_performance():
    plan = _current(spark.read.table(SILVER_PROCUREMENT_PLAN)).select("evidence_number", "estimated_value")
    procedures = _current(spark.read.table(SILVER_PROCUREMENT_PROCEDURES)).select("procedure_id", "evidence_number")
    bids = spark.read.table(GOLD_FACT_PROCUREMENT_BIDS)

    bid_counts = bids.groupBy("procedure_id").agg(F.count("*").alias("bid_count"))
    awarded = (
        bids.filter(F.col("is_awarded"))
        .select(
            "procedure_id",
            F.col("supplier_id").alias("awarded_supplier_id"),
            F.col("bid_amount").alias("awarded_bid_amount"),
        )
    )

    return (
        plan.join(procedures, "evidence_number", "inner")
        .drop("evidence_number")
        .join(awarded, "procedure_id", "left")
        .join(bid_counts, "procedure_id", "left")
        .withColumn("estimated_value", F.round(F.col("estimated_value"), 2))
        .withColumn("awarded_bid_amount", F.round(F.col("awarded_bid_amount"), 2))
        .withColumn("bid_count", F.coalesce(F.col("bid_count"), F.lit(0)))
        .withColumn("procurement_savings", F.round(F.col("estimated_value") - F.col("awarded_bid_amount"), 2))
    )
