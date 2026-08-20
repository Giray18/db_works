# Runbook: <incident/scenario name>

## Symptom

<What an operator observes — a failed job run, a pipeline stuck, a stale gold table, a
Power BI refresh error. Be specific enough to match against.>

## Likely causes (this repo)

<Start from the failure modes this pipeline actually has, not generic advice:>
- Auto Loader backlog / schema drift on a new bronze file (`transformations/*.py` ingestion
  tasks, `00_split_excel_to_csv.py` output shape changed).
- Snapshot-CDC mismatch: a key present in the new snapshot didn't close correctly, or a
  legitimately deleted key didn't get its `__END_AT` set (`create_auto_cdc_from_snapshot_flow`
  logic in the affected silver table).
- Free Edition single-pipeline contention — a second pipeline was created for this
  type, violating the one-pipeline-per-type limit.
- Unity Catalog permission drift on `resources/schemas.yml` / `resources/volumes.yml`.
- DABs target/workspace mismatch (`databricks.yml` `dev` vs a since-added `staging`/`prod`
  target).

## Diagnosis steps

1. <Check the Lakeflow pipeline event log for the affected pipeline — see
   `ai_dlc/operations/SKILL.md` for the query pattern.>
2. <...>

## Resolution

<Steps taken, or a link to the specific decision-log / unit-of-work entry if the fix required
a code change and went back through Inception→Construction→Review.>

## Rollback

<`databricks bundle deploy` to the prior state / target, if resolution requires reverting a
recent deploy.>

## Follow-up

<Did this reveal a gap that needs a new unit of work — e.g. a missing quality test that
would have caught this earlier?>
