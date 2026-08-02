from pyspark import pipelines as dp

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_SUPPLIER_LOOKUP = f"{CATALOG}.{SILVER_SCHEMA}.supplier_lookup"
GOLD_DIM_SUPPLIER = f"{CATALOG}.{GOLD_SCHEMA}.dim_supplier"


@dp.table(
    name=GOLD_DIM_SUPPLIER,
    comment="Supplier dimension. Key: supplier_id.",
)
def dim_supplier():
    return spark.read.table(SILVER_SUPPLIER_LOOKUP).select("supplier_id", "supplier_name", "supplier_city")
