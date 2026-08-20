---
name: ai-dlc-operations
description: Deploy, monitor, and run incident response for this repo's Databricks resources (DABs bundle, Lakeflow pipeline, jobs, rag_agent app) after an ai_dlc/review approval. Use for deployment, monitoring, rollback, or runbook work.
metadata:
  ai_dlc_phase: operations
---

# AI-DLC Operations

Called from `ai_dlc/workflow` once `ai_dlc/review` has recorded an "approved" verdict, and
also the entry point for standalone ops work (monitoring, incident response) that isn't part
of an active unit of work.

## Deploy

Delegate the actual DABs mechanics to `databricks-dabs`, but the gate discipline stays:

1. Confirm the decision log shows an "approved" verdict for the unit of work before deploying
   anything — operations should never deploy unreviewed work.
2. `databricks bundle validate` then `databricks bundle deploy` against the target defined in
   `databricks.yml` (currently only `dev` exists — flag it explicitly if a unit of work
   implies needing a `staging`/`prod` target that doesn't exist yet, that's an
   `ai_dlc/architecture` + human decision, not something to add silently here).
3. Record the deploy (target, bundle version/commit, timestamp) as a decision-log entry —
   Operations gates get logged too, not just Construction.

## Monitor

- Lakeflow pipeline health: pipeline event log for the single pipeline in
  `resources/pipelines.yml` — delegate the query mechanics to `databricks-unity-catalog`
  (system tables) or `databricks-execution-compute` (running ad hoc checks).
- Job runs: `resources/jobs.yml` tasks (e.g. the Excel→CSV split) — check run history via
  `databricks-jobs`.
- Data quality: `transformations/quality_tests_gold_uniqueness.py` results are the
  first thing to check when a gold table looks wrong.

## Incident response

Use `ai_dlc/templates/resources/runbook-template.md`. This repo's specific failure modes
worth checking first, in order:

1. **Auto Loader / bronze ingestion** — did the CSV shape from `00_split_excel_to_csv.py`
   change (new column, renamed sheet)? Bronze infers types from raw CSV text, so an upstream
   Excel shape change surfaces here first.
2. **Snapshot-CDC on silver** — a key missing from the new snapshot should close via
   `__END_AT`, not disappear; if a row vanished instead of closing, that's a CDC flow bug,
   not "expected deletion."
3. **Single-pipeline contention** — confirm no second pipeline got created for the same type;
   Free Edition allows only one, and a second one silently competing for the same tables is
   a real failure mode to rule out.
4. **Unity Catalog grants** — permission errors after a recent `resources/schemas.yml`
   change.

Save the filled runbook under `ai_dlc/_units_of_work/<id>-<slug>/runbook-<scenario>.md` if
tied to a specific unit of work, or `ai_dlc/_runbooks/` (create on first use) for a
standing, repo-wide incident type.

## Rollback

Redeploy the prior bundle version/target via `databricks-dabs`. If the incident traces back
to a code defect (not just a bad deploy), that's a new unit of work through
`ai_dlc/workflow`, not a hotfix outside the process — the frozen-requirements-and-review
discipline applies to fixes too.
