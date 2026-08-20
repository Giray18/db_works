# Unit of Work: <id> — <short title>

A unit of work is a feature scoped small enough to finish in a few bolts (hours-to-days
cycles), not a multi-week epic. One unit of work = one folder under
`ai_dlc/_units_of_work/<id>-<slug>/` holding this file plus the requirements, design,
decision-log, and (if relevant) ADR and runbook documents it produces.

## Intent

<One or two sentences: what business or data need triggered this. Not the solution — the
need. e.g. "Finance wants procurement cycle time by department, which today requires a
manual join across three sheets.">

## Scope

- In scope: <bullet list>
- Out of scope: <bullet list — be explicit, this is what stops scope creep mid-bolt>

## Affected surfaces

<Check all that apply, and name the specific files/resources — this determines which
product skill(s) `ai_dlc/coding` will delegate to.>

- [ ] Medallion pipeline (`transformations/*.py`, `resources/pipelines.yml`)
- [ ] DABs bundle / jobs (`databricks.yml`, `resources/jobs.yml`)
- [ ] Unity Catalog (`resources/schemas.yml`, `resources/volumes.yml`, grants)
- [ ] Power BI semantic model (`pbi/`)
- [ ] rag_agent (`rag_agent/`)
- [ ] Other: <name>

## Bolts

<Running list — add a row per bolt as work happens, don't pre-plan all of them upfront>

| Bolt | Phase | Outcome | Date |
|------|-------|---------|------|
| 1 | Inception | requirements.md + design.md drafted | |

## Status

`inception` / `construction` / `review` / `operations` / `done`
