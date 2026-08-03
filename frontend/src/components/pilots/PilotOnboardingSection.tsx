// Milestone 19 · Increment 4 (SESSION_157) — pilot onboarding admin surface.
//
// Per MILESTONE_19_PLANNING.md §7 M19.4 + §0.a M19.4 decision 2
// (user-confirmed at SESSION_157 open). Extends the existing
// `/dealer-ai-admin` route in place — sub-section inside DealerAdmin
// keeps operator route count at 20 and matches the M19.0 planning
// posture "M19.4 extends existing admin route in place."
//
// Wraps the five M19.3 + M19.4 endpoints
// (fetch/create/checklist/import/terminate). Sub-panels:
//
// - Pilot list (fetch on mount + on any mutation).
// - Create form (slug + name + owner_username).
// - Per-pilot detail: checklist stepper + CSV upload +
//   terminate confirmation.

import { useCallback, useEffect, useState } from "react";
import { Loader2, UploadCloud, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  advancePilotChecklistStep,
  createPilotDealership,
  fetchPilotDealerships,
  importPilotInventory,
  terminatePilotDealership,
  type PilotChecklistDTO,
  type PilotChecklistStepDTO,
  type PilotDealershipDTO,
  type PilotInventoryImportResultDTO,
  type PilotWithChecklistDTO,
} from "@/lib/api";
import { ApiError } from "@/lib/authFetch";

const STEP_LABELS: Record<string, string> = {
  dealership_created: "Dealership created",
  profile_configured: "Profile configured",
  owner_user_added: "Owner user added",
  staff_users_added: "Staff users added",
  inventory_imported: "Inventory imported",
  capabilities_enabled: "Capabilities enabled",
  readiness_confirmed: "Readiness confirmed",
};

export default function PilotOnboardingSection() {
  const [pilots, setPilots] = useState<PilotWithChecklistDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setGlobalError(null);
    try {
      const res = await fetchPilotDealerships();
      setPilots(res.pilots);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedPilot = pilots.find(
    (p) => p.dealership.slug === selectedSlug,
  );

  return (
    <Card data-testid="pilot-onboarding-section">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" /> Pilot onboarding
          </CardTitle>
          <CardDescription>
            Founding-dealer pilot conversion — create, advance, or
            terminate a pilot store.
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()}>
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Refresh"
          )}
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {globalError && (
          <div
            role="alert"
            data-testid="pilot-global-error"
            className="rounded border border-destructive/40 bg-destructive/10 p-2 text-sm text-destructive"
          >
            {globalError}
          </div>
        )}

        <PilotCreateForm onCreated={() => void load()} />

        <PilotList
          pilots={pilots}
          loading={loading}
          selectedSlug={selectedSlug}
          onSelect={setSelectedSlug}
        />

        {selectedPilot && selectedPilot.checklist && (
          <PilotDetailPanel
            pilot={selectedPilot.dealership}
            checklist={selectedPilot.checklist}
            onChanged={() => void load()}
          />
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Create form
// ---------------------------------------------------------------------------

function PilotCreateForm({ onCreated }: { onCreated: () => void }) {
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [ownerUsername, setOwnerUsername] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    slug.trim().length > 0 &&
    name.trim().length > 0 &&
    ownerUsername.trim().length > 0 &&
    !submitting;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createPilotDealership({
        slug: slug.trim(),
        name: name.trim(),
        owner_username: ownerUsername.trim(),
      });
      setSlug("");
      setName("");
      setOwnerUsername("");
      onCreated();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Slug is already taken by another dealership.");
      } else if (err instanceof ApiError && err.status === 400) {
        setError("Invalid input — check owner_username exists.");
      } else {
        setError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="pilot-create-form"
      className="space-y-2 rounded border p-3"
    >
      <h4 className="font-semibold">Create pilot</h4>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
        <Input
          aria-label="Slug"
          placeholder="acme-motors"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          data-testid="pilot-create-slug"
        />
        <Input
          aria-label="Name"
          placeholder="Acme Motors"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="pilot-create-name"
        />
        <Input
          aria-label="Owner username"
          placeholder="owner-username"
          value={ownerUsername}
          onChange={(e) => setOwnerUsername(e.target.value)}
          data-testid="pilot-create-owner"
        />
      </div>
      {error && (
        <div
          role="alert"
          data-testid="pilot-create-error"
          className="text-sm text-destructive"
        >
          {error}
        </div>
      )}
      <Button
        type="submit"
        disabled={!canSubmit}
        data-testid="pilot-create-submit"
      >
        {submitting ? "Creating…" : "Create pilot"}
      </Button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Pilot list
// ---------------------------------------------------------------------------

function PilotList({
  pilots,
  loading,
  selectedSlug,
  onSelect,
}: {
  pilots: PilotWithChecklistDTO[];
  loading: boolean;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}) {
  if (loading && pilots.length === 0) {
    return <div data-testid="pilot-list-loading">Loading pilots…</div>;
  }
  if (pilots.length === 0) {
    return (
      <div data-testid="pilot-list-empty" className="text-sm text-muted-foreground">
        No active pilots yet. Create one above.
      </div>
    );
  }
  return (
    <div className="space-y-1" data-testid="pilot-list">
      {pilots.map((entry) => {
        const d = entry.dealership;
        const isReady = entry.checklist?.is_ready ?? false;
        return (
          <button
            key={d.slug}
            type="button"
            data-testid={`pilot-row-${d.slug}`}
            className={`flex w-full items-center justify-between rounded border p-2 text-left hover:bg-muted ${
              selectedSlug === d.slug ? "border-primary" : ""
            }`}
            onClick={() => onSelect(d.slug)}
          >
            <div>
              <div className="font-medium">{d.name}</div>
              <div className="text-xs text-muted-foreground">{d.slug}</div>
            </div>
            <Badge variant={isReady ? "default" : "outline"}>
              {isReady ? "Ready" : "In progress"}
            </Badge>
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail panel — checklist stepper + CSV upload + terminate
// ---------------------------------------------------------------------------

function PilotDetailPanel({
  pilot,
  checklist,
  onChanged,
}: {
  pilot: PilotDealershipDTO;
  checklist: PilotChecklistDTO;
  onChanged: () => void;
}) {
  return (
    <div
      className="space-y-4 rounded border p-3"
      data-testid={`pilot-detail-${pilot.slug}`}
    >
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">
          {pilot.name}{" "}
          <span className="text-sm text-muted-foreground">
            ({pilot.slug})
          </span>
        </h4>
        <Badge variant={checklist.is_ready ? "default" : "outline"}>
          {checklist.is_ready ? "Ready" : "In progress"}
        </Badge>
      </div>

      <ChecklistStepper
        slug={pilot.slug}
        checklist={checklist}
        onAdvanced={onChanged}
      />

      <InventoryUploadPanel slug={pilot.slug} onImported={onChanged} />

      <TerminateForm slug={pilot.slug} onTerminated={onChanged} />
    </div>
  );
}

function ChecklistStepper({
  slug,
  checklist,
  onAdvanced,
}: {
  slug: string;
  checklist: PilotChecklistDTO;
  onAdvanced: () => void;
}) {
  const [advancing, setAdvancing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAdvance(step: PilotChecklistStepDTO) {
    setAdvancing(step.step_slug);
    setError(null);
    try {
      await advancePilotChecklistStep(slug, {
        step_slug: step.step_slug,
      });
      onAdvanced();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(
          "Cannot advance — prior steps incomplete or step already done.",
        );
      } else {
        setError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setAdvancing(null);
    }
  }

  return (
    <div className="space-y-1" data-testid="pilot-checklist">
      <h5 className="font-medium">Checklist</h5>
      {checklist.steps.map((step) => {
        const isComplete = step.completed_at !== null;
        return (
          <div
            key={step.step_slug}
            data-testid={`pilot-step-${step.step_slug}`}
            className="flex items-center justify-between rounded border p-2 text-sm"
          >
            <div>
              <span className={isComplete ? "line-through" : ""}>
                {STEP_LABELS[step.step_slug] ?? step.step_slug}
              </span>
              {isComplete && step.completed_at && (
                <span className="ml-2 text-xs text-muted-foreground">
                  {new Date(step.completed_at).toLocaleDateString()}
                </span>
              )}
            </div>
            {!isComplete && (
              <Button
                size="sm"
                variant="outline"
                disabled={advancing !== null}
                onClick={() => void handleAdvance(step)}
                data-testid={`pilot-advance-${step.step_slug}`}
              >
                {advancing === step.step_slug ? "Advancing…" : "Complete"}
              </Button>
            )}
          </div>
        );
      })}
      {error && (
        <div
          role="alert"
          data-testid="pilot-advance-error"
          className="text-sm text-destructive"
        >
          {error}
        </div>
      )}
    </div>
  );
}

function InventoryUploadPanel({
  slug,
  onImported,
}: {
  slug: string;
  onImported: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<PilotInventoryImportResultDTO | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = await importPilotInventory(slug, file);
      setResult(res.result);
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-2 rounded border p-2" data-testid="pilot-upload">
      <h5 className="font-medium">Inventory CSV upload</h5>
      <div className="flex items-center gap-2">
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          data-testid="pilot-upload-input"
          aria-label="CSV file"
        />
        <Button
          type="button"
          size="sm"
          disabled={!file || uploading}
          onClick={() => void handleUpload()}
          data-testid="pilot-upload-submit"
        >
          <UploadCloud className="mr-1 h-4 w-4" />
          {uploading ? "Uploading…" : "Upload"}
        </Button>
      </div>
      {error && (
        <div
          role="alert"
          data-testid="pilot-upload-error"
          className="text-sm text-destructive"
        >
          {error}
        </div>
      )}
      {result && (
        <div className="space-y-1 text-sm" data-testid="pilot-upload-result">
          <div>
            Accepted:{" "}
            <strong>{result.accepted_row_stock_numbers.length}</strong>{" "}
            · Rejected: <strong>{result.rejected_rows.length}</strong>
          </div>
          {result.rejected_rows.length > 0 && (
            <details data-testid="pilot-upload-rejected">
              <summary className="cursor-pointer text-destructive">
                Rejected rows
              </summary>
              <ul className="list-disc pl-4">
                {result.rejected_rows.map((r, idx) => (
                  <li key={idx}>
                    <span className="font-mono">
                      {r.row.stock_number || "(no stock)"}
                    </span>{" "}
                    — {r.reason}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

function TerminateForm({
  slug,
  onTerminated,
}: {
  slug: string;
  onTerminated: () => void;
}) {
  const [mode, setMode] = useState<"archive" | "cleanup">("archive");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  async function handleTerminate() {
    setSubmitting(true);
    setError(null);
    try {
      await terminatePilotDealership(slug, { reason, mode });
      onTerminated();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-2 rounded border p-2" data-testid="pilot-terminate">
      <h5 className="font-medium">Terminate pilot</h5>
      <div className="flex items-center gap-2">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as "archive" | "cleanup")}
          data-testid="pilot-terminate-mode"
          aria-label="Termination mode"
          className="rounded border p-1 text-sm"
        >
          <option value="archive">Archive (preserve data)</option>
          <option value="cleanup">Cleanup (delete children)</option>
        </select>
      </div>
      <Textarea
        placeholder="Reason (optional)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        data-testid="pilot-terminate-reason"
        aria-label="Termination reason"
        rows={2}
      />
      {!confirming ? (
        <Button
          type="button"
          variant="destructive"
          size="sm"
          onClick={() => setConfirming(true)}
          data-testid="pilot-terminate-init"
        >
          Terminate…
        </Button>
      ) : (
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="destructive"
            size="sm"
            disabled={submitting}
            onClick={() => void handleTerminate()}
            data-testid="pilot-terminate-confirm"
          >
            {submitting ? "Terminating…" : `Confirm ${mode}`}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setConfirming(false)}
          >
            Cancel
          </Button>
        </div>
      )}
      {error && (
        <div
          role="alert"
          data-testid="pilot-terminate-error"
          className="text-sm text-destructive"
        >
          {error}
        </div>
      )}
    </div>
  );
}
