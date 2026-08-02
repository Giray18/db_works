from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_CONTRACTS = f"{CATALOG}.{BRONZE_SCHEMA}.contracts"
SILVER_CONTRACTS = f"{CATALOG}.{SILVER_SCHEMA}.contracts"


@dp.table(
    name=BRONZE_CONTRACTS,
    comment="Raw contract snapshots as CSV exports land, one row set per export run",
)
def bronze_contracts():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/contracts/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="contracts_latest_snapshot")
def contracts_latest_snapshot():
    df = spark.read.table(BRONZE_CONTRACTS)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        # Excel serial dates: days since 1899-12-30. contract_deadline doesn't
        # end in "_date" but is the same serialized-date problem, so it needs
        # the same cast.
        .withColumn("signature_date", F.expr("date_add(to_date('1899-12-30'), CAST(signature_date AS INT))"))
        .withColumn("contract_deadline", F.expr("date_add(to_date('1899-12-30'), CAST(contract_deadline AS INT))"))
        .dropDuplicates(["contract_id"])
    )


dp.create_streaming_table(
    SILVER_CONTRACTS,
    comment="Deduplicated, current contracts with dates cast. Cancelled/removed contracts are "
    "closed out, not erased, via SCD2 - disappearing from the source marks the record as no "
    "longer current rather than deleting its history.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_CONTRACTS,
    source="contracts_latest_snapshot",
    keys=["contract_id"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the contract actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
