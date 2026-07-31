// Manager Phase 3: Generate Ad modal.
//
// Opened by clicking "Generate ad" on a marketing or inventory
// recommendation card. Calls POST /admin/ad-copy/, displays 2-3
// editable variants, and lets the manager copy individual fields or
// the full ad to the clipboard. Nothing is auto-published.
//
// Visible failure modes:
// - LLM offline / 5xx → red banner with the backend message
// - 0 variants survived safety stack → empty state with the warnings
// - Backend warnings (e.g., scrub drops) shown above the variants

import { useEffect, useState } from "react";
import { Check, Clipboard, Copy, Loader2, X } from "lucide-react";

import {
  generateAdCopy,
  type AdCopyResponse,
  type AdCopyVariant,
  type RecommendedAction,
  type Vehicle,
} from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

interface Props {
  /** When non-null the modal is open and generates ads for this action. */
  action: RecommendedAction | null;
  /** Optional vehicle override (otherwise the backend resolves from evidence). */
  vehicleId?: number | null;
  onClose: () => void;
}

const PLATFORM_LABEL: Record<string, string> = {
  facebook: "Facebook",
  instagram: "Instagram",
  email: "Email",
  google_search: "Google Search",
  showroom: "Showroom",
};

const PLATFORM_TONE: Record<string, string> = {
  facebook: "bg-blue-100 text-blue-700",
  instagram: "bg-pink-100 text-pink-700",
  email: "bg-emerald-100 text-emerald-700",
  google_search: "bg-amber-100 text-amber-700",
  showroom: "bg-slate-200 text-slate-700",
};

interface EditableVariant extends AdCopyVariant {
  // Local edits to allow the manager to tweak before copying.
  edited_headline: string;
  edited_body: string;
  edited_cta: string;
}

function copyText(text: string): Promise<void> {
  if (
    typeof navigator !== "undefined" &&
    navigator.clipboard &&
    typeof navigator.clipboard.writeText === "function"
  ) {
    return navigator.clipboard.writeText(text);
  }
  return Promise.reject(new Error("clipboard API unavailable"));
}

function fullVariantText(v: EditableVariant): string {
  const cta = v.edited_cta.trim();
  return [
    v.edited_headline.trim(),
    "",
    v.edited_body.trim(),
    cta ? `\n→ ${cta}` : "",
  ]
    .join("\n")
    .trim();
}

function VehicleChip({ v }: { v: Vehicle }) {
  return (
    <span
      className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600"
      title={`${v.display_name} · ${v.stock_number}`}
    >
      {v.display_name} · #{v.stock_number} · {formatCurrency(v.price)}
    </span>
  );
}

function VariantCard({
  variant,
  onChange,
}: {
  variant: EditableVariant;
  onChange: (next: EditableVariant) => void;
}) {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  function copyAndFlash(field: string, text: string) {
    copyText(text)
      .then(() => {
        setCopiedField(field);
        setTimeout(() => setCopiedField(null), 1500);
      })
      .catch((err) => {
        console.error("Clipboard copy failed", err);
        setCopiedField(`error:${field}`);
        setTimeout(() => setCopiedField(null), 2000);
      });
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-md px-2 py-0.5 text-[10px] font-bold uppercase",
            PLATFORM_TONE[variant.platform_hint] ??
              "bg-slate-100 text-slate-700",
          )}
        >
          {PLATFORM_LABEL[variant.platform_hint] ?? variant.platform_hint}
        </span>
        {variant.scrubs_fired.length > 0 ? (
          <span
            className="text-[10px] italic text-amber-700"
            title={variant.scrubs_fired.join(", ")}
          >
            scrubbed: {variant.scrubs_fired.length}
          </span>
        ) : null}
        <button
          type="button"
          onClick={() => copyAndFlash("full", fullVariantText(variant))}
          className="ml-auto inline-flex items-center gap-1 rounded-md border border-brand-blue bg-brand-blue px-2 py-1 text-[11px] font-semibold text-white hover:bg-brand-blue/90"
        >
          {copiedField === "full" ? (
            <Check className="h-3 w-3" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          Copy ad
        </button>
      </div>

      <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Headline
        <div className="flex items-center gap-1">
          <input
            type="text"
            value={variant.edited_headline}
            onChange={(e) =>
              onChange({ ...variant, edited_headline: e.target.value })
            }
            className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm text-brand-ink"
          />
          <button
            type="button"
            onClick={() =>
              copyAndFlash("headline", variant.edited_headline.trim())
            }
            className="rounded-md border border-slate-200 bg-white px-2 py-1 text-slate-500 hover:bg-slate-50"
            title="Copy headline"
          >
            {copiedField === "headline" ? (
              <Check className="h-3 w-3" />
            ) : (
              <Clipboard className="h-3 w-3" />
            )}
          </button>
        </div>
      </label>

      <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Body
        <div className="flex items-start gap-1">
          <textarea
            value={variant.edited_body}
            rows={3}
            onChange={(e) =>
              onChange({ ...variant, edited_body: e.target.value })
            }
            className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm text-brand-ink"
          />
          <button
            type="button"
            onClick={() => copyAndFlash("body", variant.edited_body.trim())}
            className="rounded-md border border-slate-200 bg-white px-2 py-1 text-slate-500 hover:bg-slate-50"
            title="Copy body"
          >
            {copiedField === "body" ? (
              <Check className="h-3 w-3" />
            ) : (
              <Clipboard className="h-3 w-3" />
            )}
          </button>
        </div>
      </label>

      <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Call to action
        <div className="flex items-center gap-1">
          <input
            type="text"
            value={variant.edited_cta}
            onChange={(e) =>
              onChange({ ...variant, edited_cta: e.target.value })
            }
            className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm text-brand-ink"
          />
          <button
            type="button"
            onClick={() => copyAndFlash("cta", variant.edited_cta.trim())}
            className="rounded-md border border-slate-200 bg-white px-2 py-1 text-slate-500 hover:bg-slate-50"
            title="Copy CTA"
          >
            {copiedField === "cta" ? (
              <Check className="h-3 w-3" />
            ) : (
              <Clipboard className="h-3 w-3" />
            )}
          </button>
        </div>
      </label>
    </div>
  );
}

export default function GenerateAdModal({
  action,
  vehicleId,
  onClose,
}: Props) {
  const [response, setResponse] = useState<AdCopyResponse | null>(null);
  const [variants, setVariants] = useState<EditableVariant[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (action == null) {
      setResponse(null);
      setVariants([]);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setResponse(null);
    setVariants([]);

    generateAdCopy({
      recommendation: action,
      vehicle_id: vehicleId ?? null,
    })
      .then((res) => {
        if (cancelled) return;
        setResponse(res);
        setVariants(
          res.variants.map((v) => ({
            ...v,
            edited_headline: v.headline,
            edited_body: v.body,
            edited_cta: v.cta,
          })),
        );
      })
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof Error
            ? err.message
            : "Ad generation failed — see network panel.";
        console.error("generateAdCopy failed", err);
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [action, vehicleId]);

  if (action == null) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4">
      <div className="my-8 w-full max-w-3xl rounded-lg bg-white shadow-2xl">
        <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Generate ad
            </div>
            <h2 className="text-lg font-bold text-brand-ink">{action.title}</h2>
            <div className="mt-1 text-xs text-slate-500">
              {action.action_text}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating ad copy…
            </div>
          ) : null}

          {error ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <div className="font-semibold">Ad generation failed</div>
              <div className="mt-1 break-words">{error}</div>
              <div className="mt-2 text-xs text-red-600">
                Check that the backend is reachable and the LLM provider is
                running. The modal stays open so you can retry by closing and
                clicking again.
              </div>
            </div>
          ) : null}

          {response && response.vehicles_used.length > 0 ? (
            <div>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Vehicles referenced
              </div>
              <div className="flex flex-wrap gap-1.5">
                {response.vehicles_used.map((v) => (
                  <VehicleChip key={v.id} v={v} />
                ))}
              </div>
            </div>
          ) : null}

          {response && response.warnings.length > 0 ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <div className="font-semibold">Notes from the safety scrub</div>
              <ul className="mt-1 list-inside list-disc space-y-0.5">
                {response.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {!loading && !error && variants.length === 0 && response ? (
            <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
              No variants survived safety review. Try regenerating, or compose
              copy by hand using the recommendation context above.
            </div>
          ) : null}

          {variants.length > 0 ? (
            <div className="space-y-3">
              {variants.map((v, idx) => (
                <VariantCard
                  key={idx}
                  variant={v}
                  onChange={(next) =>
                    setVariants((curr) => {
                      const cp = [...curr];
                      cp[idx] = next;
                      return cp;
                    })
                  }
                />
              ))}
            </div>
          ) : null}

          <div className="border-t border-slate-100 pt-3 text-[11px] text-slate-500">
            Drafts only — the manager reviews and posts manually. Numbers
            (payments, prices, stock #s) come from real inventory; rate /
            discount / dealer-cost language is auto-scrubbed before drafts
            reach you.
          </div>
        </div>
      </div>
    </div>
  );
}
