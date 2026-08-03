// Milestone 25 · Increment 2 (SESSION_187) — record-test-drive form.
//
// Posts to POST /admin/test-drives/ via createTestDrive (M11.6
// wrapper). Field surface matches TestDriveCreateRequestSerializer
// in backend/dealer_ai/views_test_drives.py:58-78 — required
// vehicle_id + lead_id (lead_id passed by the parent modal);
// optional duration_minutes / route_notes / customer_reaction /
// objections_captured (comma-separated) / next_action. driven_at
// defaults server-side to timezone.now() when omitted per M11.2
// operator reality (drives are recorded post-drive, not scheduled
// ahead).
//
// Vehicle picker per MILESTONE_25_PLANNING.md §5.e:
//   - "Suggested" zone reads detail.interested_vehicles from the
//     parent modal (chat-origin leads pre-populate this; walk-in /
//     phone / referral / webhook leads land empty).
//   - "All inventory" zone lazy-loads via listAdminVehicles from
//     salesApi (added at M25.2 open — see §Empirical discovery in
//     the M25.2 handoff).
//   - Search field narrows the inventory list by
//     stock/year/make/model/trim substring.
//
// Modal-only per §5.d. No secondary launch point on
// DealerAiSalesTestDrives — that page stays read-only.

import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  createTestDrive,
  listAdminVehicles,
  type AdminVehicleRow,
  type TestDriveProjection,
} from "@/lib/salesApi";

export interface RecordTestDriveFormSuggestedVehicle {
  id: number;
  stock_number: string;
  display_name: string;
  price: string | number;
  image_url?: string;
}

export interface RecordTestDriveFormProps {
  leadId: number;
  /**
   * Vehicles already flagged on the lead (from LeadDetailResponse
   * `interested_vehicles`). Rendered as the "Suggested" zone at
   * the top of the picker.
   */
  suggestedVehicles?: RecordTestDriveFormSuggestedVehicle[];
  /**
   * Callback fired after a successful create. Parent (modal)
   * collapses the section + shows a success indicator.
   */
  onCreated: (drive: TestDriveProjection) => void;
  /**
   * Optional cancel handler — parent collapses the section
   * without submitting. Rendered as a "Cancel" secondary
   * button when provided.
   */
  onCancel?: () => void;
  /**
   * Injected for tests. Defaults to the shipped
   * `listAdminVehicles` wrapper.
   */
  loadInventory?: typeof listAdminVehicles;
  /**
   * Injected for tests. Defaults to the shipped
   * `createTestDrive` wrapper.
   */
  submit?: typeof createTestDrive;
}

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid test-drive fields. Check the picker + optional fields and try again.";
    }
    if (err.status === 404) {
      return "Lead or vehicle not found in your dealership.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to record the test drive.";
}

export function RecordTestDriveForm({
  leadId,
  suggestedVehicles = [],
  onCreated,
  onCancel,
  loadInventory = listAdminVehicles,
  submit = createTestDrive,
}: RecordTestDriveFormProps) {
  const [vehicleId, setVehicleId] = useState<number | null>(null);
  const [inventory, setInventory] = useState<AdminVehicleRow[]>([]);
  const [inventoryState, setInventoryState] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [search, setSearch] = useState("");
  const [durationMinutes, setDurationMinutes] = useState("");
  const [routeNotes, setRouteNotes] = useState("");
  const [customerReaction, setCustomerReaction] = useState("");
  const [objectionsRaw, setObjectionsRaw] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounced inventory fetch. Fires on mount + on search change.
  useEffect(() => {
    let cancelled = false;
    setInventoryState("loading");
    const timer = window.setTimeout(() => {
      loadInventory(search ? { search } : {})
        .then((res) => {
          if (cancelled) return;
          setInventory(res.results);
          setInventoryState("ready");
        })
        .catch(() => {
          if (cancelled) return;
          setInventoryState("error");
        });
    }, search ? 200 : 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [search, loadInventory]);

  function selectVehicle(id: number) {
    setVehicleId(id);
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (vehicleId == null) {
      setError("Pick a vehicle before recording the test drive.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const objections = objectionsRaw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const parsedDuration = durationMinutes.trim()
        ? Number(durationMinutes.trim())
        : null;
      const drive = await submit({
        lead_id: leadId,
        vehicle_id: vehicleId,
        duration_minutes:
          parsedDuration != null && Number.isFinite(parsedDuration)
            ? parsedDuration
            : null,
        route_notes: routeNotes.trim() || undefined,
        customer_reaction: customerReaction.trim() || undefined,
        objections_captured: objections.length ? objections : undefined,
        next_action: nextAction.trim() || undefined,
      });
      onCreated(drive);
      // Reset form so a follow-on drive on the same lead starts clean.
      setVehicleId(null);
      setDurationMinutes("");
      setRouteNotes("");
      setCustomerReaction("");
      setObjectionsRaw("");
      setNextAction("");
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  // Suggested vehicles filtered against the current search text so
  // the operator's search narrows both zones consistently.
  const needle = search.trim().toLowerCase();
  const suggestedFiltered = suggestedVehicles.filter((v) => {
    if (!needle) return true;
    return (
      v.display_name.toLowerCase().includes(needle) ||
      v.stock_number.toLowerCase().includes(needle)
    );
  });
  const suggestedIds = new Set(suggestedFiltered.map((v) => v.id));
  const inventoryFiltered = inventory.filter((v) => !suggestedIds.has(v.id));

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3"
      data-testid="record-test-drive-form"
    >
      <label className="flex flex-col gap-1 text-xs">
        Search inventory
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Stock #, year, make, model, or trim"
          data-testid="record-test-drive-search"
        />
      </label>

      <div className="max-h-64 overflow-y-auto rounded-md border border-slate-200 bg-white">
        {suggestedFiltered.length > 0 ? (
          <div data-testid="record-test-drive-suggested-zone">
            <div className="border-b border-slate-100 bg-slate-50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              Suggested for this lead
            </div>
            <ul>
              {suggestedFiltered.map((v) => (
                <li key={`sug-${v.id}`}>
                  <button
                    type="button"
                    onClick={() => selectVehicle(v.id)}
                    data-testid={`record-test-drive-vehicle-${v.id}`}
                    className={`flex w-full items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 text-left text-sm hover:bg-brand-mist/40 ${
                      vehicleId === v.id
                        ? "bg-brand-mist/60 font-semibold text-brand-ink"
                        : "text-slate-700"
                    }`}
                  >
                    <span>
                      {v.display_name}{" "}
                      <span className="text-xs text-slate-500">
                        · #{v.stock_number}
                      </span>
                    </span>
                    <span className="text-xs text-slate-500">${v.price}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div data-testid="record-test-drive-inventory-zone">
          <div className="border-b border-slate-100 bg-slate-50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
            All inventory
          </div>
          {inventoryState === "loading" ? (
            <p className="px-3 py-3 text-xs text-slate-500">Loading…</p>
          ) : null}
          {inventoryState === "error" ? (
            <p
              className="px-3 py-3 text-xs text-destructive"
              role="alert"
              data-testid="record-test-drive-inventory-error"
            >
              Failed to load inventory.
            </p>
          ) : null}
          {inventoryState === "ready" && inventoryFiltered.length === 0 ? (
            <p
              className="px-3 py-3 text-xs text-slate-500"
              data-testid="record-test-drive-inventory-empty"
            >
              No vehicles match.
            </p>
          ) : null}
          {inventoryState === "ready" && inventoryFiltered.length > 0 ? (
            <ul>
              {inventoryFiltered.map((v) => (
                <li key={`inv-${v.id}`}>
                  <button
                    type="button"
                    onClick={() => selectVehicle(v.id)}
                    data-testid={`record-test-drive-vehicle-${v.id}`}
                    className={`flex w-full items-center justify-between gap-2 border-b border-slate-100 px-3 py-2 text-left text-sm hover:bg-brand-mist/40 ${
                      vehicleId === v.id
                        ? "bg-brand-mist/60 font-semibold text-brand-ink"
                        : "text-slate-700"
                    }`}
                  >
                    <span>
                      {v.display_name}{" "}
                      <span className="text-xs text-slate-500">
                        · #{v.stock_number} · {v.condition}
                      </span>
                    </span>
                    <span className="text-xs text-slate-500">${v.price}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          Duration (minutes)
          <Input
            type="number"
            inputMode="numeric"
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
            placeholder="20"
            data-testid="record-test-drive-duration-minutes"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          Customer reaction
          <Input
            value={customerReaction}
            onChange={(e) => setCustomerReaction(e.target.value)}
            placeholder="Positive / hesitant / negative"
            data-testid="record-test-drive-customer-reaction"
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        Route notes
        <textarea
          value={routeNotes}
          onChange={(e) => setRouteNotes(e.target.value)}
          placeholder="Highway loop, city stop-and-go, etc."
          className="min-h-[48px] rounded-md border border-input bg-background px-3 py-2 text-sm"
          data-testid="record-test-drive-route-notes"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs">
        Objections (comma-separated)
        <Input
          value={objectionsRaw}
          onChange={(e) => setObjectionsRaw(e.target.value)}
          placeholder="price too high, want AWD, waiting for tax refund"
          data-testid="record-test-drive-objections"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs">
        Next action
        <Input
          value={nextAction}
          onChange={(e) => setNextAction(e.target.value)}
          placeholder="Follow up Tuesday with financing options"
          data-testid="record-test-drive-next-action"
        />
      </label>

      {error ? (
        <p
          className="text-xs text-destructive"
          role="alert"
          data-testid="record-test-drive-error"
        >
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2">
        {onCancel ? (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            data-testid="record-test-drive-cancel"
          >
            Cancel
          </Button>
        ) : null}
        <Button
          type="submit"
          disabled={submitting || vehicleId == null}
          data-testid="record-test-drive-submit"
        >
          {submitting ? "Recording…" : "Record test drive"}
        </Button>
      </div>
    </form>
  );
}
