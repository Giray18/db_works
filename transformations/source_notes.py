from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_SOURCE_NOTES = f"{CATALOG}.{BRONZE_SCHEMA}.source_notes"
SILVER_SOURCE_NOTES = f"{CATALOG}.{SILVER_SCHEMA}.source_notes"


@dp.table(
    name=BRONZE_SOURCE_NOTES,
    comment="Raw source notes snapshots as CSV exports land",
)
def bronze_source_notes():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/source_notes/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="source_notes_latest_snapshot")
def source_notes_latest_snapshot():
    df = spark.read.table(BRONZE_SOURCE_NOTES)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["source_name"])
    )


dp.create_streaming_table(
    SILVER_SOURCE_NOTES,
    comment="Current data-source documentation - latest value only, no history kept.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_SOURCE_NOTES,
    source="source_notes_latest_snapshot",
    keys=["source_name"],
    stored_as_scd_type="1",
)
