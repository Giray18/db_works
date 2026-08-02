from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_SUMMARY_BY_YEAR = f"{CATALOG}.{BRONZE_SCHEMA}.summary_by_year"
SILVER_SUMMARY_BY_YEAR = f"{CATALOG}.{SILVER_SCHEMA}.summary_by_year"


@dp.table(
    name=BRONZE_SUMMARY_BY_YEAR,
    comment="Raw summary-by-year snapshots as CSV exports land",
)
def bronze_summary_by_year():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/summary_by_year/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="summary_by_year_latest_snapshot")
def summary_by_year_latest_snapshot():
    df = spark.read.table(BRONZE_SUMMARY_BY_YEAR)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["year"])
    )


dp.create_streaming_table(
    SILVER_SUMMARY_BY_YEAR,
    comment="Current per-year rollup - a rollup, not a transactional record, so latest value only.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_SUMMARY_BY_YEAR,
    source="summary_by_year_latest_snapshot",
    keys=["year"],
    stored_as_scd_type="1",
)
