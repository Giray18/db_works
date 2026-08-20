---
name: ai-dlc-review
description: Run the AI-DLC review and approval gate on a completed unit of work in this repo — checklist-driven, named approver, decision log — before merge or deploy. Use after ai_dlc/coding finishes Construction, before ai_dlc/operations deploys anything.
metadata:
  ai_dlc_phase: gate
---

# AI-DLC Review

The approval gate. Called from `ai_dlc/workflow` at the end of Construction (and reused for
the Inception→Construction gate and the pre-deploy gate in Operations — same checklist
pattern, different scope). Its output is a filled `review-checklist.md` and a new entry in
`decision-log.md`.

## Who approves

**The approver must not be the same identity/session that authored the artifact being
reviewed.** If you (the agent) wrote the code, you cannot also be the approver of record —
say so explicitly and ask the human to approve, rather than marking a checklist item
approved on your own authority. This is the single most important rule in this skill; the
rest is mechanical checking.

## Checklist

Copy `ai_dlc/templates/resources/review-checklist-template.md` into the unit of work's
folder and work through it:

- **Correctness** — every `requirements.md` acceptance criterion has a passing test, authored
  from the frozen requirements, not reverse-engineered from what got built.
- **Repo conventions** — fully-qualified table names, no second pipeline, rounding rules,
  numerator/denominator ratios, SCD2 `__END_AT` semantics (see `ai_dlc/coding/SKILL.md` for
  the full list — check the diff against it).
- **Config sanity** — `databricks bundle validate` passes (delegate execution to
  `databricks-dabs`); Unity Catalog grants reviewed if catalog/schema access changed
  (delegate to `databricks-unity-catalog`).
- **Quality tests** — new gold tables/keys have a corresponding test in
  `transformations/quality_tests_gold_uniqueness.py` or an equivalent.

## Decision log entry

Append to `decision-log.md` (from `ai_dlc/templates/resources/decision-log-template.md`)
with: spec version (`requirements.md`/`design.md` version numbers), approver name, eval
result (link or paste the test output), and verdict. This is what makes the unit of work
auditable later — don't skip it even for a small change; write a one-line entry rather than
none.

## Verdicts

- **Approved** → hand to `ai_dlc/operations` for deployment.
- **Approved with changes** → note exactly what changed and re-run the affected checklist
  items, don't re-run the whole thing from scratch unless the change is substantial.
- **Rejected** → back to `ai_dlc/coding` (implementation issue) or `ai_dlc/design`
  (the design itself was wrong) — the decision log entry should say which, so the next bolt
  starts in the right place.
