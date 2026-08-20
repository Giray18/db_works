---
name: ai-dlc-coding
description: Implement an approved design.md for this repo in tight plan-then-generate loops (AI-DLC Mob Construction). Use during AI-DLC Construction once requirements.md is frozen and design.md is approved — not for ad hoc coding outside a unit of work.
metadata:
  ai_dlc_phase: construction
---

# AI-DLC Coding (Mob Construction)

Called from `ai_dlc/workflow` once `design.md` for a unit of work is approved. This skill
governs *how* to implement, not the Databricks mechanics themselves — those come from the
matching product skill.

## The loop

Mob Construction is not "generate all the code and show the diff." It's:

1. **Plan** — restate `design.md`'s Affected files list as a concrete, file-by-file plan
   (what changes in each file, in what order).
2. **Get it approved** — surface the plan before writing code, especially if it deviates at
   all from `design.md` (deviation means going back to `ai_dlc/design`, not silently
   improvising).
3. **Generate** — implement one file (or one tight cluster of files) at a time.
4. **Repeat** — for the next file, rather than a single big-bang diff across the whole unit
   of work. This keeps each step small enough to actually validate.

## Delegate mechanics to the matching product skill

This skill does not duplicate Databricks how-to content that already exists — it routes to
it:

| Touching... | Use skill |
|---|---|
| `transformations/*.py`, `resources/pipelines.yml` | `databricks-pipelines` |
| `databricks.yml`, `resources/jobs.yml`, `resources/*.yml` bundle config | `databricks-dabs` |
| `resources/schemas.yml`, `resources/volumes.yml`, grants | `databricks-unity-catalog` |
| `rag_agent/` (FastAPI/Flask-style app) | `databricks-apps-python` |
| Ad hoc query/exploration while implementing | `databricks-data-discovery` |

## Repo conventions to hold constant while generating code

- Fully-qualified `catalog.schema.table` names on every `@dp.table` / `@dp.materialized_view`
  decorator — never a bare table name, since bronze/silver/gold share one pipeline
  publishing to different schemas.
- Bronze is append-only; don't add `allowOverwrites` or dedup-on-write logic there — that's
  what silver's `create_auto_cdc_from_snapshot_flow` is for.
- Monetary output columns rounded to 2 decimals, percentages to 4, on gold tables.
- Ratios as raw numerator/denominator columns in fact tables; pre-computed percentage
  columns only belong in the fixed-grain KPI materialized views.
- New gold table or key → add/extend a uniqueness test in
  `transformations/quality_tests_gold_uniqueness.py` in the same bolt, not as a follow-up.
- No second pipeline. Ever, on this Free Edition workspace. New medallion work is a new
  `@dp.table`/`@dp.materialized_view` inside the existing `resources/pipelines.yml` entry.

## Tests are not self-graded

`design.md`'s Test plan maps to `requirements.md`'s acceptance criteria, which were frozen
*before* this step. Implement the tests as written there — don't rewrite the acceptance
criteria to match whatever the implementation happens to produce. If a criterion turns out
to be untestable as written, that's a finding to take back to `ai_dlc/design`, not something
to quietly paper over.

## Hand off

Once the plan is fully implemented and tests pass locally, hand to `ai_dlc/review` for the
approval gate. Don't self-merge or self-deploy from here.
