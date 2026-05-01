// Manager Phase 4: assignment dropdown shown inside LeadDetailModal.
//
// Wraps the GET /admin/salespeople/?active=true list and the POST
// /admin/lead/<id>/assign/ mutation in a single UX. Renders the current
// assignment as a chip, opens a panel of active advisors, and supports
// "Unassign". Surfaces errors visibly instead of failing silently.

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Loader2, User, X } from "lucide-react";

import {
  assignLead,
  fetchAdminSalespeople,
  type SalespersonAdmin,
  type SalespersonAssignment,
} from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  leadId: number;
  current: SalespersonAssignment | null;
  onChange: (next: SalespersonAssignment | null) => void;
}

export default function AssignmentDropdown({
  leadId,
  current,
  onChange,
}: Props) {
  const [open, setOpen] = useState(false);
  const [advisors, setAdvisors] = useState<SalespersonAdmin[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchAdminSalespeople({ activeOnly: true })
      .then((res) => {
        if (cancelled) return;
        setAdvisors(res.results);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load salespeople.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Close the panel when the user clicks outside.
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function pick(salespersonId: number | null) {
    setBusy(true);
    setError(null);
    assignLead(leadId, salespersonId)
      .then((updated) => {
        onChange(updated.assigned_to);
        setOpen(false);
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Assignment failed.",
        );
      })
      .finally(() => {
        setBusy(false);
      });
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={busy}
        className={cn(
          "inline-flex items-center gap-2 rounded-md border px-2 py-1 text-xs",
          current
            ? "border-emerald-300 bg-emerald-50 text-emerald-800"
            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        )}
      >
        {current?.photo_url ? (
          <img
            src={current.photo_url}
            alt=""
            className="h-5 w-5 rounded-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <User className="h-3.5 w-3.5" />
        )}
        <span className="font-medium">
          {current ? current.name : "Unassigned"}
        </span>
        {busy ? (
          <Loader2 className="h-3 w-3 animate-spin text-slate-500" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>

      {open ? (
        <div className="absolute right-0 top-full z-30 mt-1 w-72 rounded-md border border-slate-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Assign advisor
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded p-0.5 text-slate-400 hover:bg-slate-100"
              aria-label="Close"
            >
              <X className="h-3 w-3" />
            </button>
          </div>

          {error ? (
            <div className="border-b border-red-100 bg-red-50 px-3 py-2 text-[11px] text-red-700">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="flex items-center justify-center px-3 py-4 text-xs text-slate-500">
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              Loading…
            </div>
          ) : (
            <ul className="max-h-72 overflow-y-auto py-1">
              <li>
                <button
                  type="button"
                  onClick={() => pick(null)}
                  className={cn(
                    "flex w-full items-center justify-between px-3 py-1.5 text-xs hover:bg-slate-50",
                    current === null && "font-semibold text-emerald-700",
                  )}
                >
                  <span>Unassigned</span>
                  {current === null ? <Check className="h-3 w-3" /> : null}
                </button>
              </li>
              {advisors.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    onClick={() => pick(a.id)}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-slate-50",
                      current?.id === a.id &&
                        "font-semibold text-emerald-700",
                    )}
                  >
                    {a.photo_url ? (
                      <img
                        src={a.photo_url}
                        alt=""
                        className="h-6 w-6 rounded-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display =
                            "none";
                        }}
                      />
                    ) : (
                      <User className="h-4 w-4 text-slate-400" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{a.name}</div>
                      {a.title ? (
                        <div className="truncate text-[10px] text-slate-500">
                          {a.title}
                        </div>
                      ) : null}
                    </div>
                    {current?.id === a.id ? (
                      <Check className="h-3 w-3 flex-none" />
                    ) : null}
                  </button>
                </li>
              ))}
              {advisors.length === 0 ? (
                <li className="px-3 py-2 text-[11px] text-slate-500">
                  No active salespeople. Seed via{" "}
                  <code className="rounded bg-slate-100 px-1 font-mono">
                    seed_phase4_demo
                  </code>
                  .
                </li>
              ) : null}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
