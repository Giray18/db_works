from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_PURCHASE_ORDERS = f"{CATALOG}.{SILVER_SCHEMA}.purchase_orders"
GOLD_FACT_PURCHASE_ORDERS = f"{CATALOG}.{GOLD_SCHEMA}.fact_purchase_orders"


@dp.table(
    name=GOLD_FACT_PURCHASE_ORDERS,
    comment="Purchase order fact. Grain: one row per purchase order. FK: contract_id -> "
    "dim_contract. order_date relates to dim_date.",
)
def fact_purchase_orders():
    return (
        spark.read.table(SILVER_PURCHASE_ORDERS)
        .filter(F.col("__END_AT").isNull())
        .withColumn("order_amount", F.round(F.col("order_amount"), 2))
        .select("purchase_order_id", "contract_id", "project_id", "order_date", "order_amount", "order_description")
    )
