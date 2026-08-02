from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
SILVER_SCHEMA = spark.conf.get("finance_cockpit.silver_schema")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

SILVER_PROCUREMENT_PROCEDURES = f"{CATALOG}.{SILVER_SCHEMA}.procurement_procedures"
SILVER_PROCUREMENT_PLAN = f"{CATALOG}.{SILVER_SCHEMA}.procurement_plan"
GOLD_DIM_PROCEDURE = f"{CATALOG}.{GOLD_SCHEMA}.dim_procedure"


def _current(df):
    return df.filter(F.col("__END_AT").isNull())


@dp.table(
    name=GOLD_DIM_PROCEDURE,
    comment="Procurement procedure dimension. Key: procedure_id. FKs: project_id -> "
    "dim_project, cpv_code -> dim_cpv.",
)
def dim_procedure():
    procedures = _current(spark.read.table(SILVER_PROCUREMENT_PROCEDURES)).select(
        "procedure_id", "evidence_number", "project_id", "procedure_type",
        "publication_date", "selection_decision_date", "procedure_status",
    )
    plan = _current(spark.read.table(SILVER_PROCUREMENT_PLAN)).select(
        "evidence_number", "cpv_code", "planned_quarter",
    )
    return procedures.join(plan, "evidence_number", "left")
