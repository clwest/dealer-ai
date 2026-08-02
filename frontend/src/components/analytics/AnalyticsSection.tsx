// Milestone 8 · Increment 5 (SESSION_098) — analytics section shell.
//
// Shared loading/error wrapper around every dashboard aggregation.
// Preserves the "Loading…" / "Access denied" / "Failed to load"
// language consistently across tabs so the operator sees the same
// language regardless of which endpoint hiccuped.

import { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export type LoadState = "loading" | "ready" | "error" | "forbidden";

interface AnalyticsSectionProps {
  title: string;
  description?: string;
  loadState: LoadState;
  errorMessage?: string | null;
  children: ReactNode;
}

export function AnalyticsSection({
  title,
  description,
  loadState,
  errorMessage,
  children,
}: AnalyticsSectionProps) {
  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? (
          <CardDescription>{description}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent>
        {loadState === "loading" ? (
          <p className="text-sm text-muted-foreground" role="status">
            Loading…
          </p>
        ) : loadState === "forbidden" ? (
          <p className="text-sm text-destructive" role="alert">
            Access denied. This dashboard is restricted to recon
            managers, sales managers, and dealer owners.
          </p>
        ) : loadState === "error" ? (
          <p className="text-sm text-destructive" role="alert">
            Failed to load: {errorMessage ?? "unknown error"}
          </p>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}

// Common "empty aggregation" placeholder — shown when a verb
// returns an empty rows array / zero-count report. Kept out of
// AnalyticsSection because "empty" is a data state (ready + zero
// rows) distinct from "loading" / "error" / "forbidden."
export function EmptyRows({ label = "No data in this window." }: { label?: string }) {
  return (
    <p className="text-sm text-muted-foreground" role="status">
      {label}
    </p>
  );
}
