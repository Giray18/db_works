# Requirements: 001-avg-payment-delay-kpi

**Status: FROZEN as of 2026-08-20 / version 1.** Once frozen, changes to this file require a
new version number and a note in the decision log explaining why — the acceptance criteria
below are the evaluation bar for Construction and must not silently drift to match whatever
got built.

## Business intent

Finance wants average invoice payment delay per department as a standing, queryable number,
instead of an ad hoc join computed each time someone asks.

## Assumptions surfaced during elaboration

- Assumed "payment delay" means `fact_invoices.days_late`, the column already produced there
  — confirmed by inspecting `transformations/fact_invoices.py`, not invented.
- Assumed the KPI should only average invoices that have actually been paid (`payment_date`
  is not null), so unpaid/outstanding invoices don't drag the average toward zero or skew it
  — this needs explicit sign-off from Finance in a real run, flagged here rather than
  silently decided.
- Assumed department attribution follows the same active drill path
  `fact_invoices.project_id -> dim_project.department_id -> dim_department`, as called out in
  `fact_invoices.py`'s own comment about avoiding ambiguous relationships.

## Acceptance criteria

1. Given the gold layer has `fact_invoices` rows with non-null `payment_date`, when the new
   KPI view is queried, then it returns exactly one row per `department_id` present among
   those invoices.
2. Given a department's paid invoices, when averaging `days_late`, then the KPI's
   `avg_days_late` equals `ROUND(AVG(days_late), 2)` computed independently over the same
   filtered row set (not reverse-engineered from the view's own output).
3. Given a department with zero paid invoices, when the KPI is queried, then that department
   does not appear as a row with a null/misleading average (excluded, not zero-filled).
4. Given the KPI view, when inspected, then `department_id` + one row per department is
   unique (uniqueness test required, per repo convention).

## Non-functional constraints

- [x] Respects the one-pipeline-per-type limit (Free Edition) — no new pipeline, extend the
      existing one in `resources/pipelines.yml` if this touches the medallion pipeline.
- [x] Monetary columns rounded to 2 decimals, percentage columns to 4, if this produces gold
      output. (N/A for money here, but `avg_days_late` rounded to 2 decimals for the same
      "no float noise" reason.)
- [ ] Ratios stored as raw numerator/denominator — N/A, this KPI is an average, not a ratio
      of two stored fact columns, so there's nothing to re-derive at a different grain.
- [x] Follows the existing KPI materialized-view pattern (`mv_procurement_savings_kpi.py`):
      one row per grain (department here, not procedure), denormalized dimension columns
      included for direct dashboard/SQL use.

## Out of scope

- Changing how `days_late` is computed in `fact_invoices`.
- Power BI report/visual changes.
- Trend-over-time / historical average (current-snapshot KPI only).
