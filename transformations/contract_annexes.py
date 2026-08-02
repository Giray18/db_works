from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_CONTRACT_ANNEXES = f"{CATALOG}.{BRONZE_SCHEMA}.contract_annexes"
SILVER_CONTRACT_ANNEXES = f"{CATALOG}.{SILVER_SCHEMA}.contract_annexes"


@dp.table(
    name=BRONZE_CONTRACT_ANNEXES,
    comment="Raw contract annex snapshots as CSV exports land, one row set per export run",
)
def bronze_contract_annexes():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/contract_annexes/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="contract_annexes_latest_snapshot")
def contract_annexes_latest_snapshot():
    df = spark.read.table(BRONZE_CONTRACT_ANNEXES)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        # Excel serial dates: days since 1899-12-30. new_deadline doesn't end in
        # "_date" but is the same serialized-date problem, so it needs the same cast.
        .withColumn("annex_date", F.expr("date_add(to_date('1899-12-30'), CAST(annex_date AS INT))"))
        .withColumn("new_deadline", F.expr("date_add(to_date('1899-12-30'), CAST(new_deadline AS INT))"))
        .dropDuplicates(["annex_id"])
    )


dp.create_streaming_table(
    SILVER_CONTRACT_ANNEXES,
    comment="Deduplicated, current contract annexes with dates cast. Full history via SCD2.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_CONTRACT_ANNEXES,
    source="contract_annexes_latest_snapshot",
    keys=["annex_id"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the annex actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
