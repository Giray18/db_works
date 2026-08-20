# Requirements: <unit-of-work id>

**Status: FROZEN as of <date> / version <n>.** Once frozen, changes to this file require a
new version number and a note in the decision log explaining why — the acceptance criteria
below are the evaluation bar for Construction and must not silently drift to match whatever
got built.

## Business intent

<Restated from the unit-of-work Intent, expanded with any clarifying answers the
requester gave during Mob Elaboration.>

## Assumptions surfaced during elaboration

<List anything ambiguous that was resolved by asking, not by guessing — this is the AI's
job during Inception: interrogate, don't assume. e.g. "Assumed 'active contracts' means
`__END_AT IS NULL` in `dim_contract`, confirmed with requester.">

## Acceptance criteria

<Concrete, testable statements. Each one should map to an assertion in a test file — these
are what `ai_dlc/review` checks against, and they must be authored here, before
Construction, by someone other than whoever will implement.>

1. Given <input/state>, when <action>, then <observable outcome>.
2. ...

## Non-functional constraints

- [ ] Respects the one-pipeline-per-type limit (Free Edition) — no new pipeline, extend the
      existing one in `resources/pipelines.yml` if this touches the medallion pipeline.
- [ ] Monetary columns rounded to 2 decimals, percentage columns to 4, if this produces gold
      output.
- [ ] Ratios stored as raw numerator/denominator in fact tables, not pre-computed percentage
      columns (percentages only belong in fixed-grain KPI materialized views).
- [ ] Any other constraint specific to this unit of work: <...>

## Out of scope

<Copied from unit-of-work.md Scope section, restated as explicit non-goals.>
