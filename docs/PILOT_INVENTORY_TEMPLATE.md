---
title: Pilot inventory CSV template
status: active
type: reference
date: 2026-08-02
milestone_shipped: 19
increment_shipped: 2
authoritative_schema: services/inventory_import.py::CSV_FIELDS
---

# Pilot inventory CSV template

Authoritative schema for the CSV a founding pilot dealer uploads
during pilot onboarding. Shipped at **Milestone 19 · Increment 2
(SESSION_155)** per `MILESTONE_19_PLANNING.md` §7 M19.2.

## What this doc is

A **field-mapping reference** for the pilot inventory import path.
The columns documented here are the columns
`backend/dealer_ai/services/pilot_onboarding/inventory_import.py::import_pilot_inventory`
consumes. That wrapper delegates row parsing to the M6.3 substrate
at `backend/dealer_ai/services/inventory_import.py`; the column
vocab this doc describes is the same 21-column vocab defined in
`CSV_FIELDS` there.

**No fork.** The pilot import and the franchise scraper import share
one shipping schema. Per §0.a M19.2 decision 1 (SESSION_155 open),
we reuse the M6.3 vocab verbatim rather than authoring a new one.

## What the wrapper does differently

Per §0.a M19.2 decision 2, `import_pilot_inventory` overlays three
pilot-specific policies on the M6.3 substrate:

1. **Belt-and-suspenders `is_pilot` guard.** Raises
   `NonPilotImportError` (500) if called against a demo or live
   dealership. The M19.3 endpoint layer surfaces this as an internal
   server error — reaching that state means a caller routed to the
   wrong verb.
2. **`mark_missing_unavailable=False`.** A pilot dealer builds
   inventory over time; a partial-CSV re-upload must NOT mark
   earlier vehicles unavailable. (The M6.3 default is `True` for
   the franchise scraper case, where the scraper re-scrapes every
   run and stale rows should sweep.)
3. **`Vehicle.source="pilot-inventory-import"`.** Stable label
   isolates pilot-imported rows from franchise-scraper rows in
   operator surfaces + queries.

Partial-success semantics inherited from M6.3: accepted rows commit;
rejected rows surface with a per-row reason string in
`PilotInventoryImportResult.rejected_rows`. The operator fixes the
rejected rows and re-uploads without losing the good rows.

Re-import semantics inherited from M6.3: a re-uploaded stock number
matching an existing Vehicle **updates** the existing row (not
rejects). The dealer can correct a value and re-upload; the update
persists with `is_available=True` restored if it was previously
swept.

## Column reference

Header row is line 1. Data rows begin at line 2. The parser is
tolerant of a UTF-8 BOM (common in Excel-saved CSVs).

**Required per row:**

| column | type | notes |
| --- | --- | --- |
| `year` | int | 1980–2100 inclusive. Rejects out-of-range. |
| `model` | string | Non-empty. |
| `price` | decimal | > 0. Strips `$` and commas (`$18,995` → 18995). |

**One of `stock_number` OR `vin` per row:**

| column | type | notes |
| --- | --- | --- |
| `stock_number` | string | Unique per row. If blank, wrapper synthesizes `VIN-<vin>`. |
| `vin` | string | Matched against existing rows for re-import updates. |

**Recommended (defaults documented):**

| column | type | default | notes |
| --- | --- | --- | --- |
| `make` | string | `Ford` | Independent pilots typically override to their carried makes. |
| `trim` | string | `""` | |
| `body_style` | string | `suv` | Aliases: `pickup→truck`, `crossover→suv`, `sedan→car`, `coupe→car`, `hatch→car`, `hatchback→car`, `electric→ev`, `minivan→van`. |
| `condition` | string | `used` | Aliases: `pre-owned→used`, `preowned→used`, `second-hand→used`, `cpo→certified`, `certified pre-owned→certified`. |
| `mileage` | int | `0` | Negative values clamp to 0. |
| `fuel_type` | string | `Gasoline` | Free-form. |

**Optional (blank tolerated):**

| column | type | notes |
| --- | --- | --- |
| `drivetrain` | string | e.g. `AWD`, `FWD`, `4WD`. |
| `transmission` | string | e.g. `Automatic`, `Manual`. |
| `engine` | string | Free-form. |
| `exterior_color` | string | |
| `interior_color` | string | |
| `msrp` | decimal | Same parser as `price`. |
| `image_url` | URL | |
| `url` | URL | Vehicle-detail landing page. |
| `description` | string | |
| `features` | list | Comma-, pipe-, or semicolon-separated. JSON array literal also accepted (`["Tow","Sync 4"]`). |

Any column not in this list is ignored (not rejected) — a dealer
can leave their DMS export columns in place without preprocessing.

## Example CSV

```csv
stock_number,vin,year,make,model,trim,condition,price,mileage,body_style,drivetrain,fuel_type,exterior_color
P-001,1FTFW1E52NKD12345,2019,Ford,F-150,XLT,used,32995,48120,truck,4WD,Gasoline,Oxford White
P-002,1C4RJFAG5MC123456,2020,Jeep,Grand Cherokee,Limited,used,28500,52340,suv,4WD,Gasoline,Diamond Black
P-003,3VW2K7AJ5EM123456,2018,Volkswagen,Jetta,SE,used,14200,71200,car,FWD,Gasoline,Reflex Silver
```

## What happens after upload

1. Wrapper checks `dealership.is_pilot`. Raises
   `NonPilotImportError` if not.
2. Wrapper reads the source (str/Path filesystem path OR file-like
   object).
3. Delegates to `services.inventory_import.import_rows` inside a
   Django transaction with `source="pilot-inventory-import"`,
   `mark_missing_unavailable=False`, and the pilot dealership pinned.
4. For each valid row: creates a new Vehicle OR updates an existing
   one keyed by `stock_number` (or by `vin` fallback). Seeds a
   `frontline` VehicleStage on new creates (M5.5 lifecycle
   contract inherited from M6.3).
5. Returns a frozen `PilotInventoryImportResult` with the accepted
   stock numbers + rejected rows for the operator surface.

## What we still don't do at M19.2

- ❌ No CSV → JSON conversion for the M19.3 endpoint response (the
  endpoint projects `PilotInventoryImportResult` at the boundary).
- ❌ No sample-file download endpoint (M19.4 admin surface may
  ship one; not committed).
- ❌ No pandas / openpyxl dependency. CSV only. Excel exports save-
  as-CSV before upload.
- ❌ No cross-tenant duplicate detection (M6.3 does within-tenant
  matching by stock number; cross-tenant is by-design not a
  constraint).

## References

- `MILESTONE_19_PLANNING.md` §7 M19.2 — the shipped scope.
- `docs/handoffs/SESSION_155_m19_inc2_inventory_import.md` — the
  session handoff (includes §0.a M19.2 decisions).
- `backend/dealer_ai/services/inventory_import.py::CSV_FIELDS` —
  the authoritative field list this doc describes.
- `backend/dealer_ai/services/pilot_onboarding/inventory_import.py`
  — the pilot wrapper.
- `backend/dealer_ai/tests/test_m192_pilot_inventory_import.py` —
  behavior contract.
