---
name: ai-dlc-design
description: Write frozen requirements.md and design.md plus acceptance tests for a Databricks unit of work in this repo before implementation starts (AI-DLC Construction gate). Use for new tables, pipeline changes, job changes, catalog changes, or rag_agent features, before writing any code.
metadata:
  ai_dlc_phase: inception
---

# AI-DLC Design

Called from `ai_dlc/workflow` during Inception, after `unit-of-work.md` exists and (if
needed) `ai_dlc/architecture` has confirmed the topology. Produces the two documents that
Construction is *not allowed to deviate from* without going back through this gate.

## Step 1 — requirements.md (freeze this first)

Copy `ai_dlc/templates/resources/requirements-template.md` to
`ai_dlc/_units_of_work/<id>-<slug>/requirements.md`. The critical governance move here:
**write the acceptance criteria before looking at how you'd implement them.** If you
(the agent) will also be writing the implementation, be explicit that these criteria need a
human approver at the Inception→Construction gate who isn't rubber-stamping their own draft —
that's `ai_dlc/review`'s job, but it starts with a requirements doc worth reviewing.

Ask clarifying questions rather than assuming when the request is ambiguous (this is "Mob
Elaboration" — the interrogate-before-assuming step). Record what was assumed vs. confirmed
in the template's "Assumptions surfaced during elaboration" section.

Mark the file's Status line frozen once approved. After freezing, any change is a new
version + a decision-log note, not a silent edit.

## Step 2 — design.md

Copy `ai_dlc/templates/resources/design-template.md` to the same folder. This is the
technical proposal Construction will mechanically follow.

Style references already in this repo — point to the closest match rather than inventing a
new pattern:

- New gold fact table → `transformations/fact_invoices.py` or
  `transformations/fact_procurement_bids.py`.
- New gold dimension → `transformations/dim_project.py` or `transformations/dim_contract.py`
  (note SCD2 pattern there if the dimension needs history).
- New silver table from a snapshot source → any `transformations/*.py` using
  `create_auto_cdc_from_snapshot_flow` (e.g. `contracts.py`, `invoices.py`) — missing key on
  a refresh means SCD2 close (`__END_AT`), not row delete.
- New KPI → `transformations/mv_procurement_savings_kpi.py` or
  `mv_project_realization_kpi.py` (materialized view, fixed grain, percentages allowed here
  specifically because it's not meant to be re-aggregated).
- rag_agent feature → `rag_agent/tools.py` / `rag_agent/multi_agent_patterns/` depending on
  whether it's a single tool or a new agent pattern.

Fill in the design template's Test plan table mapping each requirements.md acceptance
criterion to a concrete test — prefer extending
`transformations/quality_tests_gold_uniqueness.py`'s pattern over inventing a new test
framework.

## Step 3 — hand off

Once both documents exist and are approved (log the gate via `ai_dlc/review`'s decision-log
format), hand back to `ai_dlc/workflow` to proceed to `ai_dlc/coding`.
