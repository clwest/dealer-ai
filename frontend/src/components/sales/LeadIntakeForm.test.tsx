// Milestone 24 · Increment 1 (SESSION_181) — LeadIntakeForm tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/authFetch";
import type { LeadProjection } from "@/lib/salesApi";
import { LeadIntakeForm } from "./LeadIntakeForm";

function makeLead(overrides: Partial<LeadProjection> = {}): LeadProjection {
  return {
    id: 1,
    name: "Alice Buyer",
    phone: "555-0100",
    email: "alice@example.com",
    channel: "walk_in",
    referrer_id: null,
    dealership_id: 1,
    created_at: "2026-08-03T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("LeadIntakeForm", () => {
  it("submits with the entered fields and calls onCreated", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValue(makeLead({ id: 42, name: "Bob Buyer" }));
    const onCreated = vi.fn();
    render(
      <LeadIntakeForm
        channel="walk_in"
        onSubmit={onSubmit}
        onCreated={onCreated}
      />,
    );

    await userEvent.type(
      screen.getByTestId("lead-intake-walk_in-name"),
      "Bob Buyer",
    );
    await userEvent.type(
      screen.getByTestId("lead-intake-walk_in-phone"),
      "555-0100",
    );
    await userEvent.click(screen.getByTestId("lead-intake-walk_in-submit"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Bob Buyer",
          phone: "555-0100",
        }),
      );
    });
    expect(onCreated).toHaveBeenCalledWith(
      expect.objectContaining({ id: 42, name: "Bob Buyer" }),
    );
  });

  it("blocks submit when name is missing", async () => {
    const onSubmit = vi.fn();
    render(
      <LeadIntakeForm
        channel="walk_in"
        onSubmit={onSubmit}
        onCreated={vi.fn()}
      />,
    );

    // Type only in phone; leave name empty.
    await userEvent.type(
      screen.getByTestId("lead-intake-walk_in-phone"),
      "555-0100",
    );
    // Native `required` on the name field means the submit event
    // won't fire; assert onSubmit was never called and no lead was
    // created (avoids relying on the humanized error path which
    // requires the submit event to fire first).
    await userEvent.click(screen.getByTestId("lead-intake-walk_in-submit"));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sends undefined for empty optional fields (not empty strings)", async () => {
    const onSubmit = vi.fn().mockResolvedValue(makeLead());
    render(
      <LeadIntakeForm
        channel="phone"
        onSubmit={onSubmit}
        onCreated={vi.fn()}
      />,
    );

    await userEvent.type(
      screen.getByTestId("lead-intake-phone-name"),
      "Carol Caller",
    );
    await userEvent.click(screen.getByTestId("lead-intake-phone-submit"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Carol Caller",
          phone: undefined,
          email: undefined,
          notes: undefined,
          target_monthly_payment: undefined,
          down_payment: undefined,
          trade_in: undefined,
          credit_range: undefined,
          urgency: undefined,
        }),
      );
    });
  });

  it("trims whitespace from name before submitting", async () => {
    const onSubmit = vi.fn().mockResolvedValue(makeLead());
    render(
      <LeadIntakeForm
        channel="walk_in"
        onSubmit={onSubmit}
        onCreated={vi.fn()}
      />,
    );

    await userEvent.type(
      screen.getByTestId("lead-intake-walk_in-name"),
      "  Dave Driver  ",
    );
    await userEvent.click(screen.getByTestId("lead-intake-walk_in-submit"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Dave Driver" }),
      );
    });
  });

  it("surfaces a backend 400 as a human-readable error", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new ApiError(400, "bad"));
    render(
      <LeadIntakeForm
        channel="phone"
        onSubmit={onSubmit}
        onCreated={vi.fn()}
      />,
    );

    await userEvent.type(
      screen.getByTestId("lead-intake-phone-name"),
      "Ellie",
    );
    await userEvent.click(screen.getByTestId("lead-intake-phone-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("lead-intake-phone-error").textContent).toContain(
        "Invalid intake fields",
      );
    });
  });

  it("surfaces a referral 404 as 'Referring customer not found'", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new ApiError(404, "not found"));
    render(
      <LeadIntakeForm
        channel="referral"
        onSubmit={onSubmit}
        onCreated={vi.fn()}
      />,
    );

    await userEvent.type(
      screen.getByTestId("lead-intake-referral-name"),
      "Frank",
    );
    await userEvent.click(screen.getByTestId("lead-intake-referral-submit"));

    await waitFor(() => {
      expect(
        screen.getByTestId("lead-intake-referral-error").textContent,
      ).toContain("Referring customer not found");
    });
  });

  it("resets fields after successful submit", async () => {
    const onSubmit = vi.fn().mockResolvedValue(makeLead());
    render(
      <LeadIntakeForm
        channel="walk_in"
        onSubmit={onSubmit}
        onCreated={vi.fn()}
      />,
    );

    const nameInput = screen.getByTestId(
      "lead-intake-walk_in-name",
    ) as HTMLInputElement;
    const phoneInput = screen.getByTestId(
      "lead-intake-walk_in-phone",
    ) as HTMLInputElement;
    await userEvent.type(nameInput, "Gina");
    await userEvent.type(phoneInput, "555-0199");
    await userEvent.click(screen.getByTestId("lead-intake-walk_in-submit"));

    await waitFor(() => {
      expect(nameInput.value).toBe("");
      expect(phoneInput.value).toBe("");
    });
  });

  it("renders the extras slot for referral", () => {
    render(
      <LeadIntakeForm
        channel="referral"
        onSubmit={vi.fn()}
        onCreated={vi.fn()}
        extras={<div data-testid="test-extras-slot">picker goes here</div>}
      />,
    );
    expect(screen.getByTestId("test-extras-slot")).toBeTruthy();
  });
});
