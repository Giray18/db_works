from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
BRONZE_SCHEMA = spark.conf.get("finance_cockpit.bronze_schema")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
CSV_LANDING_ROOT = spark.conf.get("finance_cockpit.csv_landing_root")

BRONZE_PURCHASE_ORDERS = f"{CATALOG}.{BRONZE_SCHEMA}.purchase_orders"
SILVER_PURCHASE_ORDERS = f"{CATALOG}.{SILVER_SCHEMA}.purchase_orders"


@dp.table(
    name=BRONZE_PURCHASE_ORDERS,
    comment="Raw purchase order snapshots as CSV exports land, one row set per export run",
)
def bronze_purchase_orders():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("header", "true")
        .load(f"{CSV_LANDING_ROOT}/purchase_orders/")
        .withColumn("_snapshot_ts", F.col("_snapshot_ts").cast("timestamp"))
    )


@dp.view(name="purchase_orders_latest_snapshot")
def purchase_orders_latest_snapshot():
    df = spark.read.table(BRONZE_PURCHASE_ORDERS)
    latest_ts = df.select(F.max("_snapshot_ts").alias("ts"))
    return (
        df.join(F.broadcast(latest_ts), df["_snapshot_ts"] == latest_ts["ts"])
        .drop("ts")
        # Excel serial dates: days since 1899-12-30
        .withColumn("order_date", F.expr("date_add(to_date('1899-12-30'), CAST(order_date AS INT))"))
        .dropDuplicates(["purchase_order_id"])
    )


dp.create_streaming_table(
    SILVER_PURCHASE_ORDERS,
    comment="Deduplicated, current purchase orders with dates cast. Full history via SCD2.",
)

dp.create_auto_cdc_from_snapshot_flow(
    target=SILVER_PURCHASE_ORDERS,
    source="purchase_orders_latest_snapshot",
    keys=["purchase_order_id"],
    stored_as_scd_type="2",
    # _snapshot_ts/_rescued_data change on every run regardless of real data
    # changes - excluding them stops SCD2 from opening a new history version
    # every single run when nothing about the order actually changed.
    track_history_except_column_list=["_snapshot_ts", "_rescued_data"],
)
