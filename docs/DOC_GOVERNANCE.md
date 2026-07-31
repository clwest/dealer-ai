---
title: "Dealer AI Kit — Documentation Governance"
status: authoritative
type: governance
adopted: 2026-07-31
adopted_at_session: SESSION_036
supersedes: none
applies_to:
  - All future implementation sessions
  - All AI agent sessions (Claude Code, other agents)
  - All human contributors
---

# Dealer AI Kit — Documentation Governance

> **What this is.** Durable governance for how documentation is
> organized, named, updated, and preserved as the repository grows.
> Adopted 2026-07-31 at SESSION_036 while the project is still
> young (~35 sessions) so the rules land before sprawl.
>
> **Why this exists.** Documentation quality decays continuously
> unless discipline is continuous. The cost of a well-run docs
> tree at 300 sessions is small; the cost of retro-organizing 300
> sessions of unstructured docs is enormous. This document is the
> operating manual that keeps the cost small.
>
> **Precedence.** These rules override individual session
> convenience. `docs/PROJECT_RULES.md` is still the governance
> layer that outranks everything (project-work rules); this doc
> is the governance layer for *the docs themselves*.
>
> **Golden rule.** *Prefer updating an authoritative document over
> creating a new one.* Every rule below serves this.

---

## 1. Six preserved principles

These are the load-bearing principles. Every specific rule below
serves one or more of these.

1. **Keep `/docs` organized continuously**, not through occasional
   cleanup sessions.
2. **Prefer updating authoritative documents** over creating
   parallel versions.
3. **Avoid duplicate documentation.**
4. **Keep active references pointing only to authoritative
   documents.** Historical docs are not linked from active pointers.
5. **Preserve historical documents as immutable records** unless a
   factual correction is required.
6. **Continuously maintain repository organization** as part of
   normal development, not as a separate initiative.

---

## 2. Folder scope contracts

Each folder in `/docs` has a **scope contract** — a one-sentence
answer to "what belongs here?" A file that does not fit a scope
belongs in the `/docs` root, not in a new folder.

### `/docs/` (root)

**Scope.** Primary reference documents and governance. These are
the docs a new contributor reads to understand the project.

**Examples.** `PROJECT_RULES.md`, `PROJECT_WHAT_IT_IS.md`,
`BUILD_PLAN.md`, `CAPABILITY_MATRIX.md`, `BUSINESS_DOMAIN_MAP.md`,
`PROJECT_PIPELINE.md`, `DEALER_KIT_BEHAVIOR_LAYER.md`,
`DEALER_KIT_TRANSLATION_LAYER.md`, `DEALER_KIT_SESSION_START.md`,
`DOC_GOVERNANCE.md` (this file).

**Cap.** ~20 files. If the root exceeds 20, evaluate whether a new
folder is genuinely warranted — but the default answer is *no*,
because most bloat comes from things that belong in an existing
folder or in `/docs/handoffs/` (session-scoped).

### `/docs/research/`

**Scope.** Business-truth research. Answers "how does the business
actually operate?" not "how does the software work?" The corpus
`docs/PROJECT_RULES.md` names as the primary source of business
truth.

**Add here when.** A new department, workflow, or compliance
surface requires research before design (per Research Before
Design chain).

**Do not add here.** Software design docs. Milestone plans. Session
outputs.

**Naming.** `<TOPIC>_MAPPING.md` for department/workflow research;
`<TOPIC>_PIVOT.md` for architectural / persona pivots.

### `/docs/roadmap/`

**Scope.** Roadmap documents and per-milestone planning artifacts.
The implementation contract and its supporting planning passes.

**Examples.** `IMPLEMENTATION_ROADMAP.md` (the master contract),
`ASSISTANT_AGENT_CREATION_ROADMAP.md` (sibling), `MILESTONE_N_PLANNING.md`
(per-milestone planning).

**Add here when.** A milestone requires a planning artifact
distinct from the master roadmap (design memo, migration impact
review, compatibility checklist).

**Naming.** `MILESTONE_<N>_<SHORT_TOPIC>.md` (e.g.
`MILESTONE_1_PLANNING.md`). Milestone numbers align with the
master roadmap's numbering.

**Update discipline.** When a milestone completes, its planning
doc's frontmatter `status:` field flips from `planning` → `shipped`
in the same commit as the closing handoff.

### `/docs/handoffs/`

**Scope.** Immutable per-session handoff artifacts. The historical
record of what shipped, when, and why.

**Add here when.** Every implementation session ends. Always.

**Naming.** `SESSION_<NNN>_<short_slug>.md` — zero-padded
three-digit session number, snake_case slug describing what
shipped.

**Immutability.** Once committed, a handoff is a historical record
and is not edited except for **factual corrections** (e.g. a
mistaken file path, a wrong test count). Reorganization,
re-summarization, or "make it match the new format" is not a
factual correction. Format drift across sessions is acceptable —
the handoffs are snapshots of the session that produced them.

**Do not link handoffs from active pointers.** The active session
pointer is `00-START-NEXT-SESSION.md` and it links only the *most
recent* handoff. Older handoffs are discoverable via `ls docs/handoffs/`
and `git log`; they should not be linked from currently-authoritative
docs. This is the "active references point only to authoritative
documents" rule (principle #4).

### `/docs/onboarding/`

**Scope.** Dealer-facing product onboarding — how a dealership
configures the platform for its store. Not agent onboarding to the
project.

**Examples.** `FREEDOM_FORD_ONBOARDING_PLAN.md`.

**Add here when.** A new onboarding surface (auth-driven signup,
per-tenant provisioning, etc.) requires a plan doc.

### `/docs/demo/`

**Scope.** Demo scripts for showing the platform to prospects.

**Examples.** `COPPER_CANYON_DEMO_SCRIPT.md`,
`FREEDOM_FORD_DEMO_SCRIPT.md`.

**Add here when.** A new demo persona ships that needs its own
script. Do not create a new demo script per prospect — the demo
scripts are per-persona (indie / franchise / etc.), not per-visit.

---

## 3. When to create a new folder

**Default answer: don't.** New folders create navigation cost that
persists for the life of the repo. The cost of one extra folder is
low; the cost of "twelve subfolders each with two files" is high
and irreversible without confusing everyone.

**Create a new folder only when all three are true:**

1. The scope is genuinely new — not a re-slicing of an existing
   scope contract.
2. You expect **at least 5 files** to accumulate in it within the
   next 6 months, based on the roadmap.
3. Cross-referencing from existing docs would benefit from folder
   grouping (e.g. `docs/research/` vs. `docs/roadmap/` is worth
   the split; `docs/governance/` for one file is not).

If any of the three is false, add the file to `/docs/` root or an
existing folder.

**Never create a folder to hold a single file.** If a folder ends
up with one file, move the file up and delete the folder.

---

## 4. Naming conventions

**File names — English.**

- **UPPERCASE_SNAKE_CASE.md** for durable reference and governance
  docs at any level.
- **`SESSION_NNN_short_slug.md`** for handoffs — zero-padded
  three-digit session number, snake_case slug.
- **`MILESTONE_N_<topic>.md`** for milestone planning docs —
  matches the master roadmap's numbering.

**File names — patterns to avoid.**

- Dates in filenames (`docs_2026_07_31.md`). Git tracks dates.
- Author names in filenames.
- `_final`, `_v2`, `_new`, `_updated`, `_old` suffixes. Rename or
  overwrite; do not accumulate versions in the filename.

**Section headings.**

- Sentence-case headings, not Title-Case.
- H1 (`# `) once per document, matching the frontmatter title.
- H2 (`## `) for primary sections, H3 for subsections. Deeper
  nesting is usually a rewrite signal.

**Frontmatter.**

Every durable doc includes YAML frontmatter with at minimum:

```yaml
---
title: "<doc title>"
status: <authoritative | active | planning | shipped | historical>
type: <governance | reference | planning | research | handoff | ...>
---
```

Additional fields are welcome (`generated:`, `sources:`,
`supersedes:`, `applies_to:`) when they clarify the doc's role.

---

## 5. Handling obsolete documents

**A document is obsolete when** its claims no longer match the
codebase or the corpus, and cannot be brought current with a small
edit.

**Three moves are permitted; choose one:**

1. **Update in place.** If a small edit can bring the doc current,
   do it. Update `last_verified:` (or equivalent) in frontmatter.
   *Preferred.*

2. **Supersede.** If a new doc replaces the old one, set the old
   doc's frontmatter to:

   ```yaml
   status: superseded
   superseded_by: docs/path/to/new-doc.md
   superseded_at_session: SESSION_NNN
   ```

   Leave the file in place. Update all active-pointer references
   in other docs to point at the new doc. Do not delete — it's a
   historical artifact from here on.

3. **Retire and delete.** Only when the doc describes work that
   was never shipped, or a plan that was fully abandoned with no
   historical value. Record the deletion in the session handoff.

**Never mix moves.** Do not partially update, half-supersede, or
leave a "we should look at this" comment. A doc's status is one of
the six frontmatter values; ambiguity is worse than any of them.

---

## 6. Preserving historical documents

Handoffs and superseded docs are **immutable historical records**.

**They are not:**

- Rewritten to match a new format.
- Rewritten to match a rename (e.g. `freedom_ford` → `dealer_kit`).
  The historical text preserves the state at the time.
- Deleted to reduce noise.
- Linked from active pointers.

**They are:**

- Discoverable via `ls docs/handoffs/`, `git log`, and full-text
  search.
- Corrected for **factual errors only** (wrong test count, wrong
  commit hash). Editorial changes are not corrections.
- Referenced by other historical docs freely; referenced by active
  docs only when the active doc is describing the historical
  record itself.

**Golden test.** If a future contributor asks "what did SESSION_017
actually ship?", they should be able to read `docs/handoffs/SESSION_017_public_embed_preview.md`
and get an answer that is accurate *as of SESSION_017*, even if
every file it mentions has since been renamed or moved.

---

## 7. Session lifecycle expectations

Every implementation session follows this lifecycle. Steps that
don't apply are skipped, not filled with boilerplate.

### 7.1 Session start

1. Read `00-START-NEXT-SESSION.md` (the current priority pointer).
2. Read the anchor docs it names (typically `PROJECT_RULES.md`,
   `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §current milestone,
   the relevant research doc, `DEALER_KIT_SESSION_START.md`).
3. Read this doc (`DOC_GOVERNANCE.md`) once per new agent, then
   trust the rules.

### 7.2 During the session

- **Prefer updating an authoritative doc** over creating a new one.
  If a fact belongs in `CAPABILITY_MATRIX.md`, update
  `CAPABILITY_MATRIX.md`. Do not create `CAPABILITY_MATRIX_v2.md`
  or `CAPABILITY_UPDATES_2026_07.md`.
- **New docs are the exception, not the rule.** Only create a new
  doc if:
  - It fits a scope contract in §2, AND
  - No existing doc's scope covers it, AND
  - The content will be referenced across sessions (not just this
    one).
- **Update active pointers immediately** when a doc moves, gets
  renamed, or is superseded. Do not defer.

### 7.3 Session end

Every session that shipped code, docs, or decisions produces:

1. **A handoff at `docs/handoffs/SESSION_NNN_<slug>.md`.**
   Immutable once committed.

2. **Updates to authoritative docs** whose claims changed:
   - `CAPABILITY_MATRIX.md` if capabilities changed.
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` if milestone status
     changed. Update the reconciliation summary and the affected
     milestone's status. **Milestone planning docs** (`MILESTONE_N_PLANNING.md`)
     flip `status: planning` → `status: shipped` on completion.
   - `PROJECT_RULES.md`, `DOC_GOVERNANCE.md` only if governance
     itself changed. These changes are rare and require explicit
     user approval.
   - Any doc whose active-pointer references broke because of a
     rename/move in this session.

3. **Overwrite `00-START-NEXT-SESSION.md`** with the next
   session's priority. This file is *always* the most recent
   priority; it is not appended-to.

4. **Do not update:**
   - Prior handoffs (immutable).
   - Research docs (require explicit user approval to change).
   - Docs whose scope this session did not touch.

### 7.4 What NOT to do end-of-session

- Do not create a "session summary" doc parallel to the handoff.
  The handoff *is* the session summary.
- Do not create a "decisions log" or "changelog" doc separate
  from `CAPABILITY_MATRIX.md` and the handoffs. Those already
  cover it.
- Do not rewrite older handoffs to match a new format.
- Do not sweep unrelated docs "while we're here" — that is the
  Scope Discipline rule violated at the docs layer.

---

## 8. Terminal output discipline

**The terminal is an execution interface, not a report generator.**

Session output to the user should be **concise and factual**:

- **What is being done** — one sentence per major step.
- **Why** — only when non-obvious.
- **Important decisions** — briefly, as they're made.
- **Blockers** — immediately, with the specific unblock needed.
- **Completion status** — one clear closing sentence.

**Long-form reasoning belongs in documentation** when it creates
lasting project value, not in session output. If a planning
artifact deserves 400 lines of prose, write it to a file (per §7.2)
and reference it in the terminal; do not scroll it past the user.

**Assume the human operator is following in real time.** They can
see the diff. They can read the file. They do not need a re-narration
of what the tool call just did.

**Rules of thumb:**

- One-sentence progress updates at natural breakpoints.
- End-of-turn summary: 1–2 sentences. What changed, what's next.
- Multi-paragraph explanations only when the user explicitly
  asked for reasoning or when a blocker requires justification.

---

## 9. Naming vs. renaming

Renaming a file is fine when the old name has become misleading.
When you rename:

1. Use `git mv` so history follows the file.
2. Grep for the old path and update **all currently-authoritative
   references** in the same commit.
3. Leave historical handoffs referencing the old path *unchanged*
   (per §6).
4. Note the rename in the session handoff.

Renaming a file is *not* fine when:

- The name is merely inelegant, not misleading.
- The rename is cosmetic and would break active bookmarks / tabs /
  external references without a strong reason.
- The doc is a historical handoff (never rename these).

---

## 10. Enforcement

**For AI agents.** Read this document during orientation. When a
proposed doc change would violate a rule, push back and cite the
rule. When in doubt, ask the user for explicit approval.

**For human contributors.** Same as above.

**For code reviewers.** Flag PRs that:
- Create a new doc when an authoritative doc could have been
  updated.
- Create a new folder without meeting all three §3 conditions.
- Add active-pointer references to historical handoffs.
- Rewrite historical handoffs for editorial reasons.
- Duplicate content across two docs.

**Update discipline.** This document can be updated when:
- The project's shape changes materially (e.g. a new folder
  becomes justified under §3).
- A rule proves counterproductive with specific evidence.
- New governance rules are added.

Do **not** update this document to accommodate one session's
convenience. If a rule is inconvenient for one session, either the
session's approach or the rule is wrong — investigate which.

---

## 11. Rule provenance

Adopted at SESSION_036 (2026-07-31) as the transition from the
young-project phase into the sustained implementation phase. The
project was ~35 sessions old at adoption; the rules are designed
to hold at 300, 3,000, and 30,000 sessions with only additive
changes.

The user's directive at SESSION_036 is captured in the
`SESSION_036` handoff doc under `docs/handoffs/`.

---

## 12. Related documents

- `CLAUDE.md` — session entry point for AI agents; references
  this governance doc.
- `docs/PROJECT_RULES.md` — project-work governance (the layer
  above this doc).
- `docs/DEALER_KIT_SESSION_START.md` — durable orientation index.
- `00-START-NEXT-SESSION.md` — current-session priority (repo
  root).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — implementation
  contract.

---

*End of Documentation Governance.*
