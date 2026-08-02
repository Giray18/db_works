from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_CONTRACTS = f"{CATALOG}.{SILVER_SCHEMA}.contracts"
SILVER_CONTRACT_ANNEXES = f"{CATALOG}.{SILVER_SCHEMA}.contract_annexes"
GOLD_FACT_CONTRACT_FINANCIALS = f"{CATALOG}.{GOLD_SCHEMA}.fact_contract_financials"


def _current(df):
    return df.filter(F.col("__END_AT").isNull())


@dp.table(
    name=GOLD_FACT_CONTRACT_FINANCIALS,
    comment="Contract financials fact. Grain: one row per contract (1:1 with dim_contract). "
    "total_contract_value = contract_amount + total_annex_adjustments - the contract "
    "consolidation rule.",
)
def fact_contract_financials():
    contracts = _current(spark.read.table(SILVER_CONTRACTS)).select("contract_id", "contract_amount")
    annex_totals = (
        _current(spark.read.table(SILVER_CONTRACT_ANNEXES))
        .groupBy("contract_id")
        .agg(
            F.sum("amount_change").alias("total_annex_adjustments"),
            F.count("*").alias("annex_count"),
        )
    )
    return (
        contracts.join(annex_totals, "contract_id", "left")
        .withColumn("contract_amount", F.round(F.col("contract_amount"), 2))
        .withColumn("total_annex_adjustments", F.round(F.coalesce(F.col("total_annex_adjustments"), F.lit(0.0)), 2))
        .withColumn("annex_count", F.coalesce(F.col("annex_count"), F.lit(0)))
        .withColumn("total_contract_value", F.round(F.col("contract_amount") + F.col("total_annex_adjustments"), 2))
    )
