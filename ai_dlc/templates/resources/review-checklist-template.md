# Review Checklist: <unit-of-work id>

Filled out at the Construction → Review gate, by the approver, not the implementer.

## Correctness

- [ ] Every acceptance criterion in `requirements.md` has a passing test, and the test was
      authored from the frozen requirements, not reverse-engineered from the implementation.
- [ ] `design.md`'s affected-files list matches what was actually changed (no silent scope
      creep, no undocumented extra changes).

## Repo conventions

- [ ] Fully-qualified `catalog.schema.table` names on every `@dp.table` /
      `@dp.materialized_view`.
- [ ] No second pipeline created — medallion changes extend the existing pipeline in
      `resources/pipelines.yml`.
- [ ] Monetary columns rounded to 2dp, percentages to 4dp, if gold output changed.
- [ ] Ratios stored as numerator/denominator in fact tables, not pre-computed percentages.
- [ ] SCD2 semantics preserved on silver (`__END_AT` close on missing key, not row delete).

## Config / deployment sanity

- [ ] `databricks bundle validate` passes against the relevant target.
- [ ] Unity Catalog grants reviewed if this changes catalog/schema/table access.
- [ ] Quality tests (`transformations/quality_tests_gold_uniqueness.py` or new equivalents)
      updated for any new gold table/key.

## Governance

- [ ] Approver is not the same identity that authored the design/code being approved.
- [ ] Decision log entry written (`decision-log-template.md`) with spec version, approver,
      eval result, and verdict.

## Verdict

approved / rejected / approved with changes — <one line why>
