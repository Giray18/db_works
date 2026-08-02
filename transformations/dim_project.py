from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_PROJECTS = f"{CATALOG}.{SILVER_SCHEMA}.projects"
GOLD_DIM_PROJECT = f"{CATALOG}.{GOLD_SCHEMA}.dim_project"


@dp.table(
    name=GOLD_DIM_PROJECT,
    comment="Project dimension. Key: project_id. FKs: department_id -> dim_department, "
    "cpv_code -> dim_cpv.",
)
def dim_project():
    return (
        spark.read.table(SILVER_PROJECTS)
        .filter(F.col("__END_AT").isNull())
        .select(
            "project_id", "project_name", "project_status", "funding_source", "funding_type",
            "eu_program", "year", "department_id", "cpv_code",
        )
    )
