// Milestone 19 · Increment 4 (SESSION_157) — pilot onboarding section tests.
//
// Covers the pilot admin surface embedded in DealerAdmin per §0.a
// M19.4 decision 2:
//
// - Fetch on mount → renders list + shows empty state.
// - Create form validation + successful create refreshes list.
// - Slug-collision 409 surfaces friendly error.
// - Checklist stepper displays ordered steps + advances one.
// - Readiness precondition 409 surfaces friendly error.
// - CSV upload multipart body + rejected-rows projection surfaces.
// - Terminate flow requires confirm click.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>(
    "@/lib/api",
  );
  return {
    ...actual,
    fetchPilotDealerships: vi.fn(),
    createPilotDealership: vi.fn(),
    advancePilotChecklistStep: vi.fn(),
    importPilotInventory: vi.fn(),
    terminatePilotDealership: vi.fn(),
  };
});

import {
  advancePilotChecklistStep,
  createPilotDealership,
  fetchPilotDealerships,
  importPilotInventory,
  terminatePilotDealership,
  type PilotWithChecklistDTO,
} from "@/lib/api";
import { ApiError } from "@/lib/authFetch";
import PilotOnboardingSection from "@/components/pilots/PilotOnboardingSection";


const STEP_ORDER = [
  "dealership_created",
  "profile_configured",
  "owner_user_added",
  "staff_users_added",
  "inventory_imported",
  "capabilities_enabled",
  "readiness_confirmed",
];


function makePilot(overrides: Partial<PilotWithChecklistDTO> = {}): PilotWithChecklistDTO {
  return {
    dealership: {
      id: 1,
      slug: "acme-motors",
      name: "Acme Motors",
      is_pilot: true,
      is_demo: false,
      outbound_enabled: false,
      terminated_at: null,
      termination_reason: "",
      created_at: "2026-08-02T00:00:00Z",
    },
    checklist: {
      id: 10,
      dealership_id: 1,
      is_ready: false,
      steps: STEP_ORDER.map((slug) => ({
        step_slug: slug,
        completed_at: slug === "dealership_created" ? "2026-08-02T00:00:00Z" : null,
        completed_by_username: null,
        notes: "",
      })),
    },
    ...overrides,
  };
}


describe("PilotOnboardingSection", () => {
  beforeEach(() => {
    vi.mocked(fetchPilotDealerships).mockReset();
    vi.mocked(createPilotDealership).mockReset();
    vi.mocked(advancePilotChecklistStep).mockReset();
    vi.mocked(importPilotInventory).mockReset();
    vi.mocked(terminatePilotDealership).mockReset();
  });

  it("shows empty state when no pilots", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({ pilots: [] });
    render(<PilotOnboardingSection />);
    await waitFor(() => {
      expect(screen.getByTestId("pilot-list-empty")).toBeInTheDocument();
    });
  });

  it("renders each pilot with ready badge", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [
        makePilot(),
        makePilot({
          dealership: {
            ...makePilot().dealership,
            slug: "second-pilot",
            name: "Second Pilot",
          },
          checklist: {
            ...makePilot().checklist!,
            is_ready: true,
          },
        }),
      ],
    });
    render(<PilotOnboardingSection />);
    await waitFor(() => {
      expect(screen.getByTestId("pilot-row-acme-motors")).toBeInTheDocument();
    });
    expect(screen.getByTestId("pilot-row-second-pilot")).toBeInTheDocument();
    const secondRow = screen.getByTestId("pilot-row-second-pilot");
    expect(within(secondRow).getByText("Ready")).toBeInTheDocument();
  });

  it("disables submit until all create fields are populated", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({ pilots: [] });
    render(<PilotOnboardingSection />);
    await waitFor(() => {
      expect(screen.getByTestId("pilot-list-empty")).toBeInTheDocument();
    });
    const submit = screen.getByTestId("pilot-create-submit") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    await userEvent.type(screen.getByTestId("pilot-create-slug"), "acme");
    await userEvent.type(screen.getByTestId("pilot-create-name"), "Acme");
    await userEvent.type(screen.getByTestId("pilot-create-owner"), "owner");
    expect(submit.disabled).toBe(false);
  });

  it("calls createPilotDealership on submit and reloads", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({ pilots: [] });
    vi.mocked(createPilotDealership).mockResolvedValue({
      pilot: makePilot(),
    });
    render(<PilotOnboardingSection />);
    await waitFor(() =>
      expect(fetchPilotDealerships).toHaveBeenCalledTimes(1),
    );
    await userEvent.type(screen.getByTestId("pilot-create-slug"), "acme-motors");
    await userEvent.type(screen.getByTestId("pilot-create-name"), "Acme Motors");
    await userEvent.type(screen.getByTestId("pilot-create-owner"), "owner");
    await userEvent.click(screen.getByTestId("pilot-create-submit"));
    await waitFor(() => {
      expect(createPilotDealership).toHaveBeenCalledWith({
        slug: "acme-motors",
        name: "Acme Motors",
        owner_username: "owner",
      });
    });
    await waitFor(() =>
      expect(fetchPilotDealerships).toHaveBeenCalledTimes(2),
    );
  });

  it("surfaces 409 slug collision error", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({ pilots: [] });
    vi.mocked(createPilotDealership).mockRejectedValue(
      new ApiError(409, '{"detail":"exists"}'),
    );
    render(<PilotOnboardingSection />);
    await waitFor(() =>
      expect(screen.getByTestId("pilot-list-empty")).toBeInTheDocument(),
    );
    await userEvent.type(screen.getByTestId("pilot-create-slug"), "collide");
    await userEvent.type(screen.getByTestId("pilot-create-name"), "Collide");
    await userEvent.type(screen.getByTestId("pilot-create-owner"), "owner");
    await userEvent.click(screen.getByTestId("pilot-create-submit"));
    await waitFor(() =>
      expect(screen.getByTestId("pilot-create-error")).toHaveTextContent(
        /slug is already taken/i,
      ),
    );
  });

  it("displays checklist steps in fixed vocab order", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [makePilot()],
    });
    render(<PilotOnboardingSection />);
    await userEvent.click(await screen.findByTestId("pilot-row-acme-motors"));
    await waitFor(() =>
      expect(screen.getByTestId("pilot-checklist")).toBeInTheDocument(),
    );
    STEP_ORDER.forEach((slug) => {
      expect(screen.getByTestId(`pilot-step-${slug}`)).toBeInTheDocument();
    });
  });

  it("advances a step via checklist stepper", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [makePilot()],
    });
    vi.mocked(advancePilotChecklistStep).mockResolvedValue({
      pilot: makePilot(),
    });
    render(<PilotOnboardingSection />);
    await userEvent.click(await screen.findByTestId("pilot-row-acme-motors"));
    await userEvent.click(
      await screen.findByTestId("pilot-advance-profile_configured"),
    );
    await waitFor(() => {
      expect(advancePilotChecklistStep).toHaveBeenCalledWith(
        "acme-motors",
        { step_slug: "profile_configured" },
      );
    });
    // Reload triggered after advance.
    await waitFor(() =>
      expect(fetchPilotDealerships).toHaveBeenCalledTimes(2),
    );
  });

  it("surfaces readiness precondition 409 on invalid advance", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [makePilot()],
    });
    vi.mocked(advancePilotChecklistStep).mockRejectedValue(
      new ApiError(409, '{"detail":"prior steps"}'),
    );
    render(<PilotOnboardingSection />);
    await userEvent.click(await screen.findByTestId("pilot-row-acme-motors"));
    await userEvent.click(
      await screen.findByTestId("pilot-advance-readiness_confirmed"),
    );
    await waitFor(() =>
      expect(screen.getByTestId("pilot-advance-error")).toHaveTextContent(
        /prior steps incomplete|step already done/i,
      ),
    );
  });

  it("uploads CSV file to importPilotInventory", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [makePilot()],
    });
    vi.mocked(importPilotInventory).mockResolvedValue({
      result: {
        dealership_id: 1,
        accepted_row_stock_numbers: ["P-1", "P-2"],
        rejected_rows: [],
      },
    });
    render(<PilotOnboardingSection />);
    await userEvent.click(await screen.findByTestId("pilot-row-acme-motors"));
    const fileInput = (await screen.findByTestId(
      "pilot-upload-input",
    )) as HTMLInputElement;
    const csv = new File(
      ["stock_number,year,model,price\nP-1,2020,Civic,15000\n"],
      "pilot.csv",
      { type: "text/csv" },
    );
    await userEvent.upload(fileInput, csv);
    await userEvent.click(screen.getByTestId("pilot-upload-submit"));
    await waitFor(() =>
      expect(importPilotInventory).toHaveBeenCalledWith("acme-motors", csv),
    );
    await waitFor(() => {
      const result = screen.getByTestId("pilot-upload-result");
      expect(result).toHaveTextContent(/Accepted:.*2/);
      expect(result).toHaveTextContent(/Rejected:.*0/);
    });
  });

  it("surfaces rejected rows in details block", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [makePilot()],
    });
    vi.mocked(importPilotInventory).mockResolvedValue({
      result: {
        dealership_id: 1,
        accepted_row_stock_numbers: ["P-1"],
        rejected_rows: [
          {
            row: { stock_number: "BAD-1", year: "not-a-year" },
            reason: "invalid year",
          },
        ],
      },
    });
    render(<PilotOnboardingSection />);
    await userEvent.click(await screen.findByTestId("pilot-row-acme-motors"));
    const fileInput = (await screen.findByTestId(
      "pilot-upload-input",
    )) as HTMLInputElement;
    const csv = new File(["header"], "pilot.csv", { type: "text/csv" });
    await userEvent.upload(fileInput, csv);
    await userEvent.click(screen.getByTestId("pilot-upload-submit"));
    await waitFor(() => {
      const rejected = screen.getByTestId("pilot-upload-rejected");
      expect(rejected).toHaveTextContent(/BAD-1/);
      expect(rejected).toHaveTextContent(/invalid year/);
    });
  });

  it("requires confirm click before terminating", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [makePilot()],
    });
    vi.mocked(terminatePilotDealership).mockResolvedValue({
      dealership: { ...makePilot().dealership, is_pilot: false },
    });
    render(<PilotOnboardingSection />);
    await userEvent.click(await screen.findByTestId("pilot-row-acme-motors"));
    // Initial state: terminate not yet called.
    await userEvent.click(await screen.findByTestId("pilot-terminate-init"));
    expect(terminatePilotDealership).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("pilot-terminate-confirm"));
    await waitFor(() =>
      expect(terminatePilotDealership).toHaveBeenCalledWith(
        "acme-motors",
        { reason: "", mode: "archive" },
      ),
    );
  });

  it("terminate mode switch persists to the payload", async () => {
    vi.mocked(fetchPilotDealerships).mockResolvedValue({
      pilots: [makePilot()],
    });
    vi.mocked(terminatePilotDealership).mockResolvedValue({
      dealership: { ...makePilot().dealership, is_pilot: false },
    });
    render(<PilotOnboardingSection />);
    await userEvent.click(await screen.findByTestId("pilot-row-acme-motors"));
    const modeSelect = await screen.findByTestId(
      "pilot-terminate-mode",
    );
    await userEvent.selectOptions(modeSelect, "cleanup");
    await userEvent.click(screen.getByTestId("pilot-terminate-init"));
    await userEvent.click(screen.getByTestId("pilot-terminate-confirm"));
    await waitFor(() =>
      expect(terminatePilotDealership).toHaveBeenCalledWith(
        "acme-motors",
        { reason: "", mode: "cleanup" },
      ),
    );
  });

  it("surfaces global fetch error", async () => {
    vi.mocked(fetchPilotDealerships).mockRejectedValue(
      new Error("network down"),
    );
    render(<PilotOnboardingSection />);
    await waitFor(() =>
      expect(screen.getByTestId("pilot-global-error")).toHaveTextContent(
        /network down/i,
      ),
    );
  });
});
