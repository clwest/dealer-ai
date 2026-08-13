---
title: "SESSION_036 handoff — documentation governance + repository organization"
status: historical
type: handoff
date: 2026-07-31
session: 036
commit: (pending)
---

# SESSION_036 — Documentation governance + repository organization

## What shipped

A repository-maintenance session focused exclusively on
documentation governance. No application code changed. Adopted
governance rules that scale from the current ~35 sessions to
hundreds or thousands without retro-organizing.

### 1. `docs/DOC_GOVERNANCE.md` (new, authoritative)

12 sections covering:

- Six preserved principles (organize continuously, update over
  create, no duplicates, active refs → authoritative docs,
  immutable history, continuous maintenance).
- Folder scope contracts for `/docs/`, `/docs/research/`,
  `/docs/roadmap/`, `/docs/handoffs/`, `/docs/onboarding/`,
  `/docs/demo/`.
- Three-condition test for creating a new folder (default: don't).
- Naming conventions (filenames, headings, frontmatter).
- Obsolete-doc handling (update / supersede / retire — never mix).
- Historical-doc preservation (immutable except factual
  corrections).
- Session lifecycle expectations (start / during / end).
- Terminal output discipline (execution interface, not report
  generator).
- Renaming rules (`git mv` + reference sweep in same commit;
  never rename historical handoffs).
- Enforcement expectations for AI agents, humans, reviewers.

### 2. `/docs` audit

Current structure judged sound. Zero moves required. Five
subfolders (`handoffs/`, `research/`, `roadmap/`, `onboarding/`,
`demo/`) each have clear scope. `docs/` root has 17 files (post
addition of `DOC_GOVERNANCE.md`); still under the soft ~20-file
cap. `docs/onboarding/` is thin (1 file) but will fill as
Milestone 1 auth/tenancy work ships new onboarding surfaces.

### 3. `CLAUDE.md` — hand-written governance section added

New "Documentation governance (hand-written)" section appended
after the "Project rules (hand-written)" section. Summarizes the
six principles + practical defaults + terminal output discipline.
Survives `context-kit adopt` re-runs (outside the adopt-managed
block).

### 4. Auto-memory entries (persistent across sessions)

Three new entries indexed in `MEMORY.md`:

- `doc_governance.md` (reference) — pointer to
  `docs/DOC_GOVERNANCE.md`.
- `feedback_prefer_updating_authoritative_docs.md` (feedback) —
  never create parallel/changelog/summary docs.
- `feedback_terminal_output_discipline.md` (feedback) — terminal
  is execution interface, not report generator.

Future sessions will apply the rules without re-prompting.

## Files touched

**New:**

- `docs/DOC_GOVERNANCE.md`
- `docs/handoffs/SESSION_035_milestone_1_planning_and_roadmap_reorg.md`
- `docs/handoffs/SESSION_036_doc_governance_and_repo_org.md`

**Modified:**

- `CLAUDE.md` (hand-written governance section)
- `00-START-NEXT-SESSION.md` (overwritten for SESSION_037 = M1
  implementation)

**Memory (outside repo):**

- `.claude/projects/.../memory/doc_governance.md`
- `.claude/projects/.../memory/feedback_prefer_updating_authoritative_docs.md`
- `.claude/projects/.../memory/feedback_terminal_output_discipline.md`
- `.claude/projects/.../memory/MEMORY.md` (index updated)

## No code changed

Test baseline unchanged: 1,300 pass, 1 skipped. No backend or
frontend behavior modified.

## What's next

**SESSION_037 — Milestone 1 implementation** per
`docs/roadmap/MILESTONE_1_PLANNING.md`. Acceptance contract:
every item in the compatibility checklist (§3 of that doc)
verifies true.

## Deferred / not addressed

- **No file renames.** The audit surfaced no misleading filenames
  worth renaming under §9 of DOC_GOVERNANCE.
- **No historical handoffs edited.** Per §6, historical docs stay
  as-is. The handoffs that still reference `docs/IMPLEMENTATION_ROADMAP.md`
  or `docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md` are
  accurate as-of their session date and are not touched.
- **`docs/DEFERRED_IDEAS.md`** still does not exist. First idea
  that doesn't fit a milestone plan doc will create it (per
  `PROJECT_RULES.md` §Discovery Rule).
