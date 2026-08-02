from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_PROCUREMENT_PLAN = f"{CATALOG}.{BRONZE_SCHEMA}.procurement_plan"
SILVER_PROCUREMENT_PLAN = f"{CATALOG}.{SILVER_SCHEMA}.procurement_plan"


@dp.table(
    name=BRONZE_PROCUREMENT_PLAN,
    comment="Raw procurement plan snapshots as CSV exports land, one row set per export run",
)
def bronze_procurement_plan():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/procurement_plan/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="procurement_plan_latest_snapshot")
def procurement_plan_latest_snapshot():
    df = spark.read.table(BRONZE_PROCUREMENT_PLAN)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["evidence_number"])
    )


dp.create_streaming_table(
    SILVER_PROCUREMENT_PLAN,
    comment="Deduplicated, current procurement plan entries. Full history via SCD2.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_PROCUREMENT_PLAN,
    source="procurement_plan_latest_snapshot",
    keys=["evidence_number"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the entry actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
