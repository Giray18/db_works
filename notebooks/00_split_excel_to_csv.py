# Databricks notebook source
# Reads the finance cockpit workbook and writes each sheet as its own timestamped
# CSV, landing under one subfolder per table. Auto Loader (in the medallion
# pipeline) treats each new file as newly-arrived data - it never re-reads a
# path it has already seen - so this is what makes the pipeline incremental
# even though the source is a full re-extract each time, not a delta feed.

# MAGIC %pip install -q openpyxl

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("source_xlsx", "/Volumes/workspace/default/raw/lakehouse_city_unified_finance_cockpit_poc_dataset.xlsx")
dbutils.widgets.text("csv_landing_root", "/Volumes/workspace/default/raw/csv_landing")
dbutils.widgets.text("run_id", "")

# COMMAND ----------

import os
from datetime import datetime, timezone

import pandas as pd

SOURCE_XLSX = dbutils.widgets.get("source_xlsx")
CSV_LANDING_ROOT = dbutils.widgets.get("csv_landing_root")
# job.run_id is unique per job run - safer than a wall-clock timestamp, which
# could collide if the job is ever re-run within the same second.
RUN_ID = dbutils.widgets.get("run_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")

# Every row written in this run gets the same snapshot timestamp - this is the
# column silver uses to tell "this run's data" apart from earlier exports, and
# to sequence versions for SCD2 history.
SNAPSHOT_TS = datetime.now(timezone.utc).isoformat()

# Bronze/silver table name per sheet - drops the leading "NN_" numbering and,
# for invoices, the source-system "_ura" suffix.
SHEET_TO_TABLE = {
    "00_dashboard_summary": "dashboard_summary",
    "00_summary_by_year": "summary_by_year",
    "01_projects": "projects",
    "02_budget_plan": "budget_plan",
    "03_procurement_plan": "procurement_plan",
    "04_procurement_procedures": "procurement_procedures",
    "05_procurement_bids": "procurement_bids",
    "06_contracts": "contracts",
    "07_contract_annexes": "contract_annexes",
    "08_purchase_orders": "purchase_orders",
    "09_invoices_ura": "invoices",
    "10_cpv_lookup": "cpv_lookup",
    "11_department_lookup": "department_lookup",
    "12_supplier_lookup": "supplier_lookup",
    "13_source_notes": "source_notes",
}

# COMMAND ----------

xls = pd.ExcelFile(SOURCE_XLSX, engine="openpyxl")

for sheet_name in xls.sheet_names:
    table_name = SHEET_TO_TABLE.get(sheet_name, sheet_name)
    pdf = xls.parse(sheet_name)
    pdf.columns = [str(c).strip() for c in pdf.columns]
    pdf["_snapshot_ts"] = SNAPSHOT_TS

    target_dir = f"{CSV_LANDING_ROOT}/{table_name}"
    os.makedirs(target_dir, exist_ok=True)
    out_path = f"{target_dir}/{table_name}_{RUN_ID}.csv"
    pdf.to_csv(out_path, index=False)
    print(f"Wrote {sheet_name} -> {out_path} ({len(pdf)} rows)")
