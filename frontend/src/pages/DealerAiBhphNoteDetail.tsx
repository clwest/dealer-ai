// Milestone 12 · Increment 7 (SESSION_127) — BHPH per-note detail.
// Milestone 21 · Increment 2 (SESSION_168) — write-side attachments.
//
// Composes M12.1–M12.6 read endpoints per §5.f Option C. Each sub-list
// is fetched lazily via its own read endpoint (no bundle endpoint at
// MVP per §0.a M12.7 decision 4).
//
// M21.2 attaches the write-side surface via the components in
// frontend/src/components/bhph/:
//   - RecordPromiseToPayForm + MarkKeptPromiseButton + MarkBrokenPromiseButton
//   - LogCollectionContactForm
//   - InitiateRepossessionForm + MarkRecoveredButton + MarkReIntakedButton
//
// After each write, we optimistically merge the returned projection
// into the corresponding sub-list. The backend is the source of truth
// for aggregate state (e.g. days_past_due, current_bucket); a
// subsequent read of the note detail refreshes those.

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InitiateRepossessionForm } from "@/components/bhph/InitiateRepossessionForm";
import { LogCollectionContactForm } from "@/components/bhph/LogCollectionContactForm";
import {
  MarkBrokenPromiseButton,
  MarkKeptPromiseButton,
} from "@/components/bhph/PromiseRowActions";
import { RecordPromiseToPayForm } from "@/components/bhph/RecordPromiseToPayForm";
import {
  MarkRecoveredButton,
  MarkReIntakedButton,
} from "@/components/bhph/RepossessionRowActions";
import {
  getBhphNote,
  listBhphPayments,
  listBhphPromises,
  listCollectionContacts,
  listRepossessions,
  type BhphNoteDetailResponse,
  type BhphPaymentProjection,
  type BhphPromiseProjection,
  type CollectionContactProjection,
  type RepossessionProjection,
} from "@/lib/bhphApi";


function formatMoney(raw: string): string {
  const amount = Number(raw);
  if (Number.isNaN(amount)) return `$${raw}`;
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}


function mergeById<T extends { id: number }>(prev: T[], next: T): T[] {
  const idx = prev.findIndex((row) => row.id === next.id);
  if (idx === -1) return [...prev, next];
  const copy = prev.slice();
  copy[idx] = next;
  return copy;
}


export default function DealerAiBhphNoteDetail() {
  const { pk } = useParams<{ pk: string }>();
  const notePk = pk ? Number(pk) : NaN;
  const [detail, setDetail] = useState<BhphNoteDetailResponse | null>(null);
  const [payments, setPayments] = useState<BhphPaymentProjection[]>([]);
  const [promises, setPromises] = useState<BhphPromiseProjection[]>([]);
  const [contacts, setContacts] = useState<CollectionContactProjection[]>([]);
  const [repos, setRepos] = useState<RepossessionProjection[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (Number.isNaN(notePk)) {
      setLoadState("error");
      setErrorMessage("Invalid note ID.");
      return;
    }
    let cancelled = false;
    async function load() {
      setLoadState("loading");
      setErrorMessage(null);
      try {
        const [detailRes, paymentsRes, promisesRes, contactsRes, reposRes] =
          await Promise.all([
            getBhphNote(notePk),
            listBhphPayments(notePk),
            listBhphPromises(notePk),
            listCollectionContacts(notePk),
            listRepossessions(notePk),
          ]);
        if (cancelled) return;
        setDetail(detailRes);
        setPayments(paymentsRes.results);
        setPromises(promisesRes.results);
        setContacts(contactsRes.results);
        setRepos(reposRes.results);
        setLoadState("ready");
      } catch (err) {
        if (cancelled) return;
        setErrorMessage(
          err instanceof Error ? err.message : "Failed to load note.",
        );
        setLoadState("error");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [notePk]);

  if (loadState === "loading") {
    return <p className="text-sm text-muted-foreground">Loading note…</p>;
  }
  if (loadState === "error") {
    return <p className="text-sm text-destructive">{errorMessage}</p>;
  }
  if (!detail) return null;
  const { bhph_note: note, payment_schedule: schedule } = detail;

  return (
    <div className="flex flex-col gap-6" data-testid="bhph-note-detail">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          BHPH Note #{note.id}
        </h1>
        <p className="text-sm text-muted-foreground">
          {formatMoney(note.principal_financed)} @ {note.apr}% ·{" "}
          {note.term_weeks} weeks · {note.payment_frequency}
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Loan terms</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">Payment</dt>
              <dd>{formatMoney(note.payment_amount)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">First due</dt>
              <dd>{note.first_payment_due}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Bucket</dt>
              <dd>{note.current_bucket}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Days past due</dt>
              <dd>{note.days_past_due}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Payments ({payments.length})</CardTitle>
          <CardDescription>
            {schedule.length} scheduled installments.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {payments.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No payments recorded yet.
            </p>
          ) : (
            <ul className="text-sm">
              {payments.map((p) => (
                <li key={p.id} className="py-1">
                  {p.paid_at} · {formatMoney(p.amount)} · {p.method} ·
                  int {formatMoney(p.applied_to_interest)} · prin{" "}
                  {formatMoney(p.applied_to_principal)}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card data-testid="promises-card">
        <CardHeader>
          <CardTitle>Promises ({promises.length})</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {promises.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No promises on file.
            </p>
          ) : (
            <ul className="flex flex-col gap-2 text-sm">
              {promises.map((p) => (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded border border-border/60 px-3 py-2"
                  data-testid={`promise-row-${p.id}`}
                >
                  <span>
                    {p.promised_at} · {formatMoney(p.promised_amount)} ·{" "}
                    {p.promised_reason} ·{" "}
                    <strong data-testid={`promise-state-${p.id}`}>
                      {p.state}
                    </strong>
                  </span>
                  <span className="flex items-center gap-2">
                    <MarkKeptPromiseButton
                      notePk={notePk}
                      promise={p}
                      onMarked={(next) =>
                        setPromises((prev) => mergeById(prev, next))
                      }
                    />
                    <MarkBrokenPromiseButton
                      promise={p}
                      onMarked={(next) =>
                        setPromises((prev) => mergeById(prev, next))
                      }
                    />
                  </span>
                </li>
              ))}
            </ul>
          )}
          <RecordPromiseToPayForm
            notePk={notePk}
            onRecorded={(promise) =>
              setPromises((prev) => mergeById(prev, promise))
            }
          />
        </CardContent>
      </Card>

      <Card data-testid="contacts-card">
        <CardHeader>
          <CardTitle>Contacts ({contacts.length})</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {contacts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No collection contacts logged.
            </p>
          ) : (
            <ul className="text-sm">
              {contacts.map((c) => (
                <li
                  key={c.id}
                  className="py-1"
                  data-testid={`contact-row-${c.id}`}
                >
                  {c.contacted_at} · {c.channel} · {c.outcome}
                </li>
              ))}
            </ul>
          )}
          <LogCollectionContactForm
            notePk={notePk}
            onLogged={(contact) =>
              setContacts((prev) => mergeById(prev, contact))
            }
          />
        </CardContent>
      </Card>

      <Card data-testid="repossessions-card">
        <CardHeader>
          <CardTitle>Repossessions ({repos.length})</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {repos.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No repossessions on file.
            </p>
          ) : (
            <ul className="flex flex-col gap-2 text-sm">
              {repos.map((r) => (
                <li
                  key={r.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded border border-border/60 px-3 py-2"
                  data-testid={`repo-row-${r.id}`}
                >
                  <span>
                    {r.ordered_at} · {r.agent_name} ·{" "}
                    <strong data-testid={`repo-state-${r.id}`}>
                      {r.state}
                    </strong>
                  </span>
                  <span className="flex items-center gap-2">
                    <MarkRecoveredButton
                      repossession={r}
                      onMarked={(next) =>
                        setRepos((prev) => mergeById(prev, next))
                      }
                    />
                    <MarkReIntakedButton
                      repossession={r}
                      onMarked={(next) =>
                        setRepos((prev) => mergeById(prev, next))
                      }
                    />
                  </span>
                </li>
              ))}
            </ul>
          )}
          <InitiateRepossessionForm
            notePk={notePk}
            onInitiated={(repo) =>
              setRepos((prev) => mergeById(prev, repo))
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
