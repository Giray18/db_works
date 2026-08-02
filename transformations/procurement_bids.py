from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_PROCUREMENT_BIDS = f"{CATALOG}.{BRONZE_SCHEMA}.procurement_bids"
SILVER_PROCUREMENT_BIDS = f"{CATALOG}.{SILVER_SCHEMA}.procurement_bids"


@dp.table(
    name=BRONZE_PROCUREMENT_BIDS,
    comment="Raw procurement bid snapshots as CSV exports land, one row set per export run",
)
def bronze_procurement_bids():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/procurement_bids/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="procurement_bids_latest_snapshot")
def procurement_bids_latest_snapshot():
    df = spark.read.table(BRONZE_PROCUREMENT_BIDS)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["bid_id"])
    )


dp.create_streaming_table(
    SILVER_PROCUREMENT_BIDS,
    comment="Deduplicated, current procurement bids. Withdrawn/removed bids are closed out, "
    "not erased, via SCD2.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_PROCUREMENT_BIDS,
    source="procurement_bids_latest_snapshot",
    keys=["bid_id"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the bid actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
