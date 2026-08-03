// Milestone 11 · Increment 6 (SESSION_119) — follow-up task work-queue.
// Milestone 21 · Increment 3 (SESSION_169) — cadence config panel.
//
// Consumes GET /admin/follow-up-tasks/ (M11.4). Default filter "due
// today, pending"; operator can complete / skip inline. Optimistic
// transition updates local state; on error, refetches.
//
// M21.3 attaches the CadenceConfigPanel above the queue table. The
// createCadence / pauseCadence wrappers already existed in
// salesApi.ts since M11.4 but had no component consumers — the
// M21.1 audit flagged both as wrapper-only. The panel gives
// operators a UI path to start a follow-up cadence for a lead and
// to pause an active cadence (by ID, since M11.4 ships no cadence
// list endpoint). A change to cadences triggers a queue reload so
// newly-spawned tasks appear immediately.

import { useCallback, useEffect, useMemo, useState } from "react";

import { CadenceConfigPanel } from "@/components/sales/CadenceConfigPanel";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  completeTask,
  listFollowUpTasks,
  skipTask,
  type FollowUpTaskProjection,
  type FollowUpTaskState,
} from "@/lib/salesApi";

type StateFilter = "" | FollowUpTaskState;

const STATE_OPTIONS: Array<{ value: StateFilter; label: string }> = [
  { value: "", label: "Any state" },
  { value: "pending", label: "Pending" },
  { value: "completed", label: "Completed" },
  { value: "skipped", label: "Skipped" },
];

export default function DealerAiSalesFollowUps() {
  const [tasks, setTasks] = useState<FollowUpTaskProjection[]>([]);
  const [stateFilter, setStateFilter] = useState<StateFilter>("pending");
  const [dueTodayOnly, setDueTodayOnly] = useState(true);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [busyTaskId, setBusyTaskId] = useState<number | null>(null);

  const dueBefore = useMemo(() => {
    if (!dueTodayOnly) return undefined;
    const end = new Date();
    end.setHours(23, 59, 59, 999);
    return end.toISOString();
  }, [dueTodayOnly]);

  const load = useCallback(async () => {
    setLoadState("loading");
    setErrorMessage(null);
    try {
      const res = await listFollowUpTasks({
        state: stateFilter || undefined,
        due_before: dueBefore,
        limit: 100,
      });
      setTasks(res.results);
      setLoadState("ready");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to load tasks.",
      );
      setLoadState("error");
    }
  }, [stateFilter, dueBefore]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleTransition = useCallback(
    async (taskId: number, verb: "complete" | "skip") => {
      setBusyTaskId(taskId);
      try {
        const updated = verb === "complete"
          ? await completeTask(taskId)
          : await skipTask(taskId);
        setTasks((current) =>
          current.map((t) => (t.id === updated.id ? updated : t)),
        );
      } catch (err) {
        setErrorMessage(
          err instanceof Error ? err.message : "Transition failed.",
        );
        void load();
      } finally {
        setBusyTaskId(null);
      }
    },
    [load],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Follow-up work-queue</h1>
        <p className="text-sm text-muted-foreground">
          Scheduled follow-ups across every active cadence. Complete
          or skip inline as you work the queue.
        </p>
      </div>

      <CadenceConfigPanel onChanged={() => void load()} />

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>State + date window.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <label className="flex flex-col text-sm">
              <span className="mb-1 text-muted-foreground">State</span>
              <select
                aria-label="State filter"
                value={stateFilter}
                onChange={(e) =>
                  setStateFilter(e.target.value as StateFilter)
                }
                className="rounded border border-input bg-background px-3 py-2"
              >
                {STATE_OPTIONS.map((opt) => (
                  <option key={opt.value || "any"} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={dueTodayOnly}
                onChange={(e) => setDueTodayOnly(e.target.checked)}
                aria-label="Due today only"
              />
              Due today only
            </label>
          </div>
        </CardContent>
      </Card>

      {loadState === "loading" && (
        <p className="text-muted-foreground">Loading tasks…</p>
      )}
      {loadState === "error" && (
        <p role="alert" className="text-destructive">
          {errorMessage}
        </p>
      )}
      {loadState === "ready" && tasks.length === 0 && (
        <Card>
          <CardContent className="py-6 text-center text-muted-foreground">
            Queue is clear. No tasks match the current filter.
          </CardContent>
        </Card>
      )}
      {loadState === "ready" && tasks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{tasks.length} tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2">Due at</th>
                  <th className="pb-2">Cadence</th>
                  <th className="pb-2">State</th>
                  <th className="pb-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id} className="border-b last:border-0">
                    <td className="py-2">
                      {new Date(task.due_at).toLocaleString()}
                    </td>
                    <td className="py-2">#{task.cadence_id}</td>
                    <td className="py-2">{task.state}</td>
                    <td className="py-2 text-right">
                      {task.state === "pending" ? (
                        <span className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            disabled={busyTaskId === task.id}
                            onClick={() =>
                              handleTransition(task.id, "complete")
                            }
                          >
                            Complete
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busyTaskId === task.id}
                            onClick={() =>
                              handleTransition(task.id, "skip")
                            }
                          >
                            Skip
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
