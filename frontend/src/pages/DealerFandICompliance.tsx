// Milestone 10 · Increment 7 (SESSION_112) — F&I per-deal compliance audit.
//
// Second tab of the two-tab MVP per §1.8.d Option A. Renders the
// full deal-jacket aggregate for one Contract, with mark-timestamp
// buttons for the seven FINANCE §6 compliance concerns.
//
// Consumes:
//   GET  /admin/deal-jackets/<contract_pk>/     — aggregate view
//   POST /admin/compliance-records/              — create if missing
//   PATCH /admin/compliance-records/<pk>/        — mark timestamps
//
// Role gating: backend enforces
// IsFinanceManagerOrOwnerAtActiveDealership.

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  createCompliance,
  fetchDealJacket,
  updateCompliance,
  type DealJacket,
  type UpdateComplianceRequest,
} from "@/lib/fAndIApi";

interface ConcernRow {
  label: string;
  field: keyof UpdateComplianceRequest;
  timestampKey:
    | "reg_z_disclosed_at"
    | "ofac_checked_at"
    | "red_flags_reviewed_at"
    | "privacy_notice_delivered_at"
    | "safeguards_audit_at"
    | "adverse_action_sent_at";
}

const CONCERNS: ConcernRow[] = [
  {
    label: "Reg Z disclosures reviewed",
    field: "reg_z_disclosed_at",
    timestampKey: "reg_z_disclosed_at",
  },
  {
    label: "OFAC screen completed",
    field: "ofac_checked_at",
    timestampKey: "ofac_checked_at",
  },
  {
    label: "Red Flags reviewed",
    field: "red_flags_reviewed_at",
    timestampKey: "red_flags_reviewed_at",
  },
  {
    label: "Privacy notice delivered",
    field: "privacy_notice_delivered_at",
    timestampKey: "privacy_notice_delivered_at",
  },
  {
    label: "Safeguards audit",
    field: "safeguards_audit_at",
    timestampKey: "safeguards_audit_at",
  },
  {
    label: "Adverse action notice sent",
    field: "adverse_action_sent_at",
    timestampKey: "adverse_action_sent_at",
  },
];

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export default function DealerFandICompliance() {
  const { contract_id } = useParams<{ contract_id: string }>();
  const contractPk = contract_id ? parseInt(contract_id, 10) : NaN;

  const [jacket, setJacket] = useState<DealJacket | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (Number.isNaN(contractPk)) {
      setErrorMessage("Invalid contract id.");
      setLoadState("error");
      return;
    }
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const result = await fetchDealJacket(contractPk);
      setJacket(result);
      setLoadState("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load deal jacket.",
      );
      setLoadState("error");
    }
  }, [contractPk]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreateCompliance = useCallback(async () => {
    if (!jacket) return;
    setBusy(true);
    try {
      await createCompliance({ contract_id: jacket.contract.id });
      await load();
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Failed to create compliance record.",
      );
    } finally {
      setBusy(false);
    }
  }, [jacket, load]);

  const handleMarkConcern = useCallback(
    async (concern: ConcernRow) => {
      if (!jacket?.compliance) return;
      setBusy(true);
      try {
        const now = new Date().toISOString();
        await updateCompliance(jacket.compliance.id, {
          [concern.field]: now,
        } as UpdateComplianceRequest);
        await load();
      } catch (err) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Failed to update compliance record.",
        );
      } finally {
        setBusy(false);
      }
    },
    [jacket, load],
  );

  if (loadState === "loading") {
    return <p className="p-6 text-muted-foreground">Loading deal jacket…</p>;
  }
  if (loadState === "error") {
    return (
      <div className="p-6">
        <p role="alert" className="text-destructive">
          {errorMessage}
        </p>
        <div className="mt-4">
          <Button variant="outline" asChild>
            <Link to="/dealer-ai-f-and-i">← Back to deals</Link>
          </Button>
        </div>
      </div>
    );
  }
  if (!jacket) return null;

  const { contract, compliance, funding, stipulations, chargebacks } = jacket;

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <Button variant="outline" size="sm" asChild className="mb-2">
          <Link to="/dealer-ai-f-and-i">← Back to deals</Link>
        </Button>
        <h1 className="text-2xl font-semibold">
          Deal Jacket — Contract #{contract.id}
        </h1>
        <p className="text-sm text-muted-foreground">
          {contract.contract_type.toUpperCase()} · {contract.state}
        </p>
      </div>

      {compliance === null && (
        <Card>
          <CardHeader>
            <CardTitle>Compliance record not started</CardTitle>
            <CardDescription>
              Create one to track Reg Z, OFAC, Red Flags, Privacy,
              Safeguards, Adverse Action, and retention timestamps.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleCreateCompliance} disabled={busy}>
              {busy ? "Creating…" : "Start compliance record"}
            </Button>
          </CardContent>
        </Card>
      )}

      {compliance !== null && (
        <Card>
          <CardHeader>
            <CardTitle>Compliance concerns</CardTitle>
            <CardDescription>
              FINANCE §6.1-§6.9. Mark each concern as reviewed —
              timestamp is server-populated.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2">Concern</th>
                  <th className="pb-2">Timestamp</th>
                  <th className="pb-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {CONCERNS.map((concern) => {
                  const ts = compliance[concern.timestampKey];
                  return (
                    <tr
                      key={concern.field}
                      className="border-b last:border-0"
                    >
                      <td className="py-2">{concern.label}</td>
                      <td className="py-2">{formatTimestamp(ts)}</td>
                      <td className="py-2 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleMarkConcern(concern)}
                          disabled={busy}
                        >
                          {ts ? "Re-mark" : "Mark now"}
                        </Button>
                      </td>
                    </tr>
                  );
                })}
                <tr>
                  <td className="pt-3">Retention window</td>
                  <td className="pt-3" colSpan={2}>
                    {formatTimestamp(compliance.retention_expires_at)}
                  </td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {funding && (
        <Card>
          <CardHeader>
            <CardTitle>Funding</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">
              State: <span className="font-medium">{funding.state}</span>
              {funding.funding_amount &&
                ` · $${funding.funding_amount}`}
              {funding.funded_at &&
                ` · funded ${formatTimestamp(funding.funded_at)}`}
            </p>
          </CardContent>
        </Card>
      )}

      {stipulations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Stipulations ({stipulations.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {stipulations.map((s) => (
                <li key={s.id}>
                  <span className="font-medium">{s.stip_type}</span>
                  {" · "}
                  <span className="text-muted-foreground">{s.state}</span>
                  {s.evidence_url && (
                    <>
                      {" · "}
                      <a
                        href={s.evidence_url}
                        className="text-primary underline"
                        target="_blank"
                        rel="noreferrer"
                      >
                        evidence
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {chargebacks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Chargebacks ({chargebacks.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {chargebacks.map((c) => (
                <li key={c.id}>
                  <span className="font-medium">{c.chargeback_type}</span>
                  {" · "}
                  {c.chargeback_date} · ${c.chargeback_amount}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
