from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_DASHBOARD_SUMMARY = f"{CATALOG}.{BRONZE_SCHEMA}.dashboard_summary"
SILVER_DASHBOARD_SUMMARY = f"{CATALOG}.{SILVER_SCHEMA}.dashboard_summary"


@dp.table(
    name=BRONZE_DASHBOARD_SUMMARY,
    comment="Raw dashboard summary snapshots as CSV exports land",
)
def bronze_dashboard_summary():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/dashboard_summary/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="dashboard_summary_latest_snapshot")
def dashboard_summary_latest_snapshot():
    df = spark.read.table(BRONZE_DASHBOARD_SUMMARY)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["metric"])
    )


dp.create_streaming_table(
    SILVER_DASHBOARD_SUMMARY,
    comment="Current dashboard metric values - a rollup, not a transactional record, so latest "
    "value only.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_DASHBOARD_SUMMARY,
    source="dashboard_summary_latest_snapshot",
    keys=["metric"],
    stored_as_scd_type="1",
)
