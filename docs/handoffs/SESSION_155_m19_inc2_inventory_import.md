---
title: "SESSION_155 handoff — Milestone 19 · Increment 2 (M19.2 — Pilot inventory import)"
status: historical
type: handoff
date: 2026-08-02
session: 155
milestone: 19
milestone_status: in-progress
milestone_name: "Founding Dealer Pilot Onboarding"
increment: 2
increment_status: shipped
---

# SESSION_155 — Milestone 19 · Increment 2 (M19.2 — Pilot inventory import)

## What shipped

Single backend increment per
`MILESTONE_19_PLANNING.md` §7 M19.2.
Full body for `import_pilot_inventory`
replacing the M19.1 stub +
`docs/PILOT_INVENTORY_TEMPLATE.md`
schema reference doc + 32 focused
tests.

**Two §0.a M19.2 implementation-time
decisions recorded** (do not count
against planning-time streak per M10
§9), both surfaced at M19.2 open and
grounded in the discovered M6.3
substrate:

### §0.a M19.2 decision 1 — CSV column set

**Decision.** Reuse the M6.3
`services/inventory_import.py::CSV_FIELDS`
21-column vocab verbatim. No fork.
`import_pilot_inventory` delegates
row parsing + persistence to
`services.inventory_import.import_rows`.

**Why the session-start opener's
three options were overwritten.** All
three sketched options
("mirror M18.2 archetype",
"narrower starter set", "archetype-
parameterized") pre-supposed authoring
a new column set. The discovery
finding at M19.2 open — the M6.3
substrate (411 lines) is a shipping,
battle-tested implementation with
body-style + condition aliases,
`_parse_features` (JSON/pipe/semicolon/
comma), UTF-8-BOM tolerance,
`_parse_decimal` (strips `$` and
commas), multi-tenant scope, and
VehicleStage bootstrap — made "reuse
verbatim" the correct architectural
move. Aligns with §7 M19.2's explicit
"extend the M6.3 substrate as needed
(additive; no fork)" directive.

### §0.a M19.2 decision 2 — pilot-import policy overlay

**Decision.** `import_pilot_inventory`
is a **thin wrapper** with three
pilot-specific overrides on the M6.3
substrate:

1. Belt-and-suspenders
   `assert dealership.is_pilot` at
   top + `NonPilotImportError`
   domain guard (mirrors M19.1's
   `NonPilotTerminationError`
   posture).
2. `mark_missing_unavailable=False`
   — pilots build inventory over
   time; a partial-CSV re-upload
   must NOT mark earlier vehicles
   unavailable. (M6.3's default is
   `True` for the franchise scraper
   case.)
3. Stable
   `source="pilot-inventory-import"`
   label so pilot rows are
   isolatable from franchise-
   scraper rows in operator
   queries.

Partial-success semantics inherited
from M6.3: accepted rows commit;
rejected rows surface with per-row
reason strings in
`PilotInventoryImportResult.rejected_rows`.

Re-import semantics inherited from
M6.3: a re-uploaded stock number
matching an existing Vehicle
**updates** the row (rather than
rejecting). The dealer can correct a
value + re-upload. The
session-start opener's "reject on
collision" test bullet was wrong;
the shipped behavior + test reflects
the M6.3 inheritance.

## Delivered

**New domain error**
`services/pilot_onboarding/errors.py::NonPilotImportError`
(RuntimeError, 500 mapping) mirroring
`NonPilotTerminationError`.

**Full body for**
`services/pilot_onboarding/inventory_import.py::import_pilot_inventory`
(replaces M19.1 stub):

- Signature preserved from M19.1:
  `import_pilot_inventory(*,
  dealership, csv_source, actor=None)
  -> PilotInventoryImportResult`.
- Accepts `str`, `Path`, or file-
  like `csv_source` (tests use
  `io.StringIO`; the M19.3 endpoint
  will pass an `UploadedFile`).
- New helper `_read_csv_rows`
  yields `(line_number, raw_dict)`
  tuples with UTF-8-BOM tolerance
  on filesystem paths.
- `PILOT_IMPORT_SOURCE =
  "pilot-inventory-import"` module
  constant.
- Structured `INFO` log line on
  every import (accepted count,
  rejected count, created/updated/
  unchanged breakdown from the
  M6.3 substrate summary).

**Package `__init__.py`** exports
extended with `NonPilotImportError` +
`PILOT_IMPORT_SOURCE` (19 total
public symbols; up from 18 at M19.1).

**New doc**
`docs/PILOT_INVENTORY_TEMPLATE.md`
— authoritative field-mapping
reference. Documents the shipping
M6.3 column vocab as the pilot import
schema. Covers required vs.
recommended vs. optional columns,
type notes, alias tables, and the
example CSV. Links to
`services/inventory_import.py::CSV_FIELDS`
as the source of truth.

**32 focused tests** in new
`tests/test_m192_pilot_inventory_import.py`:

- Constant + result-shape contracts
  (3): `PilotImportSourceConstantTests`
  (1), `PilotInventoryImportResultTests`
  (2 — defaults + frozen).
- Belt-and-suspenders guard (4):
  `BeltAndSuspendersGuardTests` —
  real dealership raises + demo
  raises + terminated pilot raises
  + `NonPilotImportError` is
  `RuntimeError`.
- Happy paths (8): `HappyPathTests`
  — StringIO input; source label;
  dealership FK; price/year parse;
  frontline stage bootstrap
  inherited; filesystem path
  input; missing file raises
  `FileNotFoundError`; empty CSV
  returns empty result.
- Rejected rows (6):
  `RejectedRowsTests` — missing
  year + missing model + zero
  price + missing stock/vin +
  partial success (2 accepted, 1
  rejected across 3 rows) +
  rejected row preserves raw dict
  for M19.4 operator surface.
- CSV edge cases (6):
  `CsvEdgeCaseTests` — UTF-8 BOM
  on file path; body_style alias
  (pickup → truck); condition
  alias (pre-owned → used);
  currency-formatted price
  (`$18,995` → 18995); default
  values on blank optional
  columns (Ford / Gasoline / suv
  / used); extra columns ignored.
- Re-import (2): `ReimportTests`
  — re-import updates existing
  stock number (M6.3 semantics);
  partial re-upload leaves
  earlier rows `is_available=True`.
- Zero-drift assertions (3):
  `M192TenancyCarrierTests` (>=52
  unchanged), `M192PermissionClassZeroDriftTests`
  (exact-set equality — streak
  now sixteen consecutive
  milestones M10 → M19.2),
  `M192EndpointCountTests` (>=108
  unchanged).

## Baseline delta

- **Backend:** 4,597 → **4,628
  pass**, 1 skipped, 0 fail.
  **+32 new tests − 1 retired
  M19.1 stub test = +31 net, 0
  regressions.** Exceeded 20-25
  planning target by 7 due to
  the edge-case coverage
  inherited from M6.3 (BOM +
  aliases + currency formatting).
  The retired M19.1 test
  (``PilotInventoryImportStubTests::test_stub_raises_not_implemented``)
  encoded the deliberately-
  temporary M19.1 stub behavior;
  M19.2 shipped the real body
  so the stub-behavior assertion
  is obsolete. The M19.1
  dataclass-shape assertion in
  the same class is preserved
  (renamed
  ``PilotInventoryImportResultShapeTests``).
- Migrations `0043-0048`
  (unchanged — M19.2 is pure
  service work).
- Tenancy carriers **52**
  (unchanged — M19.2 adds no
  tenant-scoped models).
- DRF admin surface **108**
  (unchanged — 4 pilot endpoints
  land at M19.3).
- Frontend operator routes **20**
  (unchanged — M19.4 extends
  existing admin route in place).
- Permission classes **7 actual**
  — **zero-drift streak now
  sixteen consecutive milestones**
  (M10 → M19.2).
- Celery-beat task families **10**
  (unchanged).
- Frontend Vitest **140**
  (unchanged — no frontend at
  M19.2).

## Streak update

**85 planning-time as-recommended
M5.1 → M19.0** (unchanged — M19.2 is
implementation-time work per M10 §9).
**Two §0.a M19.2 implementation-time
decisions recorded** (CSV vocab
reuse + pilot policy overlay). Both
defended in this handoff and grounded
in the discovered M6.3 shipping
substrate.

## What's next: SESSION_156 M19.3 DRF endpoints

Per `MILESTONE_19_PLANNING.md` §7
M19.3:

- New module
  `dealer_ai/views_pilot_onboarding.py`
  with four endpoint handlers:
  - `POST admin/pilots/create/` —
    calls `create_pilot_dealership`.
  - `GET admin/pilots/` —
    calls `list_pilot_dealerships`.
  - `POST admin/pilots/<slug>/checklist/advance/`
    — calls `advance_step`.
  - `POST admin/pilots/<slug>/terminate/`
    — calls `terminate_pilot`.
- Optional 5th endpoint depending
  on §0.a M19.3 micro-decision:
  `POST admin/pilots/<slug>/inventory/import/`
  wrapping `import_pilot_inventory`.
  Recommendation: yes, ship at
  M19.3; keeps the pilot admin
  surface fully self-contained
  before M19.4 frontend consumes.
- Domain-error → HTTP mapping per
  the errors module contracts.
- No new permission classes —
  reuse
  `IsDealerOwnerAtActiveDealership`
  scoped to Chris's owner role at
  the DealerKit tenant (dealer-
  owner-of-the-platform pattern).
- Focused tests (~25-35 target)
  in `tests/test_m193_pilot_endpoints.py`.

**Backend baseline target at M19.3
close:** 4,628 → ~4,653-4,663 pass
(+25-35 tests). Admin surface
108 → 112 (or 113 if the import
endpoint ships).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_154_m19_inc1_backend_substrate.md`
7. `docs/handoffs/SESSION_153_m19_inc0_planning.md`
8. `docs/PILOT_INVENTORY_TEMPLATE.md`
   (freshly shipped)
9. `backend/dealer_ai/services/pilot_onboarding/inventory_import.py`
   (M19.2 wrapper)
10. `backend/dealer_ai/services/inventory_import.py`
    (M6.3 substrate — reused
    verbatim per §0.a decision 1)
11. `backend/dealer_ai/tests/test_m192_pilot_inventory_import.py`
    (behavior contract)
