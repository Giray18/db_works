---
name: ai-dlc-architecture
description: Produce or update architecture artifacts for this Finance Cockpit lakehouse — medallion bronze/silver/gold diagram, Unity Catalog catalog/schema/table topology, DABs bundle layout, ADRs — during AI-DLC Inception or before a significant Operations change. Use for architecture diagrams, topology questions, or architecture decision records.
metadata:
  ai_dlc_phase: inception
---

# AI-DLC Architecture

Called from `ai_dlc/workflow` during Inception (before a unit of work's design is written)
or from `ai_dlc/operations` before a significant infrastructure change. Its job is to keep
the repo's *existing* architecture artifacts in sync with reality, and to record any new
architecture decision as an ADR — not to re-derive the architecture from scratch each time.

## Existing sources of truth (read these first, don't guess)

- `docs/medallion_pipeline_architecture.drawio` — the medallion diagram (editable source),
  exported to `docs/medallion_pipeline_architecture.drawio.png` for the README. If a unit of
  work changes the pipeline shape (new table, new flow), **edit the `.drawio` and re-export
  the PNG** so the diagram doesn't silently go stale — this is the repo's own stated
  convention, not a new one being introduced here.
- `resources/pipelines.yml` — the single Lakeflow pipeline (bronze+silver+gold). Reminder:
  Free Edition allows only one pipeline per type, so this file has exactly one pipeline
  entry, publishing to multiple schemas by fully-qualified name on each `@dp.table`.
- `resources/schemas.yml` / `resources/volumes.yml` — Unity Catalog topology: which
  catalogs/schemas exist, which volume backs the raw Excel landing zone.
- `resources/jobs.yml` — job topology (e.g. the Excel→CSV split task).
- `databricks.yml` — DABs bundle definition and targets (currently just `dev`).

## What this skill produces

1. **Diagram updates** — when a unit of work changes the pipeline's shape. Delegate the
   actual catalog/schema/grant mechanics to the `databricks-unity-catalog` skill and bundle
   structure questions to `databricks-dabs`; this skill's job is keeping the *picture* and
   the *topology docs* honest, not re-teaching Unity Catalog or DABs.
2. **ADRs** — for decisions worth recording so they aren't re-litigated later. Use
   `ai_dlc/templates/resources/adr-template.md`, saved as
   `ai_dlc/_units_of_work/<id>-<slug>/adr-<n>-<slug>.md` if tied to a unit of work, or under
   a repo-wide `ai_dlc/_adrs/` folder (create on first use) if it's a standing decision not
   scoped to one unit of work. Good candidates from this repo's own history: "one pipeline
   for all medallion layers", "snapshot-CDC over full-reload for silver", "ratios as
   numerator/denominator, not stored percentages."
3. **Topology sanity check** — before Construction starts on anything touching catalogs,
   schemas, or the pipeline, confirm the design in `ai_dlc/design`'s `design.md` doesn't
   contradict `resources/schemas.yml` / `resources/pipelines.yml` as they currently stand.

## Handing off

Once the diagram/topology is updated (or confirmed unchanged) and any ADR is written, hand
back to `ai_dlc/workflow` to proceed to `ai_dlc/design`.
