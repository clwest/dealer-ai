// Milestone 33 · Increment 2 (SESSION_212) — DealStructure read view.
//
// Fetches a single DealStructure via `getDealStructure(id)` (M33.1
// backend endpoint at canonical path GET /admin/deal-structures/<int:pk>/)
// and renders it read-only.
//
// Per MILESTONE_33_PLANNING.md §5.b D6:
//   - Three-section layout: Vehicle / Proposed structure values /
//     Derived ratios.
//   - Every value labeled as "proposed structure value" (never
//     "sales target" at read time — all values are committed to the
//     structure).
//   - NULL-safe ratio display: "Not computable — requires income" for
//     NULL PTI/DTI on M10.1-era CAs without income captured.
//   - No edit / PATCH / delete controls in M33 (activation-vocabulary-
//     asymmetry per M31 lesson w; iteration UX deferred per §5.h).
//
// Financial-language contract per D5 + R10: never "lender-approved",
// "lender-committed", or "actual". Playwright regex assertion at D8
// enforces this.

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/authFetch";
import {
  getDealStructure,
  type DealStructureProjection,
} from "@/lib/fAndIApi";

export interface DealStructureReadViewProps {
  dealStructureId: number;
  onClose?: () => void;
  /** Injected for tests. Defaults to shipped `getDealStructure`. */
  load?: typeof getDealStructure;
}

function nullSafeRatio(value: string | null): string {
  if (value === null) return "Not computable — requires income";
  return `${value}%`;
}

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return "Deal structure not found in your dealership.";
    }
    if (err.status === 403) {
      return "Only F&I managers or dealer owners can view deal structures.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to load the deal structure.";
}

export function DealStructureReadView({
  dealStructureId,
  onClose,
  load = getDealStructure,
}: DealStructureReadViewProps) {
  const [loadState, setLoadState] = useState<
    "loading" | "ready" | "error"
  >("loading");
  const [structure, setStructure] = useState<DealStructureProjection | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadState("loading");
    setErrorMessage(null);
    load(dealStructureId)
      .then((row) => {
        if (cancelled) return;
        setStructure(row);
        setLoadState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setErrorMessage(humanizeError(err));
        setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [dealStructureId, load]);

  return (
    <div
      className="rounded-md border border-slate-200 bg-white p-4"
      data-testid="deal-structure-read"
    >
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold">Proposed deal structure</h2>
          <p className="text-xs text-muted-foreground">
            Latest F&amp;I-authored structure for this application. All
            values are proposed structure values — a lender submission
            has not yet been created.
          </p>
        </div>
        {onClose ? (
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            data-testid="deal-structure-read-close"
          >
            Close
          </Button>
        ) : null}
      </div>

      {loadState === "loading" && (
        <p
          className="text-sm text-muted-foreground"
          data-testid="deal-structure-read-loading"
        >
          Loading proposed structure…
        </p>
      )}
      {loadState === "error" && (
        <p
          role="alert"
          className="text-sm text-destructive"
          data-testid="deal-structure-read-error"
        >
          {errorMessage}
        </p>
      )}
      {loadState === "ready" && structure !== null && (
        <div className="space-y-4">
          {/* Section 1 — Vehicle */}
          <section data-testid="deal-structure-read-vehicle-section">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Vehicle
            </h3>
            <div className="text-sm">
              Stock #
              <span
                data-testid="deal-structure-read-vehicle-stock"
                className="font-medium"
              >
                {structure.vehicle_stock}
              </span>
            </div>
          </section>

          {/* Section 2 — Proposed structure values */}
          <section data-testid="deal-structure-read-values-section">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Proposed structure values
            </h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm md:grid-cols-3">
              <div>
                <dt className="text-xs text-muted-foreground">
                  Sale price
                </dt>
                <dd
                  data-testid="deal-structure-read-sale-price"
                  className="font-medium"
                >
                  {structure.sale_price}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Down payment
                </dt>
                <dd
                  data-testid="deal-structure-read-down-payment"
                  className="font-medium"
                >
                  {structure.down_payment}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Trade allowance
                </dt>
                <dd
                  data-testid="deal-structure-read-trade-allowance"
                  className="font-medium"
                >
                  {structure.trade_allowance}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Trade payoff
                </dt>
                <dd
                  data-testid="deal-structure-read-trade-payoff"
                  className="font-medium"
                >
                  {structure.trade_payoff}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Taxes</dt>
                <dd
                  data-testid="deal-structure-read-taxes"
                  className="font-medium"
                >
                  {structure.taxes}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Fees</dt>
                <dd
                  data-testid="deal-structure-read-fees"
                  className="font-medium"
                >
                  {structure.fees}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Amount financed
                </dt>
                <dd
                  data-testid="deal-structure-read-amount-financed"
                  className="font-medium"
                >
                  {structure.amount_financed}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Proposed APR
                </dt>
                <dd
                  data-testid="deal-structure-read-apr"
                  className="font-medium"
                >
                  {structure.apr}%
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Proposed term
                </dt>
                <dd
                  data-testid="deal-structure-read-term-months"
                  className="font-medium"
                >
                  {structure.term_months} mo
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">
                  Proposed monthly payment
                </dt>
                <dd
                  data-testid="deal-structure-read-monthly-payment"
                  className="font-medium"
                >
                  {structure.monthly_payment}
                </dd>
              </div>
            </dl>
          </section>

          {/* Section 3 — Derived ratios */}
          <section data-testid="deal-structure-read-ratios-section">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Derived ratios
            </h3>
            <dl className="grid grid-cols-3 gap-x-4 gap-y-2 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">LTV</dt>
                <dd
                  data-testid="deal-structure-read-ltv"
                  className="font-medium"
                >
                  {nullSafeRatio(structure.ltv_pct)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">PTI</dt>
                <dd
                  data-testid="deal-structure-read-pti"
                  className="font-medium"
                >
                  {nullSafeRatio(structure.pti_pct)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">DTI</dt>
                <dd
                  data-testid="deal-structure-read-dti"
                  className="font-medium"
                >
                  {nullSafeRatio(structure.dti_pct)}
                </dd>
              </div>
            </dl>
          </section>
        </div>
      )}
    </div>
  );
}
