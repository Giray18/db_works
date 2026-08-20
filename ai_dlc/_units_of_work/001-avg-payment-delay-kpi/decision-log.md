# Decision Log: 001-avg-payment-delay-kpi

Append-only. One entry per gate passed (Inception → Construction, Construction → Review,
Review → Operations). This is the audit trail — don't edit past entries, add new ones.

## Log

### 2026-08-20 — Inception → Construction

- Spec version: requirements.md v1, design.md (unversioned draft, first pass)
- Approver: Cihan Giray Oner (cihangiray.oner@gmail.com) — did not author requirements.md/design.md
- Eval result: N/A — no code/tests exist yet; acceptance criteria in requirements.md v1 are
  the bar Construction must satisfy
- Verdict: approved
- Notes: Design's flagged open risk (excluding invoices with null `payment_date` from the
  average rather than zero-filling/including them) was explicitly reviewed and accepted
  as-is for this unit of work. Proceeding to Construction via `ai_dlc/coding`.

### 2026-08-20 — Construction → Review

- Spec version: requirements.md v1, design.md (unversioned draft, first pass)
- Approver: Cihan Giray Oner (cihangiray.oner@gmail.com) — did not author
  `transformations/mv_avg_payment_delay_kpi.py` or the added uniqueness test
- Eval result: `databricks bundle validate` → OK. Bundle deployed and `finance_cockpit_pipeline`
  run on dev target (update `ac33800f`, after one transient auto-reverted regression-protection
  pause on `bb7bc5` — expected platform behavior for a first-time schema change, not a defect).
  All 4 acceptance criteria verified against real data: 4 departments returned
  (criterion 1); `avg_days_late` matched an independent `ROUND(AVG(days_late),2)` SQL query
  exactly — 18.01/19.38/17.26/18.55 (criterion 2); ODJ-004 and ODJ-006 (0 paid invoices)
  correctly excluded (criterion 3); `test_unique_mv_avg_payment_delay_kpi` passed with no
  `expect_or_fail` violation (criterion 4). Full detail in `review-checklist.md`.
- Verdict: approved
- Notes: Implementation matches `design.md`'s affected-files list exactly, no scope creep.
  Ready for `ai_dlc/operations` to finalize/monitor; unit of work otherwise ready to close.

### 2026-08-20 — Operations deploy

- Target: `dev` (only target defined in `databricks.yml`)
- Bundle source: working tree at git HEAD `f55eeeb6` (uncommitted at deploy time —
  `transformations/mv_avg_payment_delay_kpi.py` new,
  `transformations/quality_tests_gold_uniqueness.py` modified)
- Deploy: `databricks bundle deploy --target dev --profile cihan.giray.oner@htecgroup.com` →
  "Deployment complete!"
- Pipeline run: `finance_cockpit_pipeline` update `ac33800f-4cea-44d1-8e6d-19995ba9049d` →
  COMPLETED (one prior transient attempt `bb7bc5bd` auto-paused/reverted by Databricks'
  regression-protection safety net on first detecting the new logical plan — expected,
  self-healed on retry, not an application defect)
- Verdict: approved (deploy executed as part of the same session's Review-gate evidence
  gathering, per explicit human confirmation to run it)
- Notes: `mv_avg_payment_delay_kpi` and `test_unique_mv_avg_payment_delay_kpi` are live on
  `workspace.dev_finance_cockpit_gold` in the dev workspace. No `staging`/`prod` target exists
  yet in `databricks.yml` — flagging per `ai_dlc/operations` guidance that adding one is an
  `ai_dlc/architecture` + human decision, not done here. Code changes remain uncommitted to
  git as of this entry.
