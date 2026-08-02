from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_PROCUREMENT_BIDS = f"{CATALOG}.{SILVER_SCHEMA}.procurement_bids"
GOLD_FACT_PROCUREMENT_BIDS = f"{CATALOG}.{GOLD_SCHEMA}.fact_procurement_bids"

# procurement_bids.bid_status value for the winning bid.
AWARDED_BID_STATUS = "Odabrana"


@dp.table(
    name=GOLD_FACT_PROCUREMENT_BIDS,
    comment="Every bid fact (not just the winner). Grain: one row per bid. FKs: "
    "procedure_id -> dim_procedure, supplier_id -> dim_supplier. Lets users analyze "
    "win rate and competitiveness by supplier - not part of the original KPI list, but "
    "the extra attribute this star schema was meant to unlock.",
)
def fact_procurement_bids():
    return (
        spark.read.table(SILVER_PROCUREMENT_BIDS)
        .filter(F.col("__END_AT").isNull())
        .select("bid_id", "procedure_id", "supplier_id", "bid_amount", "bid_status")
        .withColumn("bid_amount", F.round(F.col("bid_amount"), 2))
        .withColumn("is_awarded", F.col("bid_status") == AWARDED_BID_STATUS)
    )
