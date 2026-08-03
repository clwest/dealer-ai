// Milestone 11 · Increment 6 (SESSION_119) — be-back list + transitions.
// Milestone 21 · Increment 3 (SESSION_169) — record-be-back CREATE form.
//
// Consumes GET /admin/be-backs/list/ added in M11.6. Operator can mark
// a promised be-back as returned or no_show inline (matches the
// M11.4 follow-up-queue interaction pattern). The M11.5 no-show
// detector runs at 07:00 daily — operators typically only mark
// no-show manually before the grace period elapses (customer
// called to cancel).
//
// M21.3 attaches the RecordBeBackForm (createBeBack wrapper existed
// in salesApi.ts since M11.6 but had no component consumer — the
// M21.1 audit flagged it as wrapper-only). The form appears above
// the queue table. On successful record the new row is optimistically
// prepended; a subsequent filter change or manual reload picks up
// the true server order.

import { useCallback, useEffect, useState } from "react";

import { RecordBeBackForm } from "@/components/sales/RecordBeBackForm";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  listBeBacks,
  markBeBackNoShow,
  markBeBackReturned,
  type BeBackProjection,
  type BeBackState,
} from "@/lib/salesApi";

type StateFilter = "" | BeBackState;

const STATE_OPTIONS: Array<{ value: StateFilter; label: string }> = [
  { value: "", label: "Any state" },
  { value: "promised", label: "Promised" },
  { value: "returned", label: "Returned" },
  { value: "no_show", label: "No-show" },
];

export default function DealerAiSalesBeBacks() {
  const [beBacks, setBeBacks] = useState<BeBackProjection[]>([]);
  const [stateFilter, setStateFilter] = useState<StateFilter>("promised");
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const res = await listBeBacks({
        state: stateFilter || undefined,
      });
      setBeBacks(res.results);
      setLoadState("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load be-backs.",
      );
      setLoadState("error");
    }
  }, [stateFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleTransition = useCallback(
    async (id: number, verb: "returned" | "no_show") => {
      setBusyId(id);
      try {
        const updated = verb === "returned"
          ? await markBeBackReturned(id)
          : await markBeBackNoShow(id);
        setBeBacks((current) =>
          current.map((bb) => (bb.id === updated.id ? updated : bb)),
        );
      } catch (err) {
        setErrorMessage(
          err instanceof Error ? err.message : "Transition failed.",
        );
        void load();
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Be-backs</h1>
        <p className="text-sm text-muted-foreground">
          Customers who promised to return. The daily 07:00 detector
          auto-flags no-shows after the configured grace period; mark
          manually if the customer cancels ahead of time.
        </p>
      </div>

      <RecordBeBackForm
        onRecorded={(beBack) => {
          // Optimistically prepend so the operator sees the row
          // immediately. If the current filter would exclude the new
          // row (e.g. filter="returned" and new row is "promised"),
          // the next load() call will drop it.
          setBeBacks((current) => [beBack, ...current]);
        }}
      />

      <Card>
        <CardHeader>
          <CardTitle>Filter</CardTitle>
          <CardDescription>State</CardDescription>
        </CardHeader>
        <CardContent>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-muted-foreground">State</span>
            <select
              aria-label="Be-back state filter"
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value as StateFilter)}
              className="rounded border border-input bg-background px-3 py-2"
            >
              {STATE_OPTIONS.map((opt) => (
                <option key={opt.value || "any"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </CardContent>
      </Card>

      {loadState === "loading" && (
        <p className="text-muted-foreground">Loading be-backs…</p>
      )}
      {loadState === "error" && (
        <p role="alert" className="text-destructive">
          {errorMessage}
        </p>
      )}
      {loadState === "ready" && beBacks.length === 0 && (
        <Card>
          <CardContent className="py-6 text-center text-muted-foreground">
            No be-backs match the current filter.
          </CardContent>
        </Card>
      )}
      {loadState === "ready" && beBacks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{beBacks.length} be-backs</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2">Lead</th>
                  <th className="pb-2">Promised at</th>
                  <th className="pb-2">Reason</th>
                  <th className="pb-2">State</th>
                  <th className="pb-2">Returned at</th>
                  <th className="pb-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {beBacks.map((bb) => (
                  <tr key={bb.id} className="border-b last:border-0">
                    <td className="py-2">#{bb.lead_id}</td>
                    <td className="py-2">
                      {new Date(bb.promised_at).toLocaleString()}
                    </td>
                    <td className="py-2">{bb.promised_reason}</td>
                    <td className="py-2">{bb.state}</td>
                    <td className="py-2 text-muted-foreground">
                      {bb.actual_return_at
                        ? new Date(bb.actual_return_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="py-2 text-right">
                      {bb.state === "promised" ? (
                        <span className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            disabled={busyId === bb.id}
                            onClick={() =>
                              handleTransition(bb.id, "returned")
                            }
                          >
                            Returned
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busyId === bb.id}
                            onClick={() =>
                              handleTransition(bb.id, "no_show")
                            }
                          >
                            No-show
                          </Button>
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
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
