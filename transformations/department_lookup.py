from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_DEPARTMENT_LOOKUP = f"{CATALOG}.{BRONZE_SCHEMA}.department_lookup"
SILVER_DEPARTMENT_LOOKUP = f"{CATALOG}.{SILVER_SCHEMA}.department_lookup"


@dp.table(
    name=BRONZE_DEPARTMENT_LOOKUP,
    comment="Raw department lookup snapshots as CSV exports land",
)
def bronze_department_lookup():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/department_lookup/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="department_lookup_latest_snapshot")
def department_lookup_latest_snapshot():
    df = spark.read.table(BRONZE_DEPARTMENT_LOOKUP)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["department_id"])
    )


dp.create_streaming_table(
    SILVER_DEPARTMENT_LOOKUP,
    comment="Current department code to name mapping - latest value only, no history kept.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_DEPARTMENT_LOOKUP,
    source="department_lookup_latest_snapshot",
    keys=["department_id"],
    stored_as_scd_type="1",
)
