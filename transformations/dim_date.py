from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("finance_cockpit.catalog")
GOLD_SCHEMA = spark.conf.get("finance_cockpit.gold_schema")

GOLD_DIM_DATE = f"{CATALOG}.{GOLD_SCHEMA}.dim_date"

# A fixed, wide calendar range - not derived from the data - so this table
# doesn't need rebuilding every time new dates show up in a future export.
DATE_RANGE_START = "2020-01-01"
DATE_RANGE_END = "2035-12-31"


@dp.table(
    name=GOLD_DIM_DATE,
    comment="Calendar dimension, one row per day. Key: date. Relate any fact date column "
    "(issue_date, due_date, payment_date, signature_date, order_date, ...) to this table's "
    "date column - Power BI supports multiple relationships to the same date table, only "
    "one active at a time per fact.",
)
def dim_date():
    return (
        spark.sql(
            f"SELECT explode(sequence(to_date('{DATE_RANGE_START}'), "
            f"to_date('{DATE_RANGE_END}'), interval 1 day)) AS date"
        )
        .withColumn("year", F.year("date"))
        .withColumn("quarter", F.quarter("date"))
        .withColumn("month", F.month("date"))
        .withColumn("month_name", F.date_format("date", "MMMM"))
        .withColumn("day", F.dayofmonth("date"))
        .withColumn("day_of_week_name", F.date_format("date", "EEEE"))
        # Spark's dayofweek: 1 = Sunday, 7 = Saturday
        .withColumn("is_weekend", F.dayofweek("date").isin(1, 7))
    )
