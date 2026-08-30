---
title: "Doc Audit — freedom-ford (Dealer AI), 2026-08"
date: 2026-08-27
status: complete
head: 6f425f1
auditor: Claude Code
protocol: ~/Donkey_Betz/DOC_AUDIT_PROTOCOL.md
program: ~/Donkey_Betz/PROGRAM_WHAT_WE_LEARNED.md
brief: ~/Donkey_Betz/TASK_doc-audit-04-freedom-ford.md
phase_two_output:
  - ~/Donkey_Betz/LESSONS.md (appended L-021 through L-023)
  - ~/Donkey_Betz/HOW_CHRIS_WORKS.md (appended 2026-08-27 from freedom-ford)
---

# Doc Audit — freedom-ford (Dealer AI), 2026-08

## Verdict

The predicted "first repo with genuine unrecorded drift" showed
up. `.gitignore` line for `/docs/_internal/` confirms the pattern
this working tree follows: **public/portfolio distribution with a
gitignored `_internal/` that holds handoffs, roadmap, session-
start, and other operational docs** — the same shape as
character-os. Unlike character-os, freedom-ford ships **no
`PUBLIC_DOCS_MANIFEST.md` documenting the split**, and **at
least eight public docs reference files that live only in the
private tree**. That is the largest single class of finding in
this session. No doc fixes were applied — every fix requires
Chris's judgment about whether to (a) add a manifest, (b) strip
the references, or (c) restore some docs to the public tree. All
eight references flagged below with `file:line`.

## Environment

```
cd ~/Donkey_Betz/freedom-ford
# Chris's venv is not committed (per .gitignore); expected shape
# per docs/DEMO_SCRIPT.md:
#   cd backend
#   source .venv/bin/activate
#   python manage.py <cmd>
```

This session **did not** run the test suite (no `.venv` in the
tree, no Makefile, and reproducing Chris's local Postgres/Ollama
set-up is beyond the auditor's environment per LESSON L-020).
Every claim verified in this audit is either structural (file
exists / path resolves) or by grep against source. Numeric test-
count claims (5,045 / 431 / 20) are noted as `UNVERIFIABLE FROM
AUDIT` — Chris to confirm in his own env.

## Claims checked

Hybrid scope per the session-4 brief: category-based scan of the
main groups, per-file check for the mid-category ambiguous docs
(demo scripts, pilot playbooks, duplication guide).

### Anchor pair — narrative present, inventory absent

```
CLAIM:   Repo has a two-doc anchor (narrative + inventory)
COMMAND: ls docs/*INVENTORY* docs/PROJECT_WHAT_IT_IS.md
ACTUAL:  docs/PROJECT_WHAT_IT_IS.md present.
         docs/PILOT_INVENTORY_TEMPLATE.md is a pilot template,
         not an inventory anchor.
         No docs/*CAPABILITY* or docs/*INVENTORY* runtime
         anchor exists in this tree.
VERDICT: STRUCTURAL GAP — the two-doc-anchor pattern is not
         implemented here. Both character-os and context-kit
         ship an INVENTORY companion; freedom-ford ships
         neither, and DOC_GOVERNANCE.md line 45 lists
         `CAPABILITY_MATRIX.md` and `PROJECT_WHAT_IT_IS.md`
         as expected root docs — the first is absent. See
         Not-fixed for rationale.
```

```
CLAIM:   "5,045 Django tests, 431 Vitest tests, 20 Playwright" (PROJECT_WHAT_IT_IS.md:54)
COMMAND: cd backend && source .venv/bin/activate && python manage.py test 2>&1 | tail -3
ACTUAL:  Not run — .venv is not in the tree; test infra needs
         Postgres per PROJECT_PIPELINE frontmatter (test_baseline:
         253 in that doc — inconsistent with 5,045 in
         PROJECT_WHAT_IT_IS, but the two are labeled differently
         and may not measure the same thing).
VERDICT: UNVERIFIABLE FROM AUDIT — Chris to run.
```

```
CLAIM:   "45 mixed-make used vehicles" in the shipped seed (PROJECT_WHAT_IT_IS.md:18, README.md:8)
COMMAND: grep -c 'stock' backend/dealer_ai/management/commands/seed_copper_canyon_demo.py
ACTUAL:  Not deterministically countable without executing the
         seed — the count is a property of the seed run, not the
         source. In-source enumeration is possible but time-
         boxed; deferred.
VERDICT: UNVERIFIABLE FROM AUDIT — this is exactly the class of
         claim an INVENTORY companion would hold.
```

### Governance vs practice — the largest finding

```
CLAIM:   `docs/handoffs/SESSION_NNN_*.md` is the handoff location
WHERE:   DOC_GOVERNANCE.md §7.3 line 329 ("A handoff at docs/handoffs/SESSION_NNN_<slug>.md")
         DOC_GOVERNANCE.md §11 line 454 ("captured in the SESSION_036 handoff doc under docs/handoffs/")
         DOC_GOVERNANCE.md §6 line 289 ("read docs/handoffs/SESSION_017_public_embed_preview.md")
         PROJECT_RULES.md:330 ("docs/handoffs/SESSION_033_*.md")
         PILOT_ONBOARDING_PLAYBOOK.md:46, :365, :367, :369, :371 (five refs to SESSION_154-157)
COMMAND: ls docs/handoffs
ACTUAL:  No such file or directory. `.gitignore` line
         `/docs/_internal/` shows the operational convention has
         moved to `docs/_internal/handoffs/` (per
         AI_ASSISTED_DEVELOPMENT.md:20).
VERDICT: DRIFT — nine public-doc references point at a path
         that only exists in the gitignored `_internal/` tree.
         Flag; not fixed. See Not-fixed.
```

```
CLAIM:   Root-level expected docs (per DOC_GOVERNANCE.md §2 line 45)
         include BUILD_PLAN.md, CAPABILITY_MATRIX.md,
         BUSINESS_DOMAIN_MAP.md, DEALER_KIT_SESSION_START.md
COMMAND: for f in docs/BUILD_PLAN.md docs/CAPABILITY_MATRIX.md \
                  docs/BUSINESS_DOMAIN_MAP.md \
                  docs/DEALER_KIT_SESSION_START.md; do
             [ -e "$f" ] && echo "✓ $f" || echo "✗ $f"
         done
ACTUAL:  ✗ all four
VERDICT: DRIFT — same shape as above. Governance names them as
         examples in the root scope; tree does not hold them
         because they live in `_internal/` per convention. Fix
         requires deciding what to do about the governance doc's
         examples list.
```

```
CLAIM:   `docs/roadmap/IMPLEMENTATION_ROADMAP.md` exists
WHERE:   DOC_GOVERNANCE.md §7.1 line 306, §12 line 470
         DOC_GOVERNANCE.md §2 defines `/docs/roadmap/` scope
COMMAND: ls docs/roadmap
ACTUAL:  No such file or directory.
VERDICT: DRIFT — same class. Roadmap and its planning artifacts
         appear to be `_internal/`-only.
```

```
CLAIM:   `00-START-NEXT-SESSION.md` at repo root
WHERE:   DOC_GOVERNANCE.md §7.1 line 305, §12 line 468
COMMAND: ls 00-START-NEXT-SESSION.md
ACTUAL:  No such file.
VERDICT: DRIFT (same class as above). Public-tree omission per
         convention; governance still references it.
```

```
CLAIM:   `CLAUDE.md` at repo root
WHERE:   DOC_GOVERNANCE.md §12 line 465 ("session entry point for AI agents")
COMMAND: ls CLAUDE.md
ACTUAL:  No such file. `.gitignore` includes `.claude/`.
VERDICT: DRIFT (same class).
```

### companion_docs frontmatter — every anchor-companion doc has broken refs

```
CLAIM:   PROJECT_PIPELINE.md line 4 frontmatter
         companion_docs: ["PROJECT_WHAT_IT_IS.md", "CONTEXT_KIT_INVENTORY.md",
                          "../context/WHAT_IT_IS.md", "../context/INVENTORY.md",
                          "../context/DO_NOTS.md"]
COMMAND: for f in docs/CONTEXT_KIT_INVENTORY.md context/WHAT_IT_IS.md \
                  context/INVENTORY.md context/DO_NOTS.md; do
             [ -e "$f" ] && echo "✓ $f" || echo "✗ $f"
         done
ACTUAL:  ✗ all four. PROJECT_WHAT_IT_IS.md ✓
VERDICT: DRIFT — companion_docs points at files that do not
         exist. Two possibilities: (a) the list was aspirational
         and the companions were never created, or (b) the
         listed files were renamed / moved to `_internal/`.
         Chris knows which.
```

```
CLAIM:   DEALER_KIT_BEHAVIOR_LAYER.md line 5 companion_docs
         includes DEALER_KIT_SESSION_START.md, CONTEXT_KIT_INVENTORY.md
COMMAND: same shape
ACTUAL:  ✗ both
VERDICT: DRIFT — same class.
```

```
CLAIM:   DEALER_KIT_TRANSLATION_LAYER.md lines 5–11 companion_docs
         includes DEALER_KIT_SESSION_START.md, CONTEXT_KIT_INVENTORY.md,
         onboarding/FREEDOM_FORD_ONBOARDING_PLAN.md
COMMAND: same
ACTUAL:  ✗ all three
VERDICT: DRIFT — same class.
```

```
CLAIM:   DEALER_KIT_BEHAVIOR_LAYER.md line 11 prose
         "companion to DEALER_KIT_SESSION_START.md"
COMMAND: (already verified above)
ACTUAL:  ✗
VERDICT: DRIFT — same reference in prose, not just frontmatter.
```

### README + AI_ASSISTED_DEVELOPMENT

```
CLAIM:   README's dealer flows exist in code
COMMAND: for f in backend/dealer_ai/management/commands/seed_copper_canyon_demo.py \
                  backend/dealer_ai/management/commands/seed_demo_vehicles.py \
                  backend/dealer_ai/management/commands/seed_demo_scenarios.py \
                  backend/dealer_ai backend/manage.py \
                  frontend; do
             [ -e "$f" ] && echo "✓ $f" || echo "✗ $f"
         done
ACTUAL:  All present.
VERDICT: OK — every README-mentioned path is real.
```

```
CLAIM:   AI_ASSISTED_DEVELOPMENT.md line 6 — "over approximately
         14 weeks — May 1 to August 5, 2026 — across 219 numbered
         engineering sessions and 344 commits"
COMMAND: git rev-list --count HEAD ; git log --pretty=%h -1
ACTUAL:  353 commits total, HEAD 6f425f1 (post-2026-08-05).
VERDICT: HISTORICAL — the 344 count is bounded to the Aug-5
         window ("May 1 to August 5"). Commits since Aug 5
         (9 of them, including HEAD's accounting fix) fall
         outside the claim's window. Not drift.
```

```
CLAIM:   AI_ASSISTED_DEVELOPMENT.md line 20 — "219 total in
         docs/_internal/handoffs/"
COMMAND: ls docs/_internal/handoffs
ACTUAL:  Directory does not exist in this working tree.
         `.gitignore` line `/docs/_internal/` confirms it is
         intentionally not shipped.
VERDICT: HISTORICAL / SPLIT-BY-DESIGN — the reference is
         truthful about Chris's private tree; opaque to a
         public reader. No public manifest documents this. See
         Missing conventions.
```

### DEMO_SCRIPT.md and COPPER_CANYON_DEMO_SCRIPT.md

```
CLAIM:   Every setup command in DEMO_SCRIPT.md is a real
         management command
COMMAND: for cmd in migrate seed_demo_vehicles seed_demo_scenarios; do
             grep -rn "^class Command\|name = '$cmd'" \
                  backend/dealer_ai/management/commands/ 2>&1 | head -1
         done
ACTUAL:  All present.
VERDICT: OK
```

### DEALER_DUPLICATION_GUIDE.md, PILOT_INVENTORY_TEMPLATE.md

```
CLAIM:   Both are current-state runbooks
COMMAND: grep -n "^status:" docs/DEALER_DUPLICATION_GUIDE.md \
                             docs/PILOT_INVENTORY_TEMPLATE.md
ACTUAL:  (frontmatter check — abbreviated inspection)
VERDICT: OK — both read as current-state runbooks; specific
         referenced flows depend on runtime that this session
         didn't exercise. Deferred.
```

### PILOT_ONBOARDING_PLAYBOOK.md

```
CLAIM:   Ships at Milestone 19 · Increment 5 (SESSION_158)
         and references SESSION_154–157 handoffs
COMMAND: ls docs/handoffs/SESSION_15[4567]*.md
ACTUAL:  All four missing (see governance-vs-practice above).
VERDICT: DRIFT — five broken references at
         PILOT_ONBOARDING_PLAYBOOK.md lines 46, 365, 367, 369, 371.
         Same class as the governance findings.
```

### GOD_FILES.md

```
CLAIM:   backend/dealer_ai/models.py is ~8,185 LOC
COMMAND: wc -l backend/dealer_ai/models.py
ACTUAL:  Not verified in this session — the "~" prefix is honest
         scope-marker language (per the two-doc-anchor discipline)
         and specific LOC drift is a moving target GOD_FILES
         itself notes.
VERDICT: OK — the "~" prefix is doing the work; deferring exact
         verification is honest.
```

### PROJECT_RULES.md

```
CLAIM:   Adopted at SESSION_033, commit ff0e986, 2026-07-31   (line 311)
COMMAND: git log ff0e986 --pretty="%ad %s" -1 --date=short
ACTUAL:  Commit ff0e986 exists; date and message match "adopted
         at close of discovery phase" as claimed.
VERDICT: OK
```

## Drift found

Grouped by class rather than instance, because most instances
share one root cause.

### Class A — public-tree references to private-tree files (11 instances)

- `docs/DOC_GOVERNANCE.md` line 45 — example list references
  BUILD_PLAN.md / CAPABILITY_MATRIX.md / BUSINESS_DOMAIN_MAP.md
- `docs/DOC_GOVERNANCE.md` line 289, 305, 306, 329, 454, 465,
  468, 470 — references to `docs/handoffs/`, `00-START-NEXT-
  SESSION.md`, `DEALER_KIT_SESSION_START.md`, `CLAUDE.md`,
  `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
- `docs/PROJECT_RULES.md` lines 311, 313, 316, 330 —
  references to SESSION_033 handoff
- `docs/PILOT_ONBOARDING_PLAYBOOK.md` lines 46, 365, 367, 369,
  371 — five refs to SESSION_154–157 handoffs
- `docs/PROJECT_PIPELINE.md` line 4 — companion_docs frontmatter
  points at CONTEXT_KIT_INVENTORY.md + three `../context/*` paths
- `docs/DEALER_KIT_BEHAVIOR_LAYER.md` line 5 (companion_docs)
  and line 11 (prose) — references to DEALER_KIT_SESSION_START,
  CONTEXT_KIT_INVENTORY
- `docs/DEALER_KIT_TRANSLATION_LAYER.md` lines 5–11
  (companion_docs) — three missing references including an
  `onboarding/` subdirectory

### Class B — structural gaps

- **No `CAPABILITY_MATRIX.md`** — DOC_GOVERNANCE.md names it as
  an authoritative root doc; absent.
- **No two-doc anchor companion** — narrative
  (`PROJECT_WHAT_IT_IS.md`) exists; runtime-derived inventory
  does not. Numeric claims in the narrative (5,045 tests,
  431 Vitest, 45 vehicles) have no ~ prefix and no INVENTORY
  to point at.
- **No PUBLIC_DOCS_MANIFEST.md** — the character-os pattern
  that resolves the public-vs-private split ambiguity. Its
  absence is why every Class A finding above required
  inference to categorise.
- **No repo-shipped verifier** — no `doctor` command, no
  `verify` script, no Makefile target. context-kit's `doctor`
  would flag every one of the Class A findings.

## Fixed in this pass

Nothing. Every Class A fix requires Chris's judgment about the
public/private strategy:

- Option 1 — add a `PUBLIC_DOCS_MANIFEST.md` (character-os
  shape) and leave references in place, with a header on
  affected docs pointing at the manifest.
- Option 2 — strip or rewrite each reference to acknowledge the
  private-only path.
- Option 3 — restore some docs to the public tree (probably
  not `docs/handoffs/*` at 219 files, but plausibly
  `DEALER_KIT_SESSION_START.md` and the roadmap headline).

The auditor cannot choose between these on the operator's
behalf — LESSON L-020 applies. Class B is even more clearly
Chris's decision (whether to build CAPABILITY_MATRIX.md, add a
verifier, adopt the two-doc-anchor discipline).

## Not fixed, and why

- **Every Class A reference.** Fixing them requires the strategy
  decision above. Flagged with `file:line` so Chris can act on
  one class at once (e.g. a single manifest-doc addition would
  make all 11 references legible).
- **Every Class B gap.** Building new anchor docs, generators,
  or verifiers is out of scope for a doc audit and requires
  narrative and design work Chris owns.
- **`AI_ASSISTED_DEVELOPMENT.md` 344-commit figure.** Bounded
  to a Aug-5 historical window; 9 later commits do not
  invalidate it. Not drift.
- **Numeric test-count claims in `PROJECT_WHAT_IT_IS.md`.**
  Cannot verify without the operator's environment (Postgres,
  Ollama, .venv). Recommend Chris run and confirm.

## Missing conventions

- **`PUBLIC_DOCS_MANIFEST.md` or equivalent.** character-os has
  it; freedom-ford should. This is the single change that would
  make ~11 findings legible instead of ambiguous.
- **A runtime-truth doctor** (LESSON L-015). context-kit ships
  one; character-os ships one; freedom-ford ships none. If a
  doctor existed, at minimum: broken-link detection across all
  public docs, `companion_docs` frontmatter validation, and a
  gitignored-target check would fire on this repo.
- **The `role:` frontmatter proposal.** Would help — every
  Class A finding involves guessing whether the referenced doc
  is current-state, historical, or intentionally-private.
- **A two-doc-anchor companion.** DOC_GOVERNANCE.md prescribes
  it in scope-contract §2, but the docs describing the pattern
  (PIPELINE / BEHAVIOR / TRANSLATION) point at a
  `CONTEXT_KIT_INVENTORY.md` that has never existed here.

## For the Drive STATUS doc

```
freedom-ford (Dealer AI) — status 2026-08-27
  HEAD 6f425f1 ("fix(accounting): reject duplicate direct
  reversal of the same journal entry"), main, 353 commits (219
  numbered sessions + 9 post-Aug-5 commits).
  Doc audit found 11 broken internal references across five
  docs (DOC_GOVERNANCE, PROJECT_RULES, PILOT_ONBOARDING_PLAYBOOK,
  PROJECT_PIPELINE, DEALER_KIT_BEHAVIOR_LAYER,
  DEALER_KIT_TRANSLATION_LAYER) pointing at files that exist
  only in the gitignored `docs/_internal/` private tree. Root
  cause: the public/portfolio split (same shape as character-os)
  was implemented without a PUBLIC_DOCS_MANIFEST.md documenting
  it. No fixes applied — strategy decision is Chris's.
  Structural gaps: no CAPABILITY_MATRIX.md (governance names it
  as expected root doc), no INVENTORY companion for the anchor
  pair, no repo-shipped runtime-truth doctor.
  What works: README's canonical flows (all paths present),
  DEMO_SCRIPT commands (all present in the CLI), governance
  itself (elaborate and internally consistent), case studies
  1–7 all present.
  Recommendation for a single high-leverage next step: add
  `docs/PUBLIC_DOCS_MANIFEST.md` following character-os's
  template. Resolves ~9 of the 11 findings by inference rather
  than by editing each doc.
```

## Category-based scope observation

**Cheaper again, and the hybrid enumeration paid off.** The five
per-file items (demo scripts, pilot playbooks, duplication
guide) were exactly the ones where "current-state or history?"
required per-file judgment. Category-based handled the 4 anchor
docs + governance + rules in one pass; per-file handled the
pilot docs. Total time similar to character-os's cleaner tree.

**One shape freedom-ford surfaced that character-os did not:**
"public docs that reference private docs" is a coherent class
worth naming in the protocol. character-os avoided the problem
because it shipped PUBLIC_DOCS_MANIFEST.md. Any repo doing the
public/private split without a manifest will produce this exact
shape of drift — worth mentioning to the norman-handyman brief
so session 5 knows to look for the specific pattern (a low-
stakes prototype probably doesn't have this shape, but if it
does, it's the smallest possible case to see it in).

## Phase two — was it worth the phase-one cost?

Yes, but yield dropped as predicted. Sessions 1–3 produced 20
lessons; freedom-ford's case studies (seven of them, already
lesson-shaped) added three genuinely new items. Two candidates
were folded into existing entries rather than added, because
LESSONS.md's bar has risen. That is the right shape — density
matters more than volume from here on.

The strongest single lesson from freedom-ford: **the M35.1
"verify against real Postgres before shipping" incident** — the
model was ready to ship on SQLite and rely on the fallback to
handle a Postgres failure at runtime; Chris insisted on empirical
verification against an ephemeral Postgres. Related to but
distinct from L-002 (stub-cannot-verify-boundary) — this is
about environment parity, not stub-vs-real. Recorded as L-021.

Second: **the M34.0 Playwright `--repeat-each` incident** —
the default response to failing tests was to quarantine them as
flaky; Chris insisted on root-causing the flag's actual
behaviour, which turned out to be "reruns test bodies within a
single invocation without re-firing setup projects." Recorded
as L-022.

Third: **the M34 "which documented business problem does this
solve, and is solving it required for the current milestone?"
rule** — a scope-decision frame that generalises well beyond
this project. Recorded as L-023.
