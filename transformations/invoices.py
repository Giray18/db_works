from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_INVOICES = f"{CATALOG}.{BRONZE_SCHEMA}.invoices"
SILVER_INVOICES = f"{CATALOG}.{SILVER_SCHEMA}.invoices"


@dp.table(
    name=BRONZE_INVOICES,
    comment="Raw invoice snapshots as CSV exports land, one row set per export run",
)
def bronze_invoices():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/invoices/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="invoices_latest_snapshot")
def invoices_latest_snapshot():
    df = spark.read.table(BRONZE_INVOICES)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        # Excel serial dates: days since 1899-12-30
        .withColumn("issue_date", F.expr("date_add(to_date('1899-12-30'), CAST(issue_date AS INT))"))
        .withColumn("due_date", F.expr("date_add(to_date('1899-12-30'), CAST(due_date AS INT))"))
        .withColumn("payment_date", F.expr("date_add(to_date('1899-12-30'), CAST(payment_date AS INT))"))
        .withColumn(
            "invoice_status",
            F.when(F.col("payment_date").isNotNull(), F.col("payment_status"))
             .when(F.col("due_date") < F.current_date(), F.lit("Overdue"))
             .otherwise(F.col("payment_status")),
        )
        .withColumn(
            "days_late",
            F.when(F.col("payment_date").isNotNull(), F.datediff("payment_date", "due_date")),
        )
        # Defensive: guarantees one row per key before it reaches CDC, which requires it
        .dropDuplicates(["invoice_id"])
    )


dp.create_streaming_table(
    SILVER_INVOICES,
    comment="Deduplicated, current invoices with dates cast and status derived. Full history via SCD2.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_INVOICES,
    source="invoices_latest_snapshot",
    keys=["invoice_id"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the invoice actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
