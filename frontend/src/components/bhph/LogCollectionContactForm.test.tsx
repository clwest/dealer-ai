// Milestone 21 · Increment 2 (SESSION_168) — LogCollectionContactForm tests.

import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/bhphApi", async () => {
  const actual = await vi.importActual<typeof import("@/lib/bhphApi")>(
    "@/lib/bhphApi",
  );
  return {
    ...actual,
    logCollectionContact: vi.fn(),
  };
});

import { ApiError } from "@/lib/authFetch";
import {
  logCollectionContact,
  type CollectionContactProjection,
} from "@/lib/bhphApi";
import { LogCollectionContactForm } from "./LogCollectionContactForm";

function makeContact(
  overrides: Partial<CollectionContactProjection> = {},
): CollectionContactProjection {
  return {
    id: 10,
    note_id: 100,
    dealership_id: 1,
    contacted_at: "2026-08-03T10:00:00Z",
    contacted_by_user_id: null,
    channel: "phone",
    outcome: "contact_made",
    notes: "",
    created_at: "2026-08-03T10:00:00Z",
    updated_at: "2026-08-03T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("LogCollectionContactForm", () => {
  it("submits and calls onLogged with the returned contact", async () => {
    vi.mocked(logCollectionContact).mockResolvedValue({
      collection_contact: makeContact({ id: 77, outcome: "left_message" }),
    });
    const onLogged = vi.fn();
    render(<LogCollectionContactForm notePk={100} onLogged={onLogged} />);

    await userEvent.selectOptions(
      screen.getByTestId("log-contact-channel"),
      "sms",
    );
    await userEvent.selectOptions(
      screen.getByTestId("log-contact-outcome"),
      "left_message",
    );
    await userEvent.type(
      screen.getByTestId("log-contact-notes"),
      "text sent",
    );
    await userEvent.click(screen.getByTestId("log-contact-submit"));

    await waitFor(() => {
      expect(logCollectionContact).toHaveBeenCalledWith(
        100,
        expect.objectContaining({
          channel: "sms",
          outcome: "left_message",
          notes: "text sent",
        }),
      );
    });
    expect(onLogged).toHaveBeenCalledWith(
      expect.objectContaining({ id: 77 }),
    );
  });

  it("surfaces a 400 as a human-readable error", async () => {
    vi.mocked(logCollectionContact).mockRejectedValue(
      new ApiError(400, "bad"),
    );
    const onLogged = vi.fn();
    render(<LogCollectionContactForm notePk={100} onLogged={onLogged} />);

    await userEvent.click(screen.getByTestId("log-contact-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("log-contact-error").textContent).toMatch(
        /invalid contact/i,
      );
    });
    expect(onLogged).not.toHaveBeenCalled();
  });
});
