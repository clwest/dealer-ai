// Milestone 3 · Increment 7 — create-report form.
//
// Shown when the vehicle has no report yet (or when the operator
// deliberately authors a new inspection after completing an earlier
// one). Requires the three research-backed RECON §2.4 fields:
// inspector_name, inspected_at, mileage_at_inspection. Notes is
// optional.
//
// Server owns: dealership (from request), authored_by (from
// request.user), status (always draft at create), completed_at
// (NULL at create). Client cannot spoof — serializer whitelist
// silently ignores those fields.

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  createConditionReport,
  type ConditionReport,
} from "@/lib/api";

interface Props {
  stock: string;
  onCreated: (report: ConditionReport) => void;
}

function _localIsoNow(): string {
  // <input type="datetime-local"> expects YYYY-MM-DDTHH:MM.
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(
    d.getDate(),
  )}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) return "Invalid input (check required fields).";
    if (err.status === 404) return "Vehicle not found.";
    return `Server returned ${err.status}.`;
  }
  return "Request failed.";
}

export function CreateReportForm({ stock, onCreated }: Props) {
  const [inspectorName, setInspectorName] = useState("");
  const [inspectedAt, setInspectedAt] = useState(_localIsoNow());
  const [mileage, setMileage] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (inspectorName.trim() === "") {
      setError("Inspector name is required.");
      return;
    }
    const mileageInt = parseInt(mileage, 10);
    if (Number.isNaN(mileageInt) || mileageInt < 0) {
      setError("Mileage must be a non-negative integer.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      // Convert datetime-local (local time, no tz suffix) to an
      // ISO string the backend can parse. Appending ':00' seconds
      // + calling toISOString() yields a UTC-normalized value.
      const isoWithSeconds = `${inspectedAt}:00`;
      const asDate = new Date(isoWithSeconds);
      const inspectedAtIso = asDate.toISOString();
      const { report } = await createConditionReport(stock, {
        inspector_name: inspectorName,
        inspected_at: inspectedAtIso,
        mileage_at_inspection: mileageInt,
        notes,
      });
      onCreated(report);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="text-base font-semibold text-foreground">
        Author a new condition report
      </h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Starts as a draft. You can add findings and photos, then
        complete the report — completion is one-way.
      </p>
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Inspector name
          <Input
            value={inspectorName}
            onChange={(e) => setInspectorName(e.target.value)}
            placeholder="Person who physically inspected the vehicle"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Inspection date &amp; time
          <Input
            type="datetime-local"
            value={inspectedAt}
            onChange={(e) => setInspectedAt(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Mileage at inspection
          <Input
            type="number"
            inputMode="numeric"
            min={0}
            value={mileage}
            onChange={(e) => setMileage(e.target.value)}
            placeholder="e.g. 42000"
          />
        </label>
      </div>
      <label className="mt-3 flex flex-col gap-1 text-xs font-medium">
        Notes
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          placeholder="Optional — e.g. 'arrival inspection vs Manheim condition report.'"
        />
      </label>
      {error ? (
        <p role="alert" className="mt-2 text-xs text-rose-700">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex items-center gap-2">
        <Button type="button" onClick={submit} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
          ) : null}
          Create draft report
        </Button>
      </div>
    </div>
  );
}
