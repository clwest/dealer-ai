// SESSION_235 — the overview must tell the truth about the store.
// Two shapes exercised end to end: an empty store (missing team +
// inventory show up in the attention list with fix links) and a
// populated store (those two lines are absent because the
// dealership can prove them for itself via ``profile.readiness``).
// Also verifies the coaching card labels its window and shows an
// honest empty state when there are no events, rather than dressing
// zeros as activity.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchOnboardingProfile: vi.fn(),
    fetchAuditEvents: vi.fn(),
    fetchAdminLeads: vi.fn(),
  };
});

import {
  fetchAdminLeads,
  fetchAuditEvents,
  fetchOnboardingProfile,
  type AuditEventsResponse,
  type OnboardingProfilePayload,
  type OnboardingReadinessPayload,
} from "@/lib/api";
import DealerOverviewPage from "@/pages/DealerOverviewPage";

const mockedFetchProfile = vi.mocked(fetchOnboardingProfile);
const mockedFetchAudit = vi.mocked(fetchAuditEvents);
const mockedFetchLeads = vi.mocked(fetchAdminLeads);

function makeReadiness(
  overrides: Partial<OnboardingReadinessPayload> = {},
): OnboardingReadinessPayload {
  return {
    salespeople_added: false,
    salespeople_count: 0,
    inventory_connected: false,
    inventory_count: 0,
    inventory_source: "",
    payment_defaults_set: true,
    timezone_set: true,
    ...overrides,
  };
}

function makeProfile(
  overrides: Partial<OnboardingProfilePayload> = {},
): OnboardingProfilePayload {
  return {
    dealership_name: "Copper Canyon Auto",
    store_location: "Yuma, AZ",
    street_address: "",
    city: "",
    state: "",
    postal_code: "",
    main_brands: "",
    sales_phone: "",
    website: "",
    logo_url: "",
    sales_tone: "friendly",
    pricing_comfort: "",
    appointment_preference: "",
    lead_handoff_style: "",
    salesperson_name: "",
    salesperson_role: "",
    salesperson_phone: "",
    salesperson_email: "",
    salesperson_specialties: "",
    salesperson_preferred_tone: "",
    salesperson_intro: "",
    dealership_greeting: "",
    approved_phrases: "",
    banned_phrases: "no rate quotes",
    escalation_rule: "",
    payment_disclaimer: "W.A.C.",
    inventory_connected: false,
    finance_rules_reviewed: true,
    salespeople_added: false,
    demo_prompts_tested: true,
    pilot_approved: true,
    dealer_type: "independent",
    bhph_enabled: false,
    bhph_configured: false,
    subprime_lenders: "",
    floor_plan_lender: "",
    warranty_offering: "",
    credit_range_served: "",
    makes_carried: "",
    default_apr: null,
    default_term_months: null,
    default_down_payment_pct: null,
    sales_tax_rate_pct: null,
    doc_fees: null,
    readiness: makeReadiness(),
    ...overrides,
  };
}

function makeAudit(
  overrides: Partial<AuditEventsResponse> = {},
): AuditEventsResponse {
  return {
    since: "24h",
    window_hours: 24,
    generated_at: new Date().toISOString(),
    totals: {
      total_guard_events: 0,
      pre_llm_short_circuits: 0,
      post_llm_rewrites: 0,
      post_llm_overrides: 0,
      scrubs_fired: 0,
    },
    by_flag: [],
    recent_events: [],
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <DealerOverviewPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedFetchAudit.mockResolvedValue(makeAudit());
  mockedFetchLeads.mockResolvedValue({ results: [] } as never);
});

describe("DealerOverviewPage attention list", () => {
  it("empty store surfaces the team and inventory lines with fix links", async () => {
    mockedFetchProfile.mockResolvedValue(
      makeProfile({
        readiness: makeReadiness({
          salespeople_added: false,
          inventory_connected: false,
        }),
      }),
    );
    renderPage();
    // Sales team line + Onboarding CTA
    await waitFor(() => {
      expect(screen.getByText(/first salesperson/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/inventory source/i)).toBeInTheDocument();
    // Both fix CTAs render as links to their fix pages.
    const teamLink = screen.getByRole("link", { name: /team/i });
    expect(teamLink.getAttribute("href")).toBe("/dealer-ai-admin/team");
    const inventoryLink = screen.getByRole("link", { name: /inventory/i });
    expect(inventoryLink.getAttribute("href")).toBe(
      "/dealer-ai-admin/inventory",
    );
  });

  it("populated store omits the team and inventory lines", async () => {
    mockedFetchProfile.mockResolvedValue(
      makeProfile({
        readiness: makeReadiness({
          salespeople_added: true,
          salespeople_count: 3,
          inventory_connected: true,
          inventory_count: 130,
          inventory_source: "130 vehicles · demo seed",
        }),
      }),
    );
    renderPage();
    await waitFor(() => {
      // The AttentionItemsCard has finished loading and rendered
      // (either items or the all-clear line).
      expect(screen.queryByText(/first salesperson/i)).not.toBeInTheDocument();
    });
    expect(screen.queryByText(/inventory source/i)).not.toBeInTheDocument();
  });
});

describe("DealerOverviewPage coaching summary", () => {
  it("labels its window and shows the honest empty state when totals are zero", async () => {
    mockedFetchProfile.mockResolvedValue(makeProfile());
    mockedFetchAudit.mockResolvedValue(makeAudit());
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/no coaching events in the last 24 hours\./i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(
        /how well the assistant is following your training, in the last 24 hours/i,
      ),
    ).toBeInTheDocument();
  });

  it("renders totals when the window has activity", async () => {
    mockedFetchProfile.mockResolvedValue(makeProfile());
    mockedFetchAudit.mockResolvedValue(
      makeAudit({
        totals: {
          total_guard_events: 2,
          pre_llm_short_circuits: 0,
          post_llm_rewrites: 1,
          post_llm_overrides: 0,
          scrubs_fired: 1,
        },
      }),
    );
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Rules enforced")).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/no coaching events/i),
    ).not.toBeInTheDocument();
  });
});
