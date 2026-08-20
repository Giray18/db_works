---
name: ai-dlc-skills
description: Author new AI-DLC skills, checklists, or eval standards consistent with this repo's ai_dlc framework. Use when extending the ai_dlc skill set itself — a new phase skill, a new approval checklist, or a new eval-standard definition.
metadata:
  ai_dlc_phase: meta
---

# AI-DLC Skill Authoring

This skill governs how the `ai_dlc/` library itself grows. It exists because a skill library
that gets extended ad hoc drifts into inconsistent formats fast — this keeps new additions
matching the pattern the other seven skills already establish.

## The two-file pattern (keep it when adding anything)

Every ai_dlc skill has:

1. **Canonical content** at `ai_dlc/<name>/SKILL.md` — the real, full instructions, git-tracked
   and readable as plain docs.
2. **A pointer skill** at `.claude/skills/ai-dlc-<name>/SKILL.md` — same `description` (so
   skill matching works without opening the file), a body that just says to read and follow
   the canonical file. This is what makes the skill invocable via the `Skill` tool without
   duplicating content in two places.

When adding a new skill, create both files, and keep the two `description` fields
byte-for-byte identical.

## Frontmatter conventions used across `ai_dlc/*`

```yaml
---
name: ai-dlc-<name>          # matches the pointer skill's directory name
description: <what it's for> # specific enough to match on, mentions "Use when..."
metadata:
  ai_dlc_phase: inception | construction | gate | operations | cross-cutting | meta | entry-point
---
```

## When to add a new top-level category vs. extend an existing one

- **New top-level `ai_dlc/<name>/` folder**: only if the work doesn't fit any of
  Inception/Construction/Operations/cross-cutting as currently scoped — e.g. a genuinely new
  phase, not a variant of an existing one. This is rare; the current eight cover the AI-DLC
  lifecycle for this repo's kind of work.
- **New file under an existing skill's folder**: the common case. A new template →
  `ai_dlc/templates/resources/`. A new checklist variant for a specific surface (e.g. a
  Power BI-specific review checklist) → still lives conceptually under `ai_dlc/review`, as an
  additional resource file it references, not a new top-level folder.

## Authoring a new eval standard or approval checklist

Follow the same governance rules the rest of the library enforces:

- The standard/checklist must be usable by someone who is **not** the implementer — write it
  so a different reviewer could pick it up cold.
- Acceptance criteria it checks against must already be **frozen** somewhere (a
  `requirements.md`) — a checklist that invents its own bar at review time defeats the point.
- Reference this repo's actual conventions (medallion/DABs/Unity Catalog specifics) rather
  than generic software checklist boilerplate — that's what makes these skills useful for
  training on *this* repo instead of being interchangeable with any repo's AI-DLC setup.

## Don't duplicate the product skills

If what you're about to write is really "how to configure a Lakeflow pipeline" or "how DABs
targets work," that belongs in the existing `databricks-pipelines` / `databricks-dabs`
skills, not a new `ai_dlc/` skill. Keep `ai_dlc/*` scoped to the *process* (bolts, gates,
approval, governance) and let it delegate mechanics outward, as `ai_dlc/coding` and
`ai_dlc/operations` already do.
