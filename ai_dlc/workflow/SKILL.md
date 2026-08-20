---
name: ai-dlc-workflow
description: Orchestrate a Databricks unit of work (new pipeline table, job, catalog change, or rag_agent feature in this Finance Cockpit repo) through the AI-DLC lifecycle — Inception, Construction, Operations — in short bolts with human approval gates. Use when starting new Databricks work, or asked to "run AI-DLC" / "follow the AI-DLC process" / "start a unit of work".
metadata:
  ai_dlc_phase: entry-point
---

# AI-DLC Workflow

This is the entry point into this repo's AI-DLC skill library. AI-DLC (AI-Driven
Development Life Cycle) replaces two-week sprints with **bolts** — work cycles of hours to
days, each sized to one validated decision — and replaces epics with **units of work**:
features scoped small enough to finish in a handful of bolts. The other seven `ai_dlc/*`
skills implement one phase or cross-cutting concern each; this skill routes between them and
keeps the governance discipline intact.

## The governance rules (non-negotiable)

These are what separates AI-DLC from "let the agent write code and hope":

1. **Acceptance tests are frozen during Inception**, before Construction starts, and are
   authored independently of whoever implements — see `ai_dlc/design`.
2. **Every gate has a named approver who is not the prompter/implementer** — see
   `ai_dlc/review`.
3. **Every gate is logged** — spec version, approver, eval result — in a decision log, so the
   whole unit of work is auditable after the fact.

If you're tempted to skip a gate because "it's a small change," don't silently skip it —
say so explicitly and let the human confirm that's acceptable for this unit of work.

## The three phases

### 1. Inception — turn intent into a frozen spec

Trigger: a new business need lands (e.g. "we need procurement cycle time by department",
"add a tool to rag_agent that answers budget-variance questions").

1. Start the unit of work: copy `ai_dlc/templates/resources/unit-of-work-template.md` into
   `ai_dlc/_units_of_work/<id>-<slug>/unit-of-work.md`, fill in Intent, Scope, and Affected
   surfaces.
2. Invoke `ai_dlc/architecture` if this needs a new/changed architecture artifact (new
   catalog/schema, a topology change, an ADR).
3. Invoke `ai_dlc/design` to produce and freeze `requirements.md` and draft `design.md`.
4. Log the Inception → Construction gate in the decision log (via `ai_dlc/review`'s format)
   once requirements are approved.

### 2. Construction — Mob Construction loop

Trigger: `requirements.md` is frozen and `design.md` is approved.

1. Invoke `ai_dlc/coding`, which runs the propose-plan → get-approval → generate loop and
   delegates the actual Databricks mechanics to the matching product skill
   (`databricks-pipelines`, `databricks-dabs`, `databricks-apps-python`, etc. — see
   `ai_dlc/coding/SKILL.md` for the mapping).
2. Invoke `ai_dlc/review` once implementation and tests are ready. This is the approval
   gate before anything ships.

### 3. Operations — deploy and watch

Trigger: `ai_dlc/review` recorded an "approved" verdict.

1. Invoke `ai_dlc/operations` to deploy via DABs and set up/verify monitoring.
2. If something breaks later, `ai_dlc/operations` also owns runbooks — it doesn't
   automatically spin up a new unit of work unless the fix requires a code change, in which
   case loop back to Inception for that fix.

## Repo-specific routing note

This repo (`db_works` — Finance Cockpit Lakehouse) runs on **Databricks Free Edition, which
allows only one active pipeline per pipeline type.** Bronze, silver, and gold all live in the
single pipeline defined in `resources/pipelines.yml`. Any unit of work that touches the
medallion pipeline extends that one pipeline — it never proposes a second one. Flag this
explicitly during Inception if a request seems to imply a separate pipeline.

## Quick reference

| Phase | Skill(s) | Key artifact |
|---|---|---|
| Inception | `ai_dlc/architecture`, `ai_dlc/design` | `requirements.md` (frozen), `design.md` |
| Construction | `ai_dlc/coding`, `ai_dlc/review` | code + tests, `review-checklist.md` |
| Operations | `ai_dlc/operations` | deploy, `runbook-*.md` |
| Cross-cutting | `ai_dlc/templates`, `ai_dlc/skills` | document skeletons, meta-conventions |
