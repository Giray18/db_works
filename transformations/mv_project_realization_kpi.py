from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

GOLD_FACT_PROJECT_FINANCIALS = f"{CATALOG}.{GOLD_SCHEMA}.fact_project_financials"
GOLD_DIM_PROJECT = f"{CATALOG}.{GOLD_SCHEMA}.dim_project"
GOLD_DIM_DEPARTMENT = f"{CATALOG}.{GOLD_SCHEMA}.dim_department"
GOLD_MV_PROJECT_REALIZATION_KPI = f"{CATALOG}.{GOLD_SCHEMA}.mv_project_realization_kpi"


@dp.materialized_view(
    name=GOLD_MV_PROJECT_REALIZATION_KPI,
    comment="Project realization % KPI, denormalized for direct dashboard/SQL use. Grain: "
    "one row per project - realization_pct/eu_share_pct are safe to read directly at this "
    "grain, but if rolling several rows up (e.g. by department), recompute as "
    "SUM(total_paid_amount)/SUM(planned_amount) rather than averaging these columns.",
)
def mv_project_realization_kpi():
    fin = spark.read.table(GOLD_FACT_PROJECT_FINANCIALS)
    project = spark.read.table(GOLD_DIM_PROJECT).select(
        "project_id", "project_name", "project_status", "funding_source", "eu_program",
        "year", "department_id",
    )
    department = spark.read.table(GOLD_DIM_DEPARTMENT)

    return (
        fin.join(project, "project_id", "left")
        .join(department, "department_id", "left")
        .withColumn("planned_amount", F.round(F.col("planned_amount"), 2))
        .withColumn("city_share_amount", F.round(F.col("city_share_amount"), 2))
        .withColumn("external_share_amount", F.round(F.col("external_share_amount"), 2))
        .withColumn("total_contracted_value", F.round(F.col("total_contracted_value"), 2))
        .withColumn("total_invoiced_amount", F.round(F.col("total_invoiced_amount"), 2))
        .withColumn("total_paid_amount", F.round(F.col("total_paid_amount"), 2))
        .withColumn(
            "realization_pct",
            F.round(
                F.when(F.col("total_contracted_value") > 0, F.col("total_paid_amount") / F.col("total_contracted_value")), 4
            ),
        )
        .withColumn(
            "contracted_pct",
            F.round(
                F.when(F.col("planned_amount") > 0, F.col("total_contracted_value") / F.col("planned_amount")), 4
            ),
        )
        .withColumn(
            "eu_share_pct",
            F.round(
                F.when(F.col("total_contracted_value") > 0, F.col("external_share_amount") / F.col("total_contracted_value")), 4
            ),
        )
        .select(
            "project_id", "project_name", "project_status", "department_id", "department_name",
            "funding_source", "eu_program", "year",
            "planned_amount", "city_share_amount", "external_share_amount",
            "total_contracted_value", "contract_count", "total_invoiced_amount", "total_paid_amount",
            "realization_pct", "contracted_pct", "eu_share_pct",
        )
    )
