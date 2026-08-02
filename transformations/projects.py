from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_PROJECTS = f"{CATALOG}.{BRONZE_SCHEMA}.projects"
SILVER_PROJECTS = f"{CATALOG}.{SILVER_SCHEMA}.projects"


@dp.table(
    name=BRONZE_PROJECTS,
    comment="Raw project snapshots as CSV exports land, one row set per export run",
)
def bronze_projects():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/projects/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="projects_latest_snapshot")
def projects_latest_snapshot():
    df = spark.read.table(BRONZE_PROJECTS)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        .dropDuplicates(["project_id"])
    )


dp.create_streaming_table(
    SILVER_PROJECTS,
    comment="Deduplicated, current projects. Full history via SCD2.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_PROJECTS,
    source="projects_latest_snapshot",
    keys=["project_id"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the project actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
