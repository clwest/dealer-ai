// Milestone 10 · Increment 7 (SESSION_112) — F&I deals-in-progress page.
//
// Two-tab MVP per MILESTONE_10_PLANNING.md §1.8.d Option A (user-
// confirmed at SESSION_112 open, recorded in §0.a). This is the
// list tab; the sibling per-deal compliance-audit tab lives at
// `DealerFandICompliance.tsx`.
//
// Consumes GET /admin/f-and-i/deals/ with optional filter params
// (state / funding_state / has_chargebacks). Rendered as a
// simple filterable table — no pagination at M10.7 (100-row
// server cap; server-side pagination in M11+ if operator
// evidence surfaces need).
//
// Role gating: the backend enforces
// IsFinanceManagerOrOwnerAtActiveDealership. Advisors / porters
// receive 403 and the page renders a "you don't have access"
// message via the ApiError catch.

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  fetchDeals,
  type ContractState,
  type DealListItem,
  type FundingState,
} from "@/lib/fAndIApi";

const CONTRACT_STATE_OPTIONS: Array<{
  value: ContractState | "";
  label: string;
}> = [
  { value: "", label: "Any contract state" },
  { value: "unsigned", label: "Unsigned" },
  { value: "signed", label: "Signed" },
  { value: "voided", label: "Voided" },
];

const FUNDING_STATE_OPTIONS: Array<{
  value: FundingState | "";
  label: string;
}> = [
  { value: "", label: "Any funding state" },
  { value: "pending_funding", label: "Pending funding" },
  { value: "funded", label: "Funded" },
  { value: "chargedback", label: "Chargedback" },
];

export default function DealerFandIDeals() {
  const [deals, setDeals] = useState<DealListItem[]>([]);
  const [contractStateFilter, setContractStateFilter] =
    useState<ContractState | "">("");
  const [fundingStateFilter, setFundingStateFilter] =
    useState<FundingState | "">("");
  const [hasChargebacksFilter, setHasChargebacksFilter] = useState(false);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const result = await fetchDeals({
        state: contractStateFilter || undefined,
        funding_state: fundingStateFilter || undefined,
        has_chargebacks: hasChargebacksFilter || undefined,
      });
      setDeals(result);
      setLoadState("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load deals.",
      );
      setLoadState("error");
    }
  }, [contractStateFilter, fundingStateFilter, hasChargebacksFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">F&amp;I Deals in Progress</h1>
        <p className="text-sm text-muted-foreground">
          Every signed / pending contract with its current funding
          and chargeback state. Click a row to open the deal-jacket
          compliance audit.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>
            Narrow the list by contract state, funding state, or
            chargeback presence.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <label className="flex flex-col text-sm">
              <span className="mb-1 text-muted-foreground">
                Contract state
              </span>
              <select
                aria-label="Contract state filter"
                value={contractStateFilter}
                onChange={(e) =>
                  setContractStateFilter(
                    e.target.value as ContractState | "",
                  )
                }
                className="rounded border border-input bg-background px-3 py-2"
              >
                {CONTRACT_STATE_OPTIONS.map((opt) => (
                  <option key={opt.value || "any"} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 text-muted-foreground">
                Funding state
              </span>
              <select
                aria-label="Funding state filter"
                value={fundingStateFilter}
                onChange={(e) =>
                  setFundingStateFilter(
                    e.target.value as FundingState | "",
                  )
                }
                className="rounded border border-input bg-background px-3 py-2"
              >
                {FUNDING_STATE_OPTIONS.map((opt) => (
                  <option key={opt.value || "any"} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={hasChargebacksFilter}
                onChange={(e) => setHasChargebacksFilter(e.target.checked)}
                aria-label="Has chargebacks"
              />
              Has chargebacks
            </label>
          </div>
        </CardContent>
      </Card>

      {loadState === "loading" && (
        <p className="text-muted-foreground">Loading deals…</p>
      )}
      {loadState === "error" && (
        <p role="alert" className="text-destructive">
          {errorMessage}
        </p>
      )}
      {loadState === "ready" && deals.length === 0 && (
        <Card>
          <CardContent className="py-6 text-center text-muted-foreground">
            No deals match the current filters.
          </CardContent>
        </Card>
      )}
      {loadState === "ready" && deals.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{deals.length} deals</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2">Stock</th>
                  <th className="pb-2">Type</th>
                  <th className="pb-2">Contract state</th>
                  <th className="pb-2">Funding</th>
                  <th className="pb-2">Chargebacks</th>
                  <th className="pb-2 text-right"></th>
                </tr>
              </thead>
              <tbody>
                {deals.map((deal) => (
                  <tr key={deal.contract_id} className="border-b last:border-0">
                    <td className="py-2">{deal.vehicle_stock}</td>
                    <td className="py-2">{deal.contract_type}</td>
                    <td className="py-2">{deal.contract_state}</td>
                    <td className="py-2">
                      {deal.funding_state ?? "—"}
                      {deal.funding_amount && (
                        <span className="text-muted-foreground">
                          {" "}
                          (${deal.funding_amount})
                        </span>
                      )}
                    </td>
                    <td className="py-2">{deal.chargeback_count}</td>
                    <td className="py-2 text-right">
                      <Button variant="outline" size="sm" asChild>
                        <Link
                          to={`/dealer-ai-f-and-i/${deal.contract_id}/compliance`}
                        >
                          Open jacket
                        </Link>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
