// Milestone 8 · Increment 5 (SESSION_098) — AnalyticsSection tests.
//
// Locks the four load-states (loading / forbidden / error / ready)
// so the operator-facing language stays consistent as tabs multiply.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnalyticsSection } from "@/components/analytics/AnalyticsSection";

describe("AnalyticsSection", () => {
  it("shows 'Loading…' while loadState=loading", () => {
    render(
      <AnalyticsSection title="Test" loadState="loading">
        <div>child content</div>
      </AnalyticsSection>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(screen.queryByText("child content")).not.toBeInTheDocument();
  });

  it("shows the access-denied message when loadState=forbidden", () => {
    render(
      <AnalyticsSection title="Test" loadState="forbidden">
        <div>child content</div>
      </AnalyticsSection>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      /access denied/i,
    );
    expect(screen.queryByText("child content")).not.toBeInTheDocument();
  });

  it("shows the error message when loadState=error", () => {
    render(
      <AnalyticsSection title="Test" loadState="error" errorMessage="boom">
        <div>child content</div>
      </AnalyticsSection>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });

  it("renders children when loadState=ready", () => {
    render(
      <AnalyticsSection title="Test" loadState="ready">
        <div>child content</div>
      </AnalyticsSection>,
    );
    expect(screen.getByText("child content")).toBeInTheDocument();
    // Neither the loading spinner nor the alert should render.
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
