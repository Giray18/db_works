# Databricks notebook source
# MAGIC %pip install -q openpyxl

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("target_catalog", "workspace")
dbutils.widgets.text("target_schema", "bronze")

import pandas as pd

SOURCE_PATH = "/Volumes/workspace/default/raw/lakehouse_city_unified_finance_cockpit_poc_dataset.xlsx"
TARGET_CATALOG = dbutils.widgets.get("target_catalog")
TARGET_SCHEMA = dbutils.widgets.get("target_schema")

# COMMAND ----------

xls = pd.ExcelFile(SOURCE_PATH, engine="openpyxl")

for sheet_name in xls.sheet_names:
    pdf = xls.parse(sheet_name)
    pdf.columns = [str(c).strip() for c in pdf.columns]
    sdf = spark.createDataFrame(pdf.astype(object).where(pd.notnull(pdf), None))

    table_name = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{sheet_name}"
    sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
    print(f"Loaded {sheet_name} -> {table_name} ({sdf.count()} rows)")
