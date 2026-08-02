from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

GOLD_FACT_PROCUREMENT_PERFORMANCE = f"{CATALOG}.{GOLD_SCHEMA}.fact_procurement_performance"
GOLD_DIM_PROCEDURE = f"{CATALOG}.{GOLD_SCHEMA}.dim_procedure"
GOLD_DIM_PROJECT = f"{CATALOG}.{GOLD_SCHEMA}.dim_project"
GOLD_DIM_DEPARTMENT = f"{CATALOG}.{GOLD_SCHEMA}.dim_department"
GOLD_DIM_CPV = f"{CATALOG}.{GOLD_SCHEMA}.dim_cpv"
GOLD_DIM_SUPPLIER = f"{CATALOG}.{GOLD_SCHEMA}.dim_supplier"
GOLD_MV_PROCUREMENT_SAVINGS_KPI = f"{CATALOG}.{GOLD_SCHEMA}.mv_procurement_savings_kpi"


@dp.materialized_view(
    name=GOLD_MV_PROCUREMENT_SAVINGS_KPI,
    comment="Procurement savings KPI, denormalized for direct dashboard/SQL use. Grain: one "
    "row per procedure - savings_pct is safe to read directly at this grain, but if rolling "
    "several rows up (e.g. by department), recompute as SUM(procurement_savings)/"
    "SUM(estimated_value) rather than averaging this column.",
)
def mv_procurement_savings_kpi():
    perf = spark.read.table(GOLD_FACT_PROCUREMENT_PERFORMANCE)
    procedure = spark.read.table(GOLD_DIM_PROCEDURE).select("procedure_id", "evidence_number", "project_id", "cpv_code")
    project = spark.read.table(GOLD_DIM_PROJECT).select(
        "project_id", F.col("project_name").alias("_project_name"), "department_id",
    )
    department = spark.read.table(GOLD_DIM_DEPARTMENT)
    cpv = spark.read.table(GOLD_DIM_CPV)
    supplier = spark.read.table(GOLD_DIM_SUPPLIER).select(
        F.col("supplier_id").alias("_supplier_id"), F.col("supplier_name").alias("awarded_supplier_name"),
    )

    return (
        perf.join(procedure, "procedure_id", "left")
        .join(project, "project_id", "left")
        .withColumnRenamed("_project_name", "project_name")
        .join(department, "department_id", "left")
        .join(cpv, "cpv_code", "left")
        .join(supplier, perf["awarded_supplier_id"] == supplier["_supplier_id"], "left")
        .drop("_supplier_id")
        .withColumn("estimated_value", F.round(F.col("estimated_value"), 2))
        .withColumn("awarded_bid_amount", F.round(F.col("awarded_bid_amount"), 2))
        .withColumn("procurement_savings", F.round(F.col("procurement_savings"), 2))
        .withColumn(
            "savings_pct",
            F.round(
                F.when(F.col("estimated_value") > 0, F.col("procurement_savings") / F.col("estimated_value")), 4
            ),
        )
        .select(
            "procedure_id", "evidence_number", "project_id", "project_name", "department_id", "department_name",
            "cpv_code", "cpv_description", "estimated_value", "awarded_bid_amount", "awarded_supplier_name",
            "procurement_savings", "savings_pct", "bid_count",
        )
    )
