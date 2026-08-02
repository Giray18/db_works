from pyspark import pipelines as dp

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_CPV_LOOKUP = f"{CATALOG}.{SILVER_SCHEMA}.cpv_lookup"
GOLD_DIM_CPV = f"{CATALOG}.{GOLD_SCHEMA}.dim_cpv"


@dp.table(
    name=GOLD_DIM_CPV,
    comment="CPV procurement-category dimension. Key: cpv_code.",
)
def dim_cpv():
    return spark.read.table(SILVER_CPV_LOOKUP).select("cpv_code", "cpv_description")
