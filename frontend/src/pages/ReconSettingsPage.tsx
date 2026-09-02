// SESSION_228 — store-level recon authorization + budget settings
// + the flat-rate price sheet (ReconRateCard) editor.
//
// Owner-only for settings; owner + recon manager for rate cards
// (backend enforces both).

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, PlusCircle, Save, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/AuthContext";
import { ApiError, ForbiddenError, UnauthenticatedError } from "@/lib/authFetch";
import {
  CONDITION_CATEGORY_CHOICES,
  createRateCardItem,
  deactivateRateCardItem,
  fetchRateCardItems,
  fetchReconSettings,
  updateRateCardItem,
  updateReconSettings,
  type ReconRateCardItem,
  type ReconSettings,
} from "@/lib/api";

const OWNER_ROLES = ["dealer_owner"];
const RATE_CARD_ROLES = ["dealer_owner", "sales_manager", "recon_manager"];

function _humanizeLoadError(err: unknown): string {
  if (err instanceof UnauthenticatedError) return "Sign in to view recon settings.";
  if (err instanceof ForbiddenError)
    return "You do not have permission to view recon settings.";
  if (err instanceof ApiError) return `Server returned ${err.status}.`;
  return "Failed to load recon settings.";
}

export default function ReconSettingsPage() {
  const { hasRole } = useAuth();
  const isOwner = useMemo(() => hasRole(...OWNER_ROLES), [hasRole]);
  const canEditRateCard = useMemo(
    () => hasRole(...RATE_CARD_ROLES),
    [hasRole],
  );

  const [settings, setSettings] = useState<ReconSettings | null>(null);
  const [rateCard, setRateCard] = useState<ReconRateCardItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [bandsText, setBandsText] = useState("");

  const _load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, r] = await Promise.all([
        fetchReconSettings(),
        fetchRateCardItems(true),
      ]);
      setSettings(s.settings);
      setBandsText(JSON.stringify(s.settings.recon_budget_bands, null, 2));
      setRateCard(r.items);
    } catch (err) {
      setError(_humanizeLoadError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    _load();
  }, [_load]);

  async function _saveSettings() {
    if (!settings) return;
    let bands: unknown;
    try {
      bands = bandsText.trim() ? JSON.parse(bandsText) : [];
    } catch {
      setSaveError('Bands must be valid JSON — e.g. [{"up_to":"10000","budget":"1200"}]');
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const res = await updateReconSettings({
        recon_authorization_mode: settings.recon_authorization_mode,
        recon_budget_default: settings.recon_budget_default,
        recon_budget_bands: bands as ReconSettings["recon_budget_bands"],
      });
      setSettings(res.settings);
    } catch (err) {
      if (err instanceof ApiError) {
        setSaveError(`Server returned ${err.status}: ${err.body ?? ""}`);
      } else {
        setSaveError("Failed to save settings.");
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-8 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading recon settings…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl p-6 text-sm text-destructive">{error}</div>
    );
  }

  if (!settings) return null;

  return (
    <div className="max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Recon settings</h1>
        <p className="text-sm text-muted-foreground">
          How your store handles recon spend authorization.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Authorization mode</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <fieldset className="space-y-2">
            <label className="flex items-start gap-2">
              <input
                type="radio"
                name="mode"
                className="mt-1"
                disabled={!isOwner}
                checked={settings.recon_authorization_mode === "per_job"}
                onChange={() =>
                  setSettings({
                    ...settings,
                    recon_authorization_mode: "per_job",
                  })
                }
              />
              <div>
                <div className="font-medium">Approve every job</div>
                <div className="text-xs text-muted-foreground">
                  Wholesale posture. Every work order waits on a human before
                  the money moves.
                </div>
              </div>
            </label>
            <label className="flex items-start gap-2">
              <input
                type="radio"
                name="mode"
                className="mt-1"
                disabled={!isOwner}
                checked={settings.recon_authorization_mode === "budget"}
                onChange={() =>
                  setSettings({
                    ...settings,
                    recon_authorization_mode: "budget",
                  })
                }
              />
              <div>
                <div className="font-medium">
                  Auto-authorize under a per-car budget
                </div>
                <div className="text-xs text-muted-foreground">
                  Retail posture. Work under the number happens; over-budget
                  jobs land in the Recon queue for a manager.
                </div>
              </div>
            </label>
          </fieldset>

          {settings.recon_authorization_mode === "budget" && (
            <div className="space-y-3">
              <label className="block space-y-1 text-sm">
                <span className="font-medium">Default budget per car</span>
                <Input
                  disabled={!isOwner}
                  value={settings.recon_budget_default ?? ""}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      recon_budget_default: e.target.value.trim() || null,
                    })
                  }
                  placeholder="1200.00"
                />
              </label>
              <div className="space-y-1 text-sm">
                <div className="font-medium">
                  Bands by acquisition price (optional)
                </div>
                <div className="text-xs text-muted-foreground">
                  JSON list. Each entry: {"{"}"up_to": Decimal or null,
                  "budget": Decimal{"}"}. First band whose <code>up_to</code>{" "}
                  is ≥ the car's price applies; <code>null</code> is the
                  catch-all top band.
                </div>
                <Textarea
                  disabled={!isOwner}
                  rows={6}
                  value={bandsText}
                  onChange={(e) => setBandsText(e.target.value)}
                  className="font-mono text-xs"
                />
              </div>
            </div>
          )}

          {saveError && (
            <div className="text-xs text-destructive">{saveError}</div>
          )}

          {isOwner && (
            <div className="flex justify-end">
              <Button onClick={_saveSettings} disabled={saving} className="gap-1">
                {saving ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Save className="h-3 w-3" />
                )}
                Save settings
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Flat-rate price sheet</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-xs text-muted-foreground">
            Items pre-selected on every inspection when marked "retail
            default". The inspector picks from the sheet or types a free-text
            finding — a sheet that blocks the unusual job is worse than no
            sheet.
          </div>
          {rateCard.length === 0 ? (
            <div className="rounded border bg-muted/30 p-4 text-sm text-muted-foreground">
              No rate-card items yet.
            </div>
          ) : (
            <div className="space-y-2">
              {rateCard.map((item) => (
                <RateCardRow
                  key={item.id}
                  item={item}
                  canEdit={canEditRateCard}
                  onChanged={_load}
                />
              ))}
            </div>
          )}

          {canEditRateCard && <NewRateCardItemForm onCreated={_load} />}
        </CardContent>
      </Card>
    </div>
  );
}

function RateCardRow({
  item,
  canEdit,
  onChanged,
}: {
  item: ReconRateCardItem;
  canEdit: boolean;
  onChanged: () => void;
}) {
  const [saving, setSaving] = useState(false);

  async function _deactivate() {
    setSaving(true);
    try {
      await deactivateRateCardItem(item.id);
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  async function _toggleDefault() {
    setSaving(true);
    try {
      await updateRateCardItem(item.id, {
        retail_default: !item.retail_default,
      });
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className={`flex items-center justify-between rounded border p-2 text-sm ${
        item.active ? "" : "opacity-60"
      }`}
    >
      <div className="flex-1">
        <div className="font-medium">
          {item.name}
          {item.variant && (
            <span className="ml-2 text-xs text-muted-foreground">
              · {item.variant}
            </span>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          ${item.flat_price} · {item.work_order_category}
          {item.retail_default && (
            <span className="ml-2 rounded bg-emerald-100 px-1 text-emerald-800">
              retail default
            </span>
          )}
          {!item.active && (
            <span className="ml-2 rounded bg-slate-100 px-1 text-slate-700">
              inactive
            </span>
          )}
        </div>
      </div>
      {canEdit && item.active && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            className="text-xs"
            onClick={_toggleDefault}
            disabled={saving}
          >
            {item.retail_default ? "Un-default" : "Set default"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-xs text-destructive gap-1"
            onClick={_deactivate}
            disabled={saving}
          >
            <Trash2 className="h-3 w-3" />
            Deactivate
          </Button>
        </div>
      )}
    </div>
  );
}

function NewRateCardItemForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState(
    CONDITION_CATEGORY_CHOICES[0].value,
  );
  const [flatPrice, setFlatPrice] = useState("");
  const [variant, setVariant] = useState("");
  const [retailDefault, setRetailDefault] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function _save() {
    if (!name.trim() || !flatPrice.trim()) {
      setErr("Name and flat price are required.");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      await createRateCardItem({
        name,
        work_order_category: category,
        flat_price: flatPrice,
        variant,
        retail_default: retailDefault,
      });
      setName("");
      setFlatPrice("");
      setVariant("");
      setRetailDefault(false);
      setOpen(false);
      onCreated();
    } catch (e) {
      setErr(
        e instanceof ApiError
          ? `Server returned ${e.status}: ${e.body ?? ""}`
          : "Failed to save.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="gap-1"
        onClick={() => setOpen(true)}
      >
        <PlusCircle className="h-3 w-3" />
        Add rate-card item
      </Button>
    );
  }

  return (
    <div className="space-y-2 rounded border bg-muted/40 p-3 text-sm">
      <div className="grid grid-cols-2 gap-2">
        <Input
          placeholder="Item name (LOF, Tires, …)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          placeholder="Variant (16-inch, front axle, …)"
          value={variant}
          onChange={(e) => setVariant(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded border bg-background px-2 py-1 text-sm"
        >
          {CONDITION_CATEGORY_CHOICES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <Input
          placeholder="Flat price"
          value={flatPrice}
          onChange={(e) => setFlatPrice(e.target.value)}
        />
      </div>
      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={retailDefault}
          onChange={() => setRetailDefault((v) => !v)}
        />
        Retail default — pre-tick on every inspection when this store runs in
        budget mode.
      </label>
      {err && <div className="text-xs text-destructive">{err}</div>}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <Button size="sm" onClick={_save} disabled={saving}>
          Save
        </Button>
      </div>
    </div>
  );
}
