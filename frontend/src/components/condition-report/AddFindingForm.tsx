// Milestone 3 · Increment 7 — inline add-finding form.
//
// Belongs to the draft-only edit affordances. Renders inside the
// page's findings section; on successful POST, calls the page's
// ``onCreated`` handler which appends the new finding to state and
// re-groups.

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/authFetch";
import {
  CONDITION_CATEGORY_CHOICES,
  CONDITION_SEVERITY_CHOICES,
  createConditionFinding,
  type ConditionFinding,
} from "@/lib/api";

interface Props {
  stock: string;
  reportId: number;
  onCreated: (finding: ConditionFinding) => void;
}

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Report is complete — new findings cannot be added.";
    if (err.status === 400) return "Invalid input (check category / severity / description).";
    if (err.status === 404) return "Report not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Request failed.";
}

export function AddFindingForm({ stock, reportId, onCreated }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [category, setCategory] = useState(CONDITION_CATEGORY_CHOICES[0].value);
  const [severity, setSeverity] = useState("advisory");
  const [description, setDescription] = useState("");
  const [estimatedCost, setEstimatedCost] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCategory(CONDITION_CATEGORY_CHOICES[0].value);
    setSeverity("advisory");
    setDescription("");
    setEstimatedCost("");
    setNotes("");
    setError(null);
  }

  async function submit() {
    if (description.trim() === "") {
      setError("Description is required.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const { finding } = await createConditionFinding(stock, reportId, {
        category,
        severity,
        description,
        estimated_cost: estimatedCost.trim() === "" ? null : estimatedCost,
        notes,
      });
      onCreated(finding);
      reset();
      setExpanded(false);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  if (!expanded) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={() => setExpanded(true)}
      >
        <Plus className="h-3.5 w-3.5" aria-hidden="true" />
        Add finding
      </Button>
    );
  }

  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/30 p-3">
      <h3 className="text-sm font-semibold text-foreground">
        Add finding
      </h3>
      <div className="mt-3 flex flex-col gap-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs font-medium">
            Category
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded border border-input bg-background px-2 py-1.5 text-sm"
            >
              {CONDITION_CATEGORY_CHOICES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Severity
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="rounded border border-input bg-background px-2 py-1.5 text-sm"
            >
              {CONDITION_SEVERITY_CHOICES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Description
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="What did the inspector observe?"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Estimated cost{" "}
          <span className="text-muted-foreground">
            (optional — documentation only, not part of vehicle investment)
          </span>
          <Input
            type="text"
            inputMode="decimal"
            placeholder="e.g. 165.00"
            value={estimatedCost}
            onChange={(e) => setEstimatedCost(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Notes
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Optional context."
          />
        </label>
        {error ? (
          <p role="alert" className="text-xs text-rose-700">
            {error}
          </p>
        ) : null}
        <div className="flex items-center gap-2">
          <Button
            type="button"
            size="sm"
            disabled={saving}
            onClick={submit}
          >
            {saving ? (
              <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : null}
            Add finding
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              reset();
              setExpanded(false);
            }}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
