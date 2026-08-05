// Milestone 33 · Increment 2 (SESSION_212) — DealStructure form.
//
// Posts to POST /admin/deal-structures/ (M10.2 shipped endpoint) via
// `createDealStructure`. Per MILESTONE_33_PLANNING.md §5.b D5:
//
// - Three-section layout: Vehicle (read-only) / Sales-side targets
//   (prepopulated from writeup context; editable) / F&I proposed
//   structure values (blank on load; explicit-entry required).
//
// - **Truthful-entry contract (D5 — critical):**
//   - Blank ≠ 0 anywhere on financial fields.
//   - Submit disabled until explicit values for `amount_financed`,
//     `taxes`, `fees` (visible reason).
//   - `trade_payoff` requires either an explicit numeric value OR a
//     dedicated "No trade payoff" checkbox (untouched blank blocks
//     submit; checking the checkbox clears the input and signals
//     explicit zero-intent).
//   - Prepopulated fields are editable; the visual "sales target"
//     affordance flips to "proposed structure value" once revised.
//   - Basic non-blocking consistency warning when
//     `trade_payoff > 0 && trade_allowance == 0` (obvious
//     contradiction — a trade being paid off should carry an
//     allowance).
//   - `back_end_products` omitted from the M33 form (defaults to `[]`
//     server-side; truthful — no BEPAs at structuring time).
//
// - **Financial-language contract (D5 + R10 — critical):** every
//   label / placeholder / tooltip / aria-label uses only "sales
//   target" (prepopulated) and "proposed structure value" (F&I-
//   entered or revised). Never "lender-approved", "lender-committed",
//   or "actual". Playwright regex assertion at D8 enforces.
//
// - **No client-side monthly-payment auto-derivation (D7).** F&I
//   types the proposed monthly payment explicitly. `services.payment_engine`
//   exists but is not wired — cadence variability (standard-APR vs
//   BHPH weekly/biweekly) puts the calculator UX out of M33 scope.

import { useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/authFetch";
import {
  createDealStructure,
  type CreateDealStructureRequest,
  type CreditApplicationWriteupContext,
  type DealStructureProjection,
} from "@/lib/fAndIApi";

export interface DealStructureFormProps {
  creditApplicationId: number;
  writeupContext: CreditApplicationWriteupContext;
  onCreated: (deal: DealStructureProjection) => void;
  onCancel?: () => void;
  /** Injected for tests. Defaults to shipped `createDealStructure`. */
  submit?: typeof createDealStructure;
}

type FieldValue = { raw: string; touched: boolean };

function initField(seed: string | null | undefined): FieldValue {
  return { raw: seed != null ? String(seed) : "", touched: false };
}

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 400) {
      return "Invalid structure fields. Check the values and try again.";
    }
    if (err.status === 404) {
      return "Credit application or vehicle not found in your dealership.";
    }
    if (err.status === 403) {
      return "Only F&I managers or dealer owners can create deal structures.";
    }
    if (err.status === 409) {
      return "Conflict — an existing record blocks this create.";
    }
    return `Server returned ${err.status}.`;
  }
  return "Failed to create the deal structure.";
}

/**
 * Decimal validation: accepts explicit "0" and "0.00" as truthful
 * zero (operator confirms zero); rejects blank as "not yet confirmed"
 * (returns null so the submit gate can distinguish blank from zero).
 * Trims whitespace; rejects non-finite numbers.
 */
function parseExplicitDecimal(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const num = Number(trimmed);
  if (!Number.isFinite(num) || num < 0) return null;
  return num.toFixed(2);
}

function parseExplicitInt(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const num = Number(trimmed);
  if (!Number.isFinite(num) || !Number.isInteger(num) || num < 1) return null;
  return num;
}

/**
 * Label helper — prepopulated field flips affordance from
 * "sales target" to "proposed structure value" once the operator
 * revises it (touched === true AND value differs from prepop).
 */
function fieldAffordance(
  seedValue: string | null | undefined,
  currentRaw: string,
  touched: boolean,
): "sales-target" | "proposed" | "blank-required" {
  const seedNormalized = seedValue != null ? String(seedValue).trim() : "";
  const currentNormalized = currentRaw.trim();
  if (!seedNormalized && !currentNormalized) return "blank-required";
  if (touched && seedNormalized !== currentNormalized) return "proposed";
  if (seedNormalized) return "sales-target";
  return "proposed";
}

function affordanceBadge(kind: ReturnType<typeof fieldAffordance>) {
  if (kind === "sales-target") {
    return (
      <span
        data-testid-affordance="sales-target"
        className="ml-1 rounded bg-slate-100 px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-600"
      >
        Sales target
      </span>
    );
  }
  if (kind === "proposed") {
    return (
      <span
        data-testid-affordance="proposed"
        className="ml-1 rounded bg-blue-100 px-1 text-[10px] font-semibold uppercase tracking-wide text-blue-700"
      >
        Proposed
      </span>
    );
  }
  return (
    <span
      data-testid-affordance="blank-required"
      className="ml-1 rounded bg-amber-100 px-1 text-[10px] font-semibold uppercase tracking-wide text-amber-700"
    >
      F&amp;I entry required
    </span>
  );
}

export function DealStructureForm({
  creditApplicationId,
  writeupContext,
  onCreated,
  onCancel,
  submit = createDealStructure,
}: DealStructureFormProps) {
  const terms = writeupContext.terms;
  const vehicle = writeupContext.vehicle;

  // Sales-side prepopulated fields (editable).
  const [salePrice, setSalePrice] = useState<FieldValue>(() =>
    initField(terms.vehicle_price),
  );
  const [downPayment, setDownPayment] = useState<FieldValue>(() =>
    initField(terms.down_payment),
  );
  const [tradeAllowance, setTradeAllowance] = useState<FieldValue>(() =>
    initField(terms.trade_allowance),
  );
  const [apr, setApr] = useState<FieldValue>(() =>
    initField(terms.apr_target),
  );
  const [termMonths, setTermMonths] = useState<FieldValue>(() =>
    initField(
      terms.term_months_target != null ? String(terms.term_months_target) : "",
    ),
  );
  const [monthlyPayment, setMonthlyPayment] = useState<FieldValue>(() =>
    initField(terms.monthly_payment_target),
  );

  // F&I-entered blank fields.
  const [amountFinanced, setAmountFinanced] = useState<FieldValue>({
    raw: "",
    touched: false,
  });
  const [taxes, setTaxes] = useState<FieldValue>({ raw: "", touched: false });
  const [fees, setFees] = useState<FieldValue>({ raw: "", touched: false });

  // Trade payoff — either explicit numeric entry OR the "No trade
  // payoff" checkbox (which locks the input to 0 and signals explicit
  // zero-intent). Untouched blank blocks submit.
  const [tradePayoff, setTradePayoff] = useState<FieldValue>({
    raw: "",
    touched: false,
  });
  const [noTradePayoff, setNoTradePayoff] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Derived parsed values (null when blank/invalid).
  const salePriceParsed = parseExplicitDecimal(salePrice.raw);
  const amountFinancedParsed = parseExplicitDecimal(amountFinanced.raw);
  const aprParsed = parseExplicitDecimal(apr.raw);
  const termMonthsParsed = parseExplicitInt(termMonths.raw);
  const monthlyPaymentParsed = parseExplicitDecimal(monthlyPayment.raw);
  const taxesParsed = parseExplicitDecimal(taxes.raw);
  const feesParsed = parseExplicitDecimal(fees.raw);
  const downPaymentParsed = parseExplicitDecimal(downPayment.raw);
  const tradeAllowanceParsed = parseExplicitDecimal(tradeAllowance.raw);

  // Trade payoff: checkbox override wins.
  const tradePayoffEffective = noTradePayoff
    ? "0.00"
    : parseExplicitDecimal(tradePayoff.raw);
  const tradePayoffConfirmed = noTradePayoff || tradePayoff.touched;

  // Submit-gate: every required + explicit-entry field must be a
  // valid explicit value. Blank means not yet confirmed and never
  // silently converts to 0.
  const missingReasons = useMemo(() => {
    const reasons: string[] = [];
    if (salePriceParsed === null)
      reasons.push("Enter a sale price.");
    if (aprParsed === null)
      reasons.push("Enter a proposed APR.");
    if (termMonthsParsed === null)
      reasons.push("Enter a proposed term (in months).");
    if (monthlyPaymentParsed === null)
      reasons.push("Enter a proposed monthly payment.");
    if (amountFinancedParsed === null)
      reasons.push("Enter amount financed.");
    if (taxesParsed === null) reasons.push("Enter taxes.");
    if (feesParsed === null) reasons.push("Enter fees.");
    if (!tradePayoffConfirmed || tradePayoffEffective === null)
      reasons.push(
        "Confirm trade payoff (enter amount or check 'No trade payoff').",
      );
    return reasons;
  }, [
    salePriceParsed,
    aprParsed,
    termMonthsParsed,
    monthlyPaymentParsed,
    amountFinancedParsed,
    taxesParsed,
    feesParsed,
    tradePayoffConfirmed,
    tradePayoffEffective,
  ]);

  // Non-blocking consistency warning per D5: trade_payoff > 0 with
  // trade_allowance == 0 is obviously contradictory (a trade being
  // paid off should carry an allowance). NOT full desking math —
  // cross-state tax treatment variability puts that out of M33 scope.
  const consistencyWarning = useMemo(() => {
    const payoffNum =
      tradePayoffEffective !== null ? Number(tradePayoffEffective) : null;
    const allowanceNum =
      tradeAllowanceParsed !== null ? Number(tradeAllowanceParsed) : null;
    if (
      payoffNum !== null &&
      payoffNum > 0 &&
      allowanceNum !== null &&
      allowanceNum === 0
    ) {
      return "Trade payoff entered without a trade allowance — usually a trade being paid off carries an allowance. Confirm before submitting.";
    }
    return null;
  }, [tradePayoffEffective, tradeAllowanceParsed]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (missingReasons.length > 0) {
      // Belt over the disabled attribute — refuse submit even if
      // native browser bypasses the disabled state.
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload: CreateDealStructureRequest = {
        credit_application_id: creditApplicationId,
        vehicle_stock: vehicle.stock_number,
        sale_price: salePriceParsed!,
        amount_financed: amountFinancedParsed!,
        apr: aprParsed!,
        term_months: termMonthsParsed!,
        monthly_payment: monthlyPaymentParsed!,
        // Optional decimals — send explicit value when the operator
        // provided one; omit when blank (backend defaults apply only
        // for legitimately-absent fields, e.g. back_end_products).
        // We never send `taxes` / `fees` / `trade_payoff` /
        // `amount_financed` as silent 0 because the submit gate
        // blocks that above.
        taxes: taxesParsed!,
        fees: feesParsed!,
        trade_payoff: tradePayoffEffective!,
      };
      if (downPaymentParsed !== null) {
        payload.down_payment = downPaymentParsed;
      }
      if (tradeAllowanceParsed !== null) {
        payload.trade_allowance = tradeAllowanceParsed;
      }
      const deal = await submit(payload);
      onCreated(deal);
    } catch (err) {
      setError(humanizeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  const submitDisabled = submitting || missingReasons.length > 0;

  const salePriceAffordance = fieldAffordance(
    terms.vehicle_price,
    salePrice.raw,
    salePrice.touched,
  );
  const downPaymentAffordance = fieldAffordance(
    terms.down_payment,
    downPayment.raw,
    downPayment.touched,
  );
  const tradeAllowanceAffordance = fieldAffordance(
    terms.trade_allowance,
    tradeAllowance.raw,
    tradeAllowance.touched,
  );
  const aprAffordance = fieldAffordance(
    terms.apr_target,
    apr.raw,
    apr.touched,
  );
  const termAffordance = fieldAffordance(
    terms.term_months_target != null
      ? String(terms.term_months_target)
      : "",
    termMonths.raw,
    termMonths.touched,
  );
  const monthlyPaymentAffordance = fieldAffordance(
    terms.monthly_payment_target,
    monthlyPayment.raw,
    monthlyPayment.touched,
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-md border border-slate-200 bg-white p-4"
      data-testid="deal-structure-form"
    >
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold">
            Start proposed deal structure
          </h2>
          <p className="text-xs text-muted-foreground">
            Confirm the sales-side targets and enter the F&amp;I
            proposed structure values. A lender submission has not
            yet been created — every value on this form is a proposal.
          </p>
        </div>
        {onCancel ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onCancel}
            data-testid="deal-structure-form-cancel"
          >
            Cancel
          </Button>
        ) : null}
      </div>

      {/* Section 1 — Vehicle (read-only) */}
      <section data-testid="deal-structure-form-vehicle-section">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Vehicle
        </h3>
        <div className="text-sm">
          {vehicle.year} {vehicle.make} {vehicle.model} — Stock #
          <span
            data-testid="deal-structure-form-vehicle-stock"
            className="font-medium"
          >
            {vehicle.stock_number}
          </span>
        </div>
      </section>

      {/* Section 2 — Sales-side targets (prepopulated; editable) */}
      <section data-testid="deal-structure-form-targets-section">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Sales-side targets (confirm or revise)
        </h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block">
              Sale price
              {affordanceBadge(salePriceAffordance)}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              data-testid="deal-structure-form-field-sale-price"
              value={salePrice.raw}
              onChange={(e) =>
                setSalePrice({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block">
              Down payment
              {affordanceBadge(downPaymentAffordance)}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              data-testid="deal-structure-form-field-down-payment"
              value={downPayment.raw}
              onChange={(e) =>
                setDownPayment({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block">
              Trade allowance
              {affordanceBadge(tradeAllowanceAffordance)}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              data-testid="deal-structure-form-field-trade-allowance"
              value={tradeAllowance.raw}
              onChange={(e) =>
                setTradeAllowance({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block">
              Proposed APR (%)
              {affordanceBadge(aprAffordance)}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              data-testid="deal-structure-form-field-apr"
              value={apr.raw}
              onChange={(e) =>
                setApr({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block">
              Proposed term (months)
              {affordanceBadge(termAffordance)}
            </span>
            <Input
              type="text"
              inputMode="numeric"
              data-testid="deal-structure-form-field-term-months"
              value={termMonths.raw}
              onChange={(e) =>
                setTermMonths({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block">
              Proposed monthly payment
              {affordanceBadge(monthlyPaymentAffordance)}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              data-testid="deal-structure-form-field-monthly-payment"
              value={monthlyPayment.raw}
              onChange={(e) =>
                setMonthlyPayment({ raw: e.target.value, touched: true })
              }
            />
          </label>
        </div>
      </section>

      {/* Section 3 — F&I proposed structure values (blank on load) */}
      <section data-testid="deal-structure-form-fandi-section">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          F&amp;I proposed structure values (explicit entry required)
        </h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="text-sm">
            <span className="mb-1 block">
              Amount financed
              {affordanceBadge(
                amountFinanced.raw.trim() ? "proposed" : "blank-required",
              )}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              placeholder="F&I entry — no default"
              data-testid="deal-structure-form-field-amount-financed"
              value={amountFinanced.raw}
              onChange={(e) =>
                setAmountFinanced({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block">
              Taxes
              {affordanceBadge(
                taxes.raw.trim() ? "proposed" : "blank-required",
              )}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              placeholder="F&I entry — no default"
              data-testid="deal-structure-form-field-taxes"
              value={taxes.raw}
              onChange={(e) =>
                setTaxes({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block">
              Fees
              {affordanceBadge(
                fees.raw.trim() ? "proposed" : "blank-required",
              )}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              placeholder="F&I entry — no default"
              data-testid="deal-structure-form-field-fees"
              value={fees.raw}
              onChange={(e) =>
                setFees({ raw: e.target.value, touched: true })
              }
            />
          </label>
          <div className="text-sm">
            <span className="mb-1 block">
              Trade payoff
              {affordanceBadge(
                noTradePayoff
                  ? "proposed"
                  : tradePayoff.raw.trim()
                  ? "proposed"
                  : "blank-required",
              )}
            </span>
            <Input
              type="text"
              inputMode="decimal"
              placeholder={
                noTradePayoff
                  ? "0.00 (No trade payoff)"
                  : "F&I entry — no default"
              }
              data-testid="deal-structure-form-field-trade-payoff"
              value={noTradePayoff ? "0.00" : tradePayoff.raw}
              disabled={noTradePayoff}
              onChange={(e) =>
                setTradePayoff({ raw: e.target.value, touched: true })
              }
            />
            <label className="mt-1 flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                data-testid="deal-structure-form-field-no-trade-payoff"
                checked={noTradePayoff}
                onChange={(e) => {
                  setNoTradePayoff(e.target.checked);
                  if (e.target.checked) {
                    setTradePayoff({ raw: "", touched: false });
                  }
                }}
              />
              <span>No trade payoff</span>
            </label>
          </div>
        </div>
      </section>

      {consistencyWarning ? (
        <div
          role="alert"
          data-testid="deal-structure-form-consistency-warning"
          className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800"
        >
          {consistencyWarning}
        </div>
      ) : null}

      {missingReasons.length > 0 ? (
        <ul
          data-testid="deal-structure-form-missing-reasons"
          className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground"
        >
          {missingReasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="text-sm text-destructive"
          data-testid="deal-structure-form-error"
        >
          {error}
        </p>
      ) : null}

      <div className="flex justify-end gap-2">
        <Button
          type="submit"
          disabled={submitDisabled}
          data-testid="deal-structure-form-submit"
        >
          {submitting
            ? "Creating structure…"
            : "Create proposed structure"}
        </Button>
      </div>
    </form>
  );
}
