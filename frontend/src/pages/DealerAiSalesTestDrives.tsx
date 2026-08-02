// Milestone 11 · Increment 6 (SESSION_119) — test-drive log.
//
// Consumes GET /admin/test-drives/list/ added in M11.6. Read-only view
// at M11.6 — creation happens via the dedicated form on the M11.2
// backend surface (deferred to a follow-on UX pass).

import { useCallback, useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { listTestDrives, type TestDriveProjection } from "@/lib/salesApi";

export default function DealerAiSalesTestDrives() {
  const [drives, setDrives] = useState<TestDriveProjection[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const res = await listTestDrives();
      setDrives(res.results);
      setLoadState("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load test drives.",
      );
      setLoadState("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Test drives</h1>
        <p className="text-sm text-muted-foreground">
          Every test drive across the sales floor. Route notes and
          objections are captured at drive time.
        </p>
      </div>

      {loadState === "loading" && (
        <p className="text-muted-foreground">Loading test drives…</p>
      )}
      {loadState === "error" && (
        <p role="alert" className="text-destructive">
          {errorMessage}
        </p>
      )}
      {loadState === "ready" && drives.length === 0 && (
        <Card>
          <CardContent className="py-6 text-center text-muted-foreground">
            No test drives recorded yet.
          </CardContent>
        </Card>
      )}
      {loadState === "ready" && drives.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{drives.length} drives</CardTitle>
            <CardDescription>Most recent first.</CardDescription>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2">Driven at</th>
                  <th className="pb-2">Lead</th>
                  <th className="pb-2">Vehicle</th>
                  <th className="pb-2">Duration</th>
                  <th className="pb-2">Reaction</th>
                  <th className="pb-2">Objections</th>
                </tr>
              </thead>
              <tbody>
                {drives.map((drive) => (
                  <tr key={drive.id} className="border-b last:border-0">
                    <td className="py-2">
                      {new Date(drive.driven_at).toLocaleString()}
                    </td>
                    <td className="py-2">#{drive.lead_id}</td>
                    <td className="py-2">#{drive.vehicle_id}</td>
                    <td className="py-2">
                      {drive.duration_minutes
                        ? `${drive.duration_minutes} min`
                        : "—"}
                    </td>
                    <td className="py-2">{drive.customer_reaction || "—"}</td>
                    <td className="py-2">
                      {drive.objections_captured.length > 0
                        ? drive.objections_captured.join(", ")
                        : "—"}
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
