from pyspark import pipelines as dp

CATALOG = spark.conf.get("finance_cockpit.catalog")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

# Every gold table's uniqueness is supposed to be structurally guaranteed by
# something upstream (silver's SCD2 "one current row per key" guarantee, or
# the table's own grain) - these checks exist to catch a regression, not to
# tolerate routine bad data. expect_or_fail means a violation stops the
# pipeline update immediately rather than silently shipping duplicated rows
# into Power BI. Uniqueness is a dataset-level property, so each check groups
# by the key and asserts every group has exactly one row - a plain row-level
# expectation can't express this on its own.


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_dim_department",
    comment="Fails the pipeline if dim_department ever has more than one row per department_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_dim_department():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.dim_department")
        .groupBy("department_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_dim_supplier",
    comment="Fails the pipeline if dim_supplier ever has more than one row per supplier_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_dim_supplier():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.dim_supplier")
        .groupBy("supplier_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_dim_cpv",
    comment="Fails the pipeline if dim_cpv ever has more than one row per cpv_code.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_dim_cpv():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.dim_cpv")
        .groupBy("cpv_code")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_dim_project",
    comment="Fails the pipeline if dim_project ever has more than one row per project_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_dim_project():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.dim_project")
        .groupBy("project_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_dim_contract",
    comment="Fails the pipeline if dim_contract ever has more than one row per contract_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_dim_contract():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.dim_contract")
        .groupBy("contract_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_dim_procedure",
    comment="Fails the pipeline if dim_procedure ever has more than one row per procedure_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_dim_procedure():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.dim_procedure")
        .groupBy("procedure_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_dim_date",
    comment="Fails the pipeline if dim_date ever has more than one row per date.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_dim_date():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.dim_date")
        .groupBy("date")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_fact_invoices",
    comment="Fails the pipeline if fact_invoices ever has more than one row per invoice_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_fact_invoices():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.fact_invoices")
        .groupBy("invoice_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_fact_purchase_orders",
    comment="Fails the pipeline if fact_purchase_orders ever has more than one row per purchase_order_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_fact_purchase_orders():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.fact_purchase_orders")
        .groupBy("purchase_order_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_fact_contract_financials",
    comment="Fails the pipeline if fact_contract_financials ever has more than one row per contract_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_fact_contract_financials():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.fact_contract_financials")
        .groupBy("contract_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_fact_procurement_bids",
    comment="Fails the pipeline if fact_procurement_bids ever has more than one row per bid_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_fact_procurement_bids():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.fact_procurement_bids")
        .groupBy("bid_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_fact_procurement_performance",
    comment="Fails the pipeline if fact_procurement_performance ever has more than one row per procedure_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_fact_procurement_performance():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.fact_procurement_performance")
        .groupBy("procedure_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_fact_project_financials",
    comment="Fails the pipeline if fact_project_financials ever has more than one row per project_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_fact_project_financials():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.fact_project_financials")
        .groupBy("project_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_mv_procurement_savings_kpi",
    comment="Fails the pipeline if mv_procurement_savings_kpi ever has more than one row per procedure_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_mv_procurement_savings_kpi():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.mv_procurement_savings_kpi")
        .groupBy("procedure_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_mv_project_realization_kpi",
    comment="Fails the pipeline if mv_project_realization_kpi ever has more than one row per project_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_mv_project_realization_kpi():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.mv_project_realization_kpi")
        .groupBy("project_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )


@dp.materialized_view(
    name=f"{CATALOG}.{GOLD_SCHEMA}.test_unique_mv_avg_payment_delay_kpi",
    comment="Fails the pipeline if mv_avg_payment_delay_kpi ever has more than one row per department_id.",
)
@dp.expect_or_fail("unique_key", "num_entries = 1")
def test_unique_mv_avg_payment_delay_kpi():
    return (
        spark.read.table(f"{CATALOG}.{GOLD_SCHEMA}.mv_avg_payment_delay_kpi")
        .groupBy("department_id")
        .count()
        .withColumnRenamed("count", "num_entries")
    )
