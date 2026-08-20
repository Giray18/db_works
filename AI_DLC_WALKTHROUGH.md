# AI-DLC Walkthrough: how "average payment delay KPI" went from request to deployed table

This document walks through, step by step, how a single Databricks unit of work moved
through this repo's AI-DLC (AI-Driven Development Life Cycle) process — from a one-line
business ask to a deployed, tested, committed gold table. It uses the real run of
**unit-of-work 001 — average invoice payment delay KPI by department**
(`ai_dlc/_units_of_work/001-avg-payment-delay-kpi/`) as the worked example. Read this if you
want to understand *how* the process works, not just *what* got built.

## The mental model: bolts, units of work, gates

AI-DLC replaces two-week sprints with **bolts** (hours-to-days work cycles, each sized to one
validated decision) and epics with **units of work** — features small enough to finish in a
handful of bolts. Every unit of work lives in its own folder under
`ai_dlc/_units_of_work/<id>-<slug>/` and moves through three phases:

```
Inception  →  Construction  →  Operations
(spec)         (code)           (deploy/monitor)
```

Three non-negotiable governance rules run through all of it:

1. **Acceptance tests are frozen during Inception**, before any code is written.
2. **Every phase transition ("gate") needs a named human approver who did not author the
   artifact being approved** — the agent that wrote the code cannot also approve it.
3. **Every gate is logged** in an append-only `decision-log.md`, so the whole unit of work is
   auditable after the fact.

The rest of this document shows exactly where each rule bit in practice.

## Step 0 — entry point: `ai_dlc/workflow`

The request was simply "run the unit of work defined at
`ai_dlc/_units_of_work/001-avg-payment-delay-kpi/unit-of-work.md`." That file is the entry
point skill (`ai_dlc/workflow/SKILL.md`) routes from — it doesn't do any phase's work itself,
it reads the unit-of-work's current status and dispatches to the right phase skill.

Reading `unit-of-work.md` showed:

- **Intent**: Finance wants average invoice payment delay per department as a standing
  number instead of an ad hoc join every time someone asks.
- **Scope**: one new gold KPI view, same shape as the existing `mv_procurement_savings_kpi`;
  explicitly *not* changing how `days_late` is computed, *not* touching Power BI, *not* a
  time series.
- **Status**: `inception` — `requirements.md` and `design.md` were already drafted (from an
  earlier session) but explicitly marked "not yet approved or implemented."

So the first real decision point was: **this unit of work is sitting right at the
Inception → Construction gate**, waiting for approval.

## Step 1 — Inception → Construction gate (human approval required)

`requirements.md` was already **frozen at version 1** with four acceptance criteria (one row
per department among paid invoices; `avg_days_late` must equal an independently-computed
`ROUND(AVG(days_late), 2)`; departments with zero paid invoices excluded, not zero-filled;
uniqueness on `department_id`). `design.md` proposed one new gold materialized view,
`mv_avg_payment_delay_kpi`, following the exact shape of the existing
`mv_procurement_savings_kpi.py`.

Design flagged one open risk worth a human decision: **excluding unpaid invoices
(`payment_date IS NULL`) from the average**, rather than zero-filling them, needed explicit
sign-off since it changes the number Finance would see.

Per governance rule #2, the agent that would go on to write the code could not also approve
this gate. Two questions were put to the human approver:

1. *Approve the "exclude unpaid invoices" design decision as-is?* → **Approved as-is.**
2. *Who is the approver of record?* → **Cihan Giray Oner** (cihangiray.oner@gmail.com).

This was logged as the first entry in a new
`ai_dlc/_units_of_work/001-avg-payment-delay-kpi/decision-log.md`:

```
### 2026-08-20 — Inception → Construction
- Spec version: requirements.md v1, design.md (unversioned draft, first pass)
- Approver: Cihan Giray Oner — did not author requirements.md/design.md
- Verdict: approved
- Notes: exclude-unpaid-invoices risk explicitly reviewed and accepted.
```

`unit-of-work.md`'s status line and bolts table were updated to reflect this gate.

## Step 2 — Construction: `ai_dlc/coding`

With the gate passed, `ai_dlc/coding` took over. This skill governs *how* to implement
(plan → get it approved → generate one file at a time → repeat), and delegates the actual
Databricks mechanics to the matching product skill — here, `databricks-pipelines`.

Before writing anything, the existing repo patterns were read to confirm the plan wasn't
guessing:

- `transformations/mv_procurement_savings_kpi.py` — the KPI view shape to copy (fully
  qualified table names, join chain, denormalized dimension columns).
- `transformations/fact_invoices.py`, `dim_project.py`, `dim_department.py` — confirmed the
  join path `fact_invoices.project_id → dim_project.department_id → dim_department`.
- `transformations/quality_tests_gold_uniqueness.py` — the existing pattern for
  `@dp.expect_or_fail("unique_key", "num_entries = 1")` uniqueness tests.
- `resources/pipelines.yml` — confirmed its `libraries.glob: ../transformations/**` already
  picks up any new file automatically, so **no pipeline config change was needed** (and no
  second pipeline was created — this workspace's Free Edition only allows one per type).

The concrete plan (file-by-file, matching `design.md` exactly, no deviation) was:

1. **New** `transformations/mv_avg_payment_delay_kpi.py` — gold materialized view:
   `fact_invoices` → join `dim_project` (for `department_id`) → join `dim_department` (for
   `department_name`), filter `payment_date IS NOT NULL`, group by department, compute
   `paid_invoice_count` and `avg_days_late` (`ROUND(AVG(days_late), 2)`).
2. **Extend** `transformations/quality_tests_gold_uniqueness.py` with
   `test_unique_mv_avg_payment_delay_kpi`.
3. **No change** to `resources/pipelines.yml`.

Both files were generated to match this plan, then validated for config sanity:

```
databricks bundle validate --profile cihan.giray.oner@htecgroup.com
→ Validation OK!
```

## Step 3 — Construction → Review gate

`ai_dlc/review`'s rule is the same as Inception's: **the approver can't be the session that
wrote the code.** A `review-checklist.md` was drafted (copied from
`ai_dlc/templates/resources/review-checklist-template.md`) with everything the agent could
verify objectively — repo conventions followed, `design.md`'s affected-files list matched
exactly, `bundle validate` passed — but two acceptance criteria (the average matching an
independent calculation, and zero-paid departments being excluded) **couldn't be checked
without actually running the pipeline against real data.**

That's a meaningfully different kind of action than writing code — it touches the shared
Databricks workspace — so it was called out explicitly and the human was asked whether to
run it now. Answer: **yes, deploy and run now.**

### What actually happened when it ran

```
databricks bundle deploy --target dev --profile cihan.giray.oner@htecgroup.com
→ Deployment complete!

databricks bundle run finance_cockpit_pipeline --target dev --profile cihan.giray.oner@htecgroup.com
```

The **first** run failed:

```
[INTERNAL_ERROR_BEHAVIOR_CHANGED] Pipeline update paused because Databricks Platform found
a potential regression. The change is automatically reverted...
Detection criteria: logicalPlanChanged, sessionConfigChanged.
```

This is a Databricks platform safety net, not an application bug — it pauses once the first
time it sees a logical plan change (which a brand-new table always is) and self-heals.
Retrying the exact same command succeeded end-to-end: 60+ flows across bronze, silver, and
gold ran, including the new `mv_avg_payment_delay_kpi` flow and its uniqueness test, ending
in `Update ac3380 is COMPLETED.`

### Verifying the acceptance criteria against real data

With the view live at `workspace.dev_finance_cockpit_gold.mv_avg_payment_delay_kpi`, its
output was queried directly and cross-checked with an independently-written SQL query — not
by reading the view's own numbers back at itself.

The KPI view returned 4 departments:

| department_id | department_name | paid_invoice_count | avg_days_late |
|---|---|---|---|
| ODJ-001 | Upravni odjel za komunalno gospodarstvo | 141 | 18.01 |
| ODJ-002 | Upravni odjel za društvene djelatnosti | 116 | 19.38 |
| ODJ-003 | Upravni odjel za razvoj i EU fondove | 92 | 17.26 |
| ODJ-005 | Upravni odjel za opće i pravne poslove | 44 | 18.55 |

An independent query — `ROUND(AVG(days_late), 2)` computed directly from
`fact_invoices` joined to `dim_project`, filtered to `payment_date IS NOT NULL`, grouped by
department — produced **exactly the same four numbers**. A separate query against
`dim_department` (left-joined, so departments with no matching invoices still show up)
confirmed two departments genuinely have zero paid invoices — **ODJ-004** and **ODJ-006** —
and both were correctly absent from the KPI view rather than showing up as a misleading
zero.

That closed out all four frozen acceptance criteria with real evidence, not
self-reported success. The checklist and decision log were updated accordingly, and the
human approver recorded the verdict: **Approved.**

## Step 4 — Operations: deploy record and commit

`ai_dlc/operations` owns the deploy record and monitoring handoff. Since the deploy had
already happened as part of gathering review evidence, this step was mostly about **logging
it properly** rather than doing it again: target (`dev`, the only target `databricks.yml`
defines), the bundle's source commit, the pipeline update ID, and an explicit note that no
`staging`/`prod` target exists yet (flagged as an architecture + human decision, not
something to add silently).

Finally, the changes were committed — scoped only to what this unit of work actually
touched (not the wider `ai_dlc/` skill framework or `.claude/` config, which predate this
session and weren't part of the ask):

```
git add transformations/mv_avg_payment_delay_kpi.py \
        transformations/quality_tests_gold_uniqueness.py \
        ai_dlc/_units_of_work/001-avg-payment-delay-kpi/
git commit -m "Add avg invoice payment delay KPI by department (unit-of-work 001)"
→ 8e3cd9d
```

## Where everything lives now

| What | Where |
|---|---|
| The KPI view itself | `transformations/mv_avg_payment_delay_kpi.py`, live at `workspace.dev_finance_cockpit_gold.mv_avg_payment_delay_kpi` |
| Its quality test | `transformations/quality_tests_gold_uniqueness.py` (`test_unique_mv_avg_payment_delay_kpi`) |
| Frozen requirements | `ai_dlc/_units_of_work/001-avg-payment-delay-kpi/requirements.md` |
| Technical design | `ai_dlc/_units_of_work/001-avg-payment-delay-kpi/design.md` |
| Review checklist + evidence | `ai_dlc/_units_of_work/001-avg-payment-delay-kpi/review-checklist.md` |
| Full audit trail (every gate, approver, eval result) | `ai_dlc/_units_of_work/001-avg-payment-delay-kpi/decision-log.md` |
| Status/bolt history | `ai_dlc/_units_of_work/001-avg-payment-delay-kpi/unit-of-work.md` |

## The shape of the process, generalized

Strip away the specifics of this one KPI and the repeatable pattern is:

1. **State what's already true** (read `unit-of-work.md`, `requirements.md`, `design.md` —
   don't re-derive from scratch or silently redecide something already frozen).
2. **Find the next ungated transition** and stop there — don't self-approve it.
3. **Get a named human decision** on anything genuinely open (a design risk, an approver, a
   verdict) — one targeted question at a time, not a wall of decisions at once.
4. **Implement mechanically** from the approved design — no scope creep, no "while I'm here"
   changes.
5. **Prove it, don't assert it** — run real validation (`bundle validate`, an actual pipeline
   run, an independent SQL check) instead of describing what the code is supposed to do.
6. **Log every gate** with what was approved, by whom, and what evidence backed it, so the
   next person (or the next AI session) can trust the trail without re-doing the work.
