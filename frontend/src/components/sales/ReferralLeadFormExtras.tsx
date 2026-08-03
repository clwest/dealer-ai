// Milestone 24 · Increment 3 (SESSION_183) — referring-customer picker.
//
// Optional "Referring customer (existing lead)" slot that composes
// into <LeadIntakeForm channel="referral"> via its `extras` prop.
// Backend contract preserved: the referring party IS an existing
// CustomerLead (self-FK per models.py:904); the picker's selection
// posts as `referrer_lead_id`. Field is optional per backend
// nullability — operators can record a referral where the referrer
// identity lives only in notes.
//
// UX: tenant-scoped lead list fetched on mount (limit=200), filtered
// client-side by name substring as the operator types. Top matches
// render as clickable rows; clicking selects. Selected lead shows
// as a chip with an "Unselect" button. `fetchAdminLeads` has no
// server-side name filter today; client-side substring match is
// sufficient for typical dealership scale (tens to a few hundred
// leads) — server-side search UI is a future enhancement (M25+
// candidate if evidence surfaces).

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchAdminLeads, type AdminLead } from "@/lib/api";

const MAX_VISIBLE_MATCHES = 10;

export interface ReferralLeadFormExtrasProps {
  /**
   * Controlled selection state. `null` = no referrer selected
   * (backend contract: NULL referrer FK is valid — referrals can
   * ship with referrer identity only in notes).
   */
  value: number | null;
  /**
   * Fires when the operator picks or clears a referring customer.
   * Parent Dialog handler folds this into the createReferralLead
   * payload's `referrer_lead_id` field.
   */
  onSelect: (leadId: number | null) => void;
}

export function ReferralLeadFormExtras({
  value,
  onSelect,
}: ReferralLeadFormExtrasProps) {
  const [leads, setLeads] = useState<AdminLead[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    fetchAdminLeads({ limit: 200 })
      .then((res) => {
        if (cancelled) return;
        setLeads(res.results);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(
          err instanceof Error
            ? err.message
            : "Failed to load existing leads for the picker.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedLead = useMemo(
    () => (value != null ? leads.find((l) => l.id === value) : undefined),
    [value, leads],
  );

  const matches = useMemo(() => {
    if (!search.trim()) return [] as AdminLead[];
    const needle = search.trim().toLowerCase();
    return leads
      .filter((lead) => {
        const haystack = `${lead.name} ${lead.phone} ${lead.email}`.toLowerCase();
        return haystack.includes(needle);
      })
      .slice(0, MAX_VISIBLE_MATCHES);
  }, [search, leads]);

  const handleClear = useCallback(() => {
    onSelect(null);
    setSearch("");
  }, [onSelect]);

  return (
    <div
      className="flex flex-col gap-2 rounded-md border border-input p-3"
      data-testid="referral-lead-form-extras"
    >
      <div className="flex items-center justify-between">
        <label
          className="text-xs font-semibold text-foreground"
          htmlFor="referral-lead-form-extras-search-input"
        >
          Referring customer (existing lead)
        </label>
        <span className="text-xs text-muted-foreground">
          Optional — leave blank if the referrer isn't a customer yet.
        </span>
      </div>
      {selectedLead ? (
        <div
          className="flex items-center justify-between rounded-md bg-muted/40 px-3 py-2"
          data-testid="referral-lead-form-extras-selected"
        >
          <span className="text-sm">
            <span className="font-medium">{selectedLead.name}</span>
            <span className="text-muted-foreground">
              {" "}
              — lead #{selectedLead.id}
              {selectedLead.phone ? ` · ${selectedLead.phone}` : ""}
            </span>
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClear}
            data-testid="referral-lead-form-extras-clear"
          >
            Unselect
          </Button>
        </div>
      ) : (
        <>
          <Input
            id="referral-lead-form-extras-search-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, phone, or email"
            data-testid="referral-lead-form-extras-search"
            disabled={loading}
          />
          {loading ? (
            <p className="text-xs text-muted-foreground">
              Loading existing leads…
            </p>
          ) : null}
          {loadError ? (
            <p
              className="text-xs text-destructive"
              role="alert"
              data-testid="referral-lead-form-extras-error"
            >
              {loadError}
            </p>
          ) : null}
          {!loading && !loadError && search.trim() && matches.length === 0 ? (
            <p
              className="text-xs text-muted-foreground"
              data-testid="referral-lead-form-extras-empty"
            >
              No existing leads match "{search.trim()}".
            </p>
          ) : null}
          {matches.length > 0 ? (
            <ul
              className="max-h-48 overflow-y-auto rounded border border-input bg-background"
              data-testid="referral-lead-form-extras-matches"
            >
              {matches.map((lead) => (
                <li key={lead.id}>
                  <button
                    type="button"
                    className="w-full px-3 py-2 text-left text-sm hover:bg-muted/40"
                    onClick={() => {
                      onSelect(lead.id);
                      setSearch("");
                    }}
                    data-testid={`referral-lead-form-extras-match-${lead.id}`}
                  >
                    <span className="font-medium">{lead.name}</span>
                    <span className="text-muted-foreground">
                      {" "}
                      — lead #{lead.id}
                      {lead.phone ? ` · ${lead.phone}` : ""}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </div>
  );
}
