from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_BUDGET_PLAN = f"{CATALOG}.{BRONZE_SCHEMA}.budget_plan"
SILVER_BUDGET_PLAN = f"{CATALOG}.{SILVER_SCHEMA}.budget_plan"


@dp.table(
    name=BRONZE_BUDGET_PLAN,
    comment="Raw budget plan snapshots as CSV exports land, one row set per export run",
)
def bronze_budget_plan():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/budget_plan/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="budget_plan_latest_snapshot")
def budget_plan_latest_snapshot():
    df = spark.read.table(BRONZE_BUDGET_PLAN)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["budget_item_id"])
    )


dp.create_streaming_table(
    SILVER_BUDGET_PLAN,
    comment="Deduplicated, current budget plan lines. Full history via SCD2.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_BUDGET_PLAN,
    source="budget_plan_latest_snapshot",
    keys=["budget_item_id"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the budget line actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
