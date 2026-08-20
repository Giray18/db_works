---
name: ai-dlc-templates
description: Reusable AI-DLC document templates for this repo — unit of work, requirements, design, decision log, ADR, review checklist, runbook. Use when another ai_dlc skill needs a template to fill in, or when asked to start a new unit-of-work document.
metadata:
  ai_dlc_phase: cross-cutting
---

# AI-DLC Templates

Seven fillable Markdown skeletons live in `ai_dlc/templates/resources/`. Every other
`ai_dlc/*` skill points here instead of inventing its own document format — that
consistency is what makes a decision log or a requirements doc comparable across units of
work.

| Template | Used by | Produces |
|---|---|---|
| `unit-of-work-template.md` | `ai_dlc/workflow` | `ai_dlc/_units_of_work/<id>-<slug>/unit-of-work.md` |
| `requirements-template.md` | `ai_dlc/design` | `.../requirements.md` (frozen before Construction) |
| `design-template.md` | `ai_dlc/design` | `.../design.md` |
| `decision-log-template.md` | `ai_dlc/review` (and every gate) | `.../decision-log.md` |
| `adr-template.md` | `ai_dlc/architecture` | `.../adr-<n>-<slug>.md` |
| `review-checklist-template.md` | `ai_dlc/review` | `.../review-checklist.md` |
| `runbook-template.md` | `ai_dlc/operations` | `.../runbook-<scenario>.md` |

## How to use a template

1. Copy the template file into the unit of work's folder,
   `ai_dlc/_units_of_work/<id>-<slug>/`, renamed as shown in the table above (create the
   folder on first use — it doesn't exist until a unit of work starts).
2. Fill in every placeholder (`<...>`). Don't delete sections that don't apply yet — mark
   them "N/A" with a reason, so a reader can tell "not applicable" from "forgot."
3. Treat `requirements.md` as frozen once written: further changes bump a version number and
   get a decision-log note, they don't silently overwrite the acceptance criteria.

## When to add a new template

Only when an existing one genuinely doesn't fit — check `ai_dlc/skills/SKILL.md` first for
the convention on extending the ai_dlc set itself before adding an eighth template file.
