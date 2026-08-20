# Design: 001-avg-payment-delay-kpi

Technical approach for satisfying `requirements.md` (version 1). This is what gets proposed,
argued about, and approved *before* code is generated — Construction should be a mechanical
follow of this document, not where the real design decisions get made.

## Approach

Add one new gold materialized view, `mv_avg_payment_delay_kpi`, following the exact shape of
`transformations/mv_procurement_savings_kpi.py`: read the relevant fact table
(`fact_invoices`), join in the dimension chain needed to attribute rows to a department, then
aggregate. This is a rollup KPI (average over many invoices), so — unlike the two existing
fact-grain KPI views — this one is genuinely grouped/aggregated rather than one-row-per-fact,
which is a real difference from the two existing KPI views worth flagging in review.

## Data model

- Layer: gold
- Table type: `@dp.materialized_view` (aggregated, not a passthrough — a `@dp.table` would
  imply row-level streaming semantics that don't fit a GROUP BY)
- Grain: one row per `department_id` (only departments with at least one paid invoice)
- Key: `department_id`
- CDC strategy: N/A — gold materialized view, recomputed from `fact_invoices` +
  `dim_project` + `dim_department` on each pipeline run, same as the existing KPI views.
- Schema:
  - `department_id` (from `dim_department`)
  - `department_name` (from `dim_department`)
  - `paid_invoice_count` (count of invoices included in the average — lets a dashboard show
    the average isn't from a single invoice)
  - `avg_days_late` (`ROUND(AVG(days_late), 2)`, filtered to `payment_date IS NOT NULL`)

## Affected files

- `transformations/mv_avg_payment_delay_kpi.py` (new) — reads `fact_invoices`, joins
  `dim_project` (for `department_id`) then `dim_department` (for `department_name`),
  filters `payment_date IS NOT NULL`, groups by department, rounds the average to 2dp.
- `resources/pipelines.yml` — no change needed; the pipeline's `libraries.glob` already
  includes all of `transformations/**`, so a new file is picked up automatically. (Confirmed
  by reading the existing `pipelines.yml` — this is why the file list doesn't touch it,
  unlike a change that needed a new schema/catalog entry.)
- `transformations/quality_tests_gold_uniqueness.py` — extend with a uniqueness test on
  `mv_avg_payment_delay_kpi.department_id`.

## Test plan

| Acceptance criterion | Test |
|---|---|
| 1. One row per department_id among paid invoices | Uniqueness test on `department_id` in `quality_tests_gold_uniqueness.py`, plus a row-count comparison against `SELECT COUNT(DISTINCT department_id) FROM fact_invoices JOIN dim_project ... WHERE payment_date IS NOT NULL` |
| 2. avg_days_late matches independent calculation | Ad hoc SQL: compare view output to `SELECT department_id, ROUND(AVG(days_late), 2) FROM ... GROUP BY department_id` computed directly against fact_invoices/dim_project, for at least one department |
| 3. Departments with zero paid invoices excluded | Pick a department known to have only unpaid invoices (or none), confirm it's absent from the view |
| 4. Uniqueness | Same test as criterion 1 |

## Risks / open questions

- The "exclude unpaid invoices" assumption in `requirements.md` needs real Finance
  confirmation before this leaves Inception for real (flagged there, repeated here since
  it's the one design choice most likely to get rejected at review).
- If a future unit of work wants this trended over time rather than as a snapshot, that's a
  different grain (department × period) and should be a new unit of work, not a retrofit of
  this view.
