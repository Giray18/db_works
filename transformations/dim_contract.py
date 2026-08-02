from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_CONTRACTS = f"{CATALOG}.{SILVER_SCHEMA}.contracts"
SILVER_CONTRACT_ANNEXES = f"{CATALOG}.{SILVER_SCHEMA}.contract_annexes"
GOLD_DIM_CONTRACT = f"{CATALOG}.{GOLD_SCHEMA}.dim_contract"


def _current(df):
    return df.filter(F.col("__END_AT").isNull())


@dp.table(
    name=GOLD_DIM_CONTRACT,
    comment="Contract dimension. Key: contract_id. FKs: supplier_id -> dim_supplier, "
    "project_id -> dim_project. Dollar measures live in fact_contract_financials, not here.",
)
def dim_contract():
    contracts = _current(spark.read.table(SILVER_CONTRACTS)).select(
        "contract_id", "project_id", "budget_item_id", "procedure_id", "supplier_id",
        "signature_date", "contract_deadline", "contract_status",
    )
    latest_annex_deadline = (
        _current(spark.read.table(SILVER_CONTRACT_ANNEXES))
        .groupBy("contract_id")
        .agg(F.max("new_deadline").alias("latest_annex_deadline"))
    )
    return (
        contracts.join(latest_annex_deadline, "contract_id", "left")
        # A signed annex can push the deadline out - fall back to contract_deadline
        # when there's no annex.
        .withColumn("current_deadline", F.coalesce(F.col("latest_annex_deadline"), F.col("contract_deadline")))
        .drop("latest_annex_deadline")
    )
