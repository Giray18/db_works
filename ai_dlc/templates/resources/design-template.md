# Design: <unit-of-work id>

Technical approach for satisfying `requirements.md` (version <n>). This is what gets proposed,
argued about, and approved *before* code is generated — Construction should be a mechanical
follow of this document, not where the real design decisions get made.

## Approach

<One paragraph: the shape of the solution. Which medallion layer(s), which existing pattern
it follows (name the file, e.g. "follows `transformations/fact_invoices.py`"), and why this
approach over alternatives considered.>

## Data model

<For pipeline/table work:>
- Layer: bronze / silver / gold
- Table type: `@dp.table` (streaming/append) or `@dp.materialized_view`
- Grain: <one row per ...>
- Key(s): <...>
- CDC strategy if silver: snapshot-CDC (`create_auto_cdc_from_snapshot_flow`) — confirm
  missing-key-on-refresh means SCD2 close (`__END_AT`), not delete.
- Schema: <column list with types, or "extends <existing table>">

## Affected files

<Concrete file list this design will touch, one line each, e.g.:>
- `transformations/fact_x.py` (new)
- `resources/pipelines.yml` (add table to existing single pipeline — do not create a new one)
- `transformations/quality_tests_gold_uniqueness.py` (extend with a uniqueness test on `<key>`)

## Test plan

<How each acceptance criterion in requirements.md gets checked. Prefer extending the
existing quality-test pattern over inventing a new test framework.>

| Acceptance criterion | Test |
|---|---|
| 1 | ... |

## Risks / open questions

<Anything still uncertain going into Construction — flag it here rather than silently
deciding during coding.>
