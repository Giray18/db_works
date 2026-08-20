# Unit of Work: 001 — Average invoice payment delay KPI by department

A unit of work is a feature scoped small enough to finish in a few bolts (hours-to-days
cycles), not a multi-week epic. One unit of work = one folder under
`ai_dlc/_units_of_work/<id>-<slug>/` holding this file plus the requirements, design,
decision-log, and (if relevant) ADR and runbook documents it produces.

## Intent

Finance wants to see, per department, how late invoices are typically paid — today that
requires an ad hoc join and average in Power BI or SQL every time someone asks. `days_late`
already exists on `fact_invoices`; there's no department-level rollup of it yet.

## Scope

- In scope: one new gold KPI materialized view, average `days_late` grouped by department,
  denormalized with `department_name` for direct dashboard/SQL use (same shape as the
  existing `mv_procurement_savings_kpi` / `mv_project_realization_kpi`).
- Out of scope: any change to how `days_late` itself is computed in `fact_invoices`; any
  Power BI report/visual changes (follow-up unit of work if wanted); trend-over-time
  (this is a current-snapshot KPI, not a time series).

## Affected surfaces

- [x] Medallion pipeline (`transformations/*.py`, `resources/pipelines.yml`)
- [ ] DABs bundle / jobs (`databricks.yml`, `resources/jobs.yml`)
- [ ] Unity Catalog (`resources/schemas.yml`, `resources/volumes.yml`, grants)
- [ ] Power BI semantic model (`pbi/`)
- [ ] rag_agent (`rag_agent/`)
- [ ] Other: <name>

## Bolts

| Bolt | Phase | Outcome | Date |
|------|-------|---------|------|
| 1 | Inception | requirements.md + design.md drafted (this demo) | 2026-08-20 |
| 2 | Inception → Construction gate | Approved by Cihan Giray Oner; see `decision-log.md` | 2026-08-20 |
| 3 | Construction | `mv_avg_payment_delay_kpi.py` + uniqueness test implemented, deployed and run on dev; all 4 acceptance criteria verified against real data | 2026-08-20 |
| 4 | Construction → Review gate | Approved by Cihan Giray Oner; see `review-checklist.md`, `decision-log.md` | 2026-08-20 |
| 5 | Operations | Deployed to `dev` target; `mv_avg_payment_delay_kpi` live on `workspace.dev_finance_cockpit_gold` | 2026-08-20 |

## Status

`closed` — live in the dev workspace, reviewed and approved, committed (`8e3cd9d`). All
gates logged in `decision-log.md`.
