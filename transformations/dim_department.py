from pyspark import pipelines as dp

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_DEPARTMENT_LOOKUP = f"{CATALOG}.{SILVER_SCHEMA}.department_lookup"
GOLD_DIM_DEPARTMENT = f"{CATALOG}.{GOLD_SCHEMA}.dim_department"


@dp.table(
    name=GOLD_DIM_DEPARTMENT,
    comment="Department dimension. Key: department_id.",
)
def dim_department():
    return spark.read.table(SILVER_DEPARTMENT_LOOKUP).select("department_id", "department_name")
