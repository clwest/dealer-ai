// SESSION_008 — onboarding now reads/writes against
// GET|PUT /api/dealer-ai/onboarding/profile/ (singleton).
//
// Single store profile only. Multi-tenant boundaries (and the per-entity
// split sketched in docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md)
// are deferred. Field shapes mirror the future schema so when the
// Dealership / DealerAssistant migration lands, columns just split.
//
// Frontend keeps camelCase state for ergonomics; transformer functions
// map to/from the snake_case API payload at the boundary.

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Boxes,
  Building2,
  CheckCircle2,
  Circle,
  ClipboardList,
  Coins,
  Loader2,
  Megaphone,
  Settings,
  Sparkles,
  Upload,
  UserRound,
} from "lucide-react";

import { DEFAULT_DEALER, PRODUCT } from "@/config/defaultDealer";
import {
  fetchOnboardingProfile,
  saveOnboardingProfile,
  uploadOnboardingLogo,
  type OnboardingProfilePayload,
} from "@/lib/api";

interface DealershipProfile {
  name: string;
  location: string;
  brands: string;
  salesPhone: string;
  website: string;
  /** SESSION_021 — hosted logo URL. Empty string keeps the static
   *  fallback (`DEFAULT_DEALER.logoPath`) in play via useBrand(). */
  logoUrl: string;
}

interface ManagerPreferences {
  salesTone: string;
  pricingComfort: string;
  appointmentPreference: string;
  leadHandoffStyle: string;
}

interface SalespersonProfile {
  name: string;
  role: string;
  phone: string;
  email: string;
  specialties: string;
  preferredTone: string;
  personalIntro: string;
}

interface AssistantBehavior {
  greeting: string;
  approvedPhrases: string;
  bannedPhrases: string;
  escalationRule: string;
  paymentDisclaimer: string;
}

interface PilotChecklist {
  inventoryConnected: boolean;
  financeRulesReviewed: boolean;
  salespeopleAdded: boolean;
  demoPromptsTested: boolean;
  pilotApproved: boolean;
}

// SESSION_032 — shape-of-business fields. Backend resolver
// (services/dealer_config.get_dealer_profile) reads the same values
// and threads them into every prompt template. `configured` is a
// sentinel that flips true on the first save, gating whether the
// resolver trusts the `bhph_enabled` toggle vs. falling back to the
// Copper Canyon default (`True`).
interface IndieBusiness {
  dealerType: "" | "independent" | "franchise";
  bhphEnabled: boolean;
  bhphConfigured: boolean;
  subprimeLenders: string;
  floorPlanLender: string;
  warrantyOffering: string;
  creditRangeServed: string;
  makesCarried: string;
}

interface OnboardingState {
  dealership: DealershipProfile;
  manager: ManagerPreferences;
  salesperson: SalespersonProfile;
  assistant: AssistantBehavior;
  indie: IndieBusiness;
  checklist: PilotChecklist;
}

const SALES_TONE_OPTIONS = [
  "Warm + consultative",
  "Direct + fast-paced",
  "Formal",
  "Friendly + casual",
];

const PRICING_COMFORT_OPTIONS = [
  "Firm — sticker price holds",
  "Negotiable — sales has discretion",
  "Disclose ranges up front",
];

const APPOINTMENT_OPTIONS = [
  "Book online preferred",
  "Phone call back",
  "Walk-in welcome",
];

const HANDOFF_OPTIONS = [
  "Next available salesperson",
  "Round-robin by team",
  "By specialty match",
  "Manager-assigned",
];

const SALESPERSON_TONE_OPTIONS = [
  "Match store default",
  "Warm + consultative",
  "Direct",
  "Highly technical",
];

const SECTION_COUNT = 6; // dealership, manager, salesperson, assistant, indie, checklist

const EMPTY_STATE: OnboardingState = {
  dealership: {
    name: "",
    location: "",
    brands: "",
    salesPhone: "",
    website: "",
    logoUrl: "",
  },
  manager: {
    salesTone: "",
    pricingComfort: "",
    appointmentPreference: "",
    leadHandoffStyle: "",
  },
  salesperson: {
    name: "",
    role: "",
    phone: "",
    email: "",
    specialties: "",
    preferredTone: "",
    personalIntro: "",
  },
  assistant: {
    greeting: "",
    approvedPhrases: "",
    bannedPhrases: "",
    escalationRule: "",
    paymentDisclaimer: "",
  },
  indie: {
    dealerType: "",
    bhphEnabled: true,
    bhphConfigured: false,
    subprimeLenders: "",
    floorPlanLender: "",
    warrantyOffering: "",
    creditRangeServed: "",
    makesCarried: "",
  },
  checklist: {
    inventoryConnected: false,
    financeRulesReviewed: false,
    salespeopleAdded: false,
    demoPromptsTested: false,
    pilotApproved: false,
  },
};

// API payload (snake_case) → page state (camelCase, sectioned).
function fromApi(payload: OnboardingProfilePayload): OnboardingState {
  return {
    dealership: {
      name: payload.dealership_name,
      location: payload.store_location,
      brands: payload.main_brands,
      salesPhone: payload.sales_phone,
      website: payload.website,
      logoUrl: payload.logo_url ?? "",
    },
    manager: {
      salesTone: payload.sales_tone,
      pricingComfort: payload.pricing_comfort,
      appointmentPreference: payload.appointment_preference,
      leadHandoffStyle: payload.lead_handoff_style,
    },
    salesperson: {
      name: payload.salesperson_name,
      role: payload.salesperson_role,
      phone: payload.salesperson_phone,
      email: payload.salesperson_email,
      specialties: payload.salesperson_specialties,
      preferredTone: payload.salesperson_preferred_tone,
      personalIntro: payload.salesperson_intro,
    },
    assistant: {
      greeting: payload.dealership_greeting,
      approvedPhrases: payload.approved_phrases,
      bannedPhrases: payload.banned_phrases,
      escalationRule: payload.escalation_rule,
      paymentDisclaimer: payload.payment_disclaimer,
    },
    indie: {
      dealerType: payload.dealer_type,
      bhphEnabled: payload.bhph_enabled,
      bhphConfigured: payload.bhph_configured,
      subprimeLenders: payload.subprime_lenders,
      floorPlanLender: payload.floor_plan_lender,
      warrantyOffering: payload.warranty_offering,
      creditRangeServed: payload.credit_range_served,
      makesCarried: payload.makes_carried,
    },
    checklist: {
      inventoryConnected: payload.inventory_connected,
      financeRulesReviewed: payload.finance_rules_reviewed,
      salespeopleAdded: payload.salespeople_added,
      demoPromptsTested: payload.demo_prompts_tested,
      pilotApproved: payload.pilot_approved,
    },
  };
}

// Page state → API payload (PUT body).
function toApi(state: OnboardingState): OnboardingProfilePayload {
  return {
    dealership_name: state.dealership.name,
    store_location: state.dealership.location,
    main_brands: state.dealership.brands,
    sales_phone: state.dealership.salesPhone,
    website: state.dealership.website,
    logo_url: state.dealership.logoUrl,
    sales_tone: state.manager.salesTone,
    pricing_comfort: state.manager.pricingComfort,
    appointment_preference: state.manager.appointmentPreference,
    lead_handoff_style: state.manager.leadHandoffStyle,
    salesperson_name: state.salesperson.name,
    salesperson_role: state.salesperson.role,
    salesperson_phone: state.salesperson.phone,
    salesperson_email: state.salesperson.email,
    salesperson_specialties: state.salesperson.specialties,
    salesperson_preferred_tone: state.salesperson.preferredTone,
    salesperson_intro: state.salesperson.personalIntro,
    dealership_greeting: state.assistant.greeting,
    approved_phrases: state.assistant.approvedPhrases,
    banned_phrases: state.assistant.bannedPhrases,
    escalation_rule: state.assistant.escalationRule,
    payment_disclaimer: state.assistant.paymentDisclaimer,
    inventory_connected: state.checklist.inventoryConnected,
    finance_rules_reviewed: state.checklist.financeRulesReviewed,
    salespeople_added: state.checklist.salespeopleAdded,
    demo_prompts_tested: state.checklist.demoPromptsTested,
    pilot_approved: state.checklist.pilotApproved,
    dealer_type: state.indie.dealerType,
    bhph_enabled: state.indie.bhphEnabled,
    bhph_configured: state.indie.bhphConfigured,
    subprime_lenders: state.indie.subprimeLenders,
    floor_plan_lender: state.indie.floorPlanLender,
    warranty_offering: state.indie.warrantyOffering,
    credit_range_served: state.indie.creditRangeServed,
    makes_carried: state.indie.makesCarried,
  };
}

type LoadStatus = "loading" | "loaded" | "error";
type SaveStatus = "idle" | "saving" | "saved" | "error";
type UploadStatus = "idle" | "uploading" | "uploaded" | "error";

export default function DealerOnboardingPage() {
  const [state, setState] = useState<OnboardingState>(EMPTY_STATE);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Load on mount. The backend always returns 200 with either the saved
  // profile or the default shape, so we don't have a "no row yet" branch.
  useEffect(() => {
    let cancelled = false;
    fetchOnboardingProfile()
      .then((payload) => {
        if (cancelled) return;
        setState(fromApi(payload));
        setLoadStatus("loaded");
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadStatus("error");
        setLoadError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { dealership, manager, salesperson, assistant, indie, checklist } = state;
  const setDealership = (next: DealershipProfile) =>
    setState((s) => ({ ...s, dealership: next }));
  const setManager = (next: ManagerPreferences) =>
    setState((s) => ({ ...s, manager: next }));
  const setSalesperson = (next: SalespersonProfile) =>
    setState((s) => ({ ...s, salesperson: next }));
  const setAssistant = (next: AssistantBehavior) =>
    setState((s) => ({ ...s, assistant: next }));
  const setIndie = (updater: (prev: IndieBusiness) => IndieBusiness) =>
    setState((s) => ({ ...s, indie: updater(s.indie) }));
  const setChecklist = (
    updater: (prev: PilotChecklist) => PilotChecklist,
  ) => setState((s) => ({ ...s, checklist: updater(s.checklist) }));

  // Lightweight completion heuristic so the manager can see progress.
  // Each section is "complete" when its primary fields are non-empty.
  const completion = useMemo(() => {
    const sectionsDone = [
      Boolean(dealership.name && dealership.location),
      Boolean(manager.salesTone && manager.pricingComfort),
      Boolean(salesperson.name && salesperson.role),
      Boolean(assistant.greeting && assistant.escalationRule),
      // Indie section — complete when dealer type is chosen AND BHPH
      // is explicitly configured (either enabled or disabled).
      Boolean(indie.dealerType && indie.bhphConfigured),
      Object.values(checklist).every(Boolean),
    ].filter(Boolean).length;
    return { sectionsDone, total: SECTION_COUNT };
  }, [dealership, manager, salesperson, assistant, indie, checklist]);

  const handleSave = async () => {
    setSaveStatus("saving");
    setSaveError(null);
    try {
      const saved = await saveOnboardingProfile(toApi(state));
      // Reflect server-canonical values (e.g. updated_at) back into local
      // state so a subsequent edit-then-save round-trip stays consistent.
      setState(fromApi(saved));
      setSaveStatus("saved");
    } catch (err: unknown) {
      setSaveStatus("error");
      setSaveError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleLogoUpload = async (file: File | null) => {
    if (!file) return;
    setUploadStatus("uploading");
    setUploadError(null);
    try {
      const saved = await uploadOnboardingLogo(file);
      setDealership({ ...dealership, logoUrl: saved.logo_url ?? "" });
      setUploadStatus("uploaded");
    } catch (err: unknown) {
      setUploadStatus("error");
      setUploadError(err instanceof Error ? err.message : String(err));
    }
  };

  const checklistItems: Array<{
    key: keyof PilotChecklist;
    label: string;
  }> = [
    { key: "inventoryConnected", label: "Inventory connected" },
    { key: "financeRulesReviewed", label: "Finance rules reviewed" },
    { key: "salespeopleAdded", label: "Salespeople added" },
    { key: "demoPromptsTested", label: "Demo prompts tested" },
    { key: "pilotApproved", label: "Pilot approved" },
  ];

  if (loadStatus === "loading") {
    return (
      <div className="card flex items-center gap-3 px-6 py-5 text-sm text-slate-500">
        <span
          className="inline-block h-3 w-3 animate-pulse rounded-full bg-brand-blue"
          aria-hidden
        />
        Loading onboarding profile…
      </div>
    );
  }

  if (loadStatus === "error") {
    return (
      <div className="card px-6 py-5">
        <h1 className="text-lg font-bold text-brand-ink">Dealership Onboarding</h1>
        <p className="mt-2 text-sm text-rose-600">
          Failed to load onboarding profile: {loadError ?? "unknown error"}
        </p>
        <button
          type="button"
          onClick={() => {
            setLoadStatus("loading");
            setLoadError(null);
            fetchOnboardingProfile()
              .then((p) => {
                setState(fromApi(p));
                setLoadStatus("loaded");
              })
              .catch((err: unknown) => {
                setLoadStatus("error");
                setLoadError(err instanceof Error ? err.message : String(err));
              });
          }}
          className="mt-4 rounded-md bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue/90"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Section 1 — Welcome / setup status */}
      <div className="card flex flex-wrap items-center justify-between gap-4 px-6 py-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-blue text-white">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-brand-ink">
              Dealership Onboarding
            </h1>
            <p className="text-sm text-slate-500">
              Configure store-level voice, salesperson profiles, and pilot
              readiness. Nothing here goes live until you flip the pilot
              switch in Step 6.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              completion.sectionsDone === completion.total
                ? "bg-emerald-50 text-emerald-700"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {completion.sectionsDone} of {completion.total} sections complete
          </span>
          <Link
            to="/dealer-ai-demo"
            className="text-sm font-semibold text-brand-accent hover:underline"
          >
            Open customer demo →
          </Link>
        </div>
      </div>

      {/* Section 2 — Dealership profile */}
      <SectionCard
        icon={<Building2 className="h-4 w-4" />}
        title="Dealership profile"
        subtitle="The basics. Used by the assistant for greetings, handoffs, and fallback references."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Dealership name"
            value={dealership.name}
            onChange={(v) => setDealership({ ...dealership, name: v })}
            placeholder="Your dealership name"
          />
          <Field
            label="Store location"
            value={dealership.location}
            onChange={(v) => setDealership({ ...dealership, location: v })}
            placeholder="City, State"
          />
          <Field
            label="Main brands carried"
            value={dealership.brands}
            onChange={(v) => setDealership({ ...dealership, brands: v })}
            placeholder="Ford (new) + multi-brand used"
          />
          <Field
            label="Sales phone"
            value={dealership.salesPhone}
            onChange={(v) => setDealership({ ...dealership, salesPhone: v })}
            placeholder="(555) 555-1234"
            type="tel"
          />
          <Field
            label="Website"
            value={dealership.website}
            onChange={(v) => setDealership({ ...dealership, website: v })}
            placeholder="https://your-dealership.example.com"
            type="url"
            className="sm:col-span-2"
          />
          {/* SESSION_021 — Logo URL. Profile-supplied URL wins over the
              kit's static fallback in `defaultDealer.ts`. The
              <BrandHeader /> in the OS shell and the <BrandMark /> on
              the embed both source `brand.logoUrl`, so a save here
              flows into every brand surface on the next route mount. */}
          <Field
            label="Logo URL"
            value={dealership.logoUrl}
            onChange={(v) => setDealership({ ...dealership, logoUrl: v })}
            placeholder="https://cdn.example.com/dealer-logo.svg"
            type="url"
            className="sm:col-span-2"
            helperText="Paste a hosted logo URL. If blank, the default dealer logo is used."
          />
          <LogoUploadField
            status={uploadStatus}
            error={uploadError}
            onUpload={handleLogoUpload}
          />
        </div>
      </SectionCard>

      {/* SESSION_020 — Dealer Kit Status.
          Read-only summary that mirrors the Dealership profile
          fields above plus the kit-level constants from
          config/defaultDealer.ts. Updates live as the manager
          types — they see exactly what the OS chrome and embed
          will read once they save.
          SESSION_021 — Logo row now reflects the profile URL
          when set, falling back to DEFAULT_DEALER.logoPath. */}
      <DealerKitStatusCard
        dealershipName={dealership.name}
        storeLocation={dealership.location}
        brands={dealership.brands}
        logoUrl={dealership.logoUrl}
      />

      {/* Section 3 — Manager preferences */}
      <SectionCard
        icon={<Settings className="h-4 w-4" />}
        title="Manager preferences"
        subtitle="These shape the AI's voice and routing rules store-wide."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Sales tone"
            value={manager.salesTone}
            onChange={(v) => setManager({ ...manager, salesTone: v })}
            options={SALES_TONE_OPTIONS}
          />
          <SelectField
            label="Pricing comfort"
            value={manager.pricingComfort}
            onChange={(v) => setManager({ ...manager, pricingComfort: v })}
            options={PRICING_COMFORT_OPTIONS}
          />
          <SelectField
            label="Appointment preference"
            value={manager.appointmentPreference}
            onChange={(v) =>
              setManager({ ...manager, appointmentPreference: v })
            }
            options={APPOINTMENT_OPTIONS}
          />
          <SelectField
            label="Lead handoff style"
            value={manager.leadHandoffStyle}
            onChange={(v) => setManager({ ...manager, leadHandoffStyle: v })}
            options={HANDOFF_OPTIONS}
          />
        </div>
      </SectionCard>

      {/* Section 4 — Salesperson profile setup */}
      <SectionCard
        icon={<UserRound className="h-4 w-4" />}
        title="Salesperson profile setup"
        subtitle="Add one salesperson now. Use the Sales Team page to add the rest later."
        right={
          <Link
            to="/dealer-ai-admin/team"
            className="text-xs font-semibold text-brand-accent hover:underline"
          >
            Manage full team →
          </Link>
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Name"
            value={salesperson.name}
            onChange={(v) => setSalesperson({ ...salesperson, name: v })}
            placeholder="Sarah Lin"
          />
          <Field
            label="Role"
            value={salesperson.role}
            onChange={(v) => setSalesperson({ ...salesperson, role: v })}
            placeholder="Senior Sales Advisor"
          />
          <Field
            label="Phone"
            value={salesperson.phone}
            onChange={(v) => setSalesperson({ ...salesperson, phone: v })}
            placeholder="(555) 555-1234"
            type="tel"
          />
          <Field
            label="Email"
            value={salesperson.email}
            onChange={(v) => setSalesperson({ ...salesperson, email: v })}
            placeholder="sarah@your-dealership.example.com"
            type="email"
          />
          <Field
            label="Specialties"
            value={salesperson.specialties}
            onChange={(v) =>
              setSalesperson({ ...salesperson, specialties: v })
            }
            placeholder="Trucks, first-time buyers, finance pre-quals"
            className="sm:col-span-2"
          />
          <SelectField
            label="Preferred tone"
            value={salesperson.preferredTone}
            onChange={(v) =>
              setSalesperson({ ...salesperson, preferredTone: v })
            }
            options={SALESPERSON_TONE_OPTIONS}
          />
          <Field
            label="Personal intro"
            value={salesperson.personalIntro}
            onChange={(v) =>
              setSalesperson({ ...salesperson, personalIntro: v })
            }
            placeholder="Hi, I'm Sarah — I've been helping families pick the right vehicle for 12 years."
            multiline
            className="sm:col-span-2"
          />
        </div>
      </SectionCard>

      {/* Section 5 — AI assistant behavior */}
      <SectionCard
        icon={<Megaphone className="h-4 w-4" />}
        title="AI assistant behavior"
        subtitle="What the AI says, what it never says, and when it hands off to a human."
      >
        <div className="grid gap-4">
          <Field
            label="Dealership greeting"
            value={assistant.greeting}
            onChange={(v) => setAssistant({ ...assistant, greeting: v })}
            placeholder="Welcome to your dealership. Tell me what you're shopping for…"
            multiline
          />
          <Field
            label="Approved phrases"
            value={assistant.approvedPhrases}
            onChange={(v) =>
              setAssistant({ ...assistant, approvedPhrases: v })
            }
            placeholder="One per line — e.g., 'Want me to set up a closer look?'"
            multiline
          />
          <Field
            label="Banned phrases"
            value={assistant.bannedPhrases}
            onChange={(v) =>
              setAssistant({ ...assistant, bannedPhrases: v })
            }
            placeholder="One per line — e.g., 'guaranteed approval', 'best price ever'"
            multiline
          />
          <Field
            label="Escalation / handoff rule"
            value={assistant.escalationRule}
            onChange={(v) =>
              setAssistant({ ...assistant, escalationRule: v })
            }
            placeholder="When a customer asks about financing terms, hand off to next available."
            multiline
          />
          <Field
            label="Inventory / payment disclaimer"
            value={assistant.paymentDisclaimer}
            onChange={(v) =>
              setAssistant({ ...assistant, paymentDisclaimer: v })
            }
            placeholder="Payments shown are estimates. Final terms with approved credit (W.A.C.)."
            multiline
          />
        </div>
      </SectionCard>

      {/* Section 6 — Indie business shape (SESSION_032) */}
      <SectionCard
        icon={<Coins className="h-4 w-4" />}
        title="Business shape"
        subtitle="How this store makes money — drives BHPH math, subprime language, and prohibited-copy scrubs."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {/* Dealer type — radio-style choice */}
          <div className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-xs font-semibold text-slate-600">
              Dealer type
            </span>
            <div className="flex flex-wrap gap-2">
              {(["independent", "franchise"] as const).map((option) => {
                const active = indie.dealerType === option;
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() =>
                      setIndie((i) => ({ ...i, dealerType: option }))
                    }
                    className={`rounded-md border px-4 py-2 text-sm font-medium transition ${
                      active
                        ? "border-brand-blue bg-brand-blue text-white"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {option === "independent"
                      ? "Independent (mixed-lot used)"
                      : "Franchise (OEM-affiliated)"}
                  </button>
                );
              })}
            </div>
            <span className="text-[11px] text-slate-500">
              Independent = mixed-make used lot. Franchise = OEM-affiliated
              store. Chat prompts + scrubs adjust automatically.
            </span>
          </div>

          {/* BHPH toggle — mirrors the checklist toggle pattern */}
          <div className="flex flex-col gap-1 sm:col-span-2">
            <span className="text-xs font-semibold text-slate-600">
              Buy-Here-Pay-Here financing
            </span>
            <button
              type="button"
              onClick={() =>
                setIndie((i) => ({
                  ...i,
                  bhphEnabled: !i.bhphEnabled,
                  bhphConfigured: true,
                }))
              }
              className="flex w-full items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-left transition hover:bg-slate-50"
            >
              {indie.bhphEnabled ? (
                <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
              ) : (
                <Circle className="h-5 w-5 shrink-0 text-slate-300" />
              )}
              <span className="flex-1 text-sm">
                <span
                  className={
                    indie.bhphEnabled
                      ? "font-semibold text-brand-ink"
                      : "text-slate-600"
                  }
                >
                  {indie.bhphEnabled ? "Enabled" : "Disabled"}
                </span>
                {indie.bhphConfigured ? null : (
                  <span className="ml-2 text-[11px] text-amber-600">
                    (Uses default until saved)
                  </span>
                )}
              </span>
            </button>
            <span className="text-[11px] text-slate-500">
              Enables the weekly / biweekly BHPH payment engine variant and
              matching prompt scaffolding for credit-challenged buyers.
            </span>
          </div>

          <Field
            label="Floor plan lender"
            value={indie.floorPlanLender}
            onChange={(v) =>
              setIndie((i) => ({ ...i, floorPlanLender: v }))
            }
            placeholder="e.g., NextGear, Kinetic Advantage, AFC"
            helperText="Wholesale inventory-financing partner."
          />
          <Field
            label="Warranty offering"
            value={indie.warrantyOffering}
            onChange={(v) =>
              setIndie((i) => ({ ...i, warrantyOffering: v }))
            }
            placeholder="30-day / 1000-mile powertrain"
            helperText="Retail warranty. AS-IS lots leave this blank."
          />
          <Field
            label="Credit range served"
            value={indie.creditRangeServed}
            onChange={(v) =>
              setIndie((i) => ({ ...i, creditRangeServed: v }))
            }
            placeholder="580+ with strong down; BHPH below"
            helperText="Guides the assistant's tone when a customer names their credit tier."
            className="sm:col-span-2"
          />
          <Field
            label="Subprime lender panel"
            value={indie.subprimeLenders}
            onChange={(v) =>
              setIndie((i) => ({ ...i, subprimeLenders: v }))
            }
            placeholder="One lender per line — e.g., Westlake Financial, Global Lending"
            helperText="Panels used for sub-660 buyers. Assistant references without naming rate ranges."
            multiline
            className="sm:col-span-2"
          />
          <Field
            label="Makes carried"
            value={indie.makesCarried}
            onChange={(v) => setIndie((i) => ({ ...i, makesCarried: v }))}
            placeholder="One make per line — e.g., Toyota, Honda, Ford"
            helperText="Mixed-make used lots list every make they stock. Franchise stores list their OEM + any secondary makes."
            multiline
            className="sm:col-span-2"
          />
        </div>
      </SectionCard>

      {/* Section 7 — Pilot checklist */}
      <SectionCard
        icon={<ClipboardList className="h-4 w-4" />}
        title="Next steps checklist"
        subtitle="Complete these before flipping the dealership to pilot active."
      >
        <ul className="space-y-2">
          {checklistItems.map((item) => {
            const checked = checklist[item.key];
            return (
              <li key={item.key}>
                <button
                  type="button"
                  className="flex w-full items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-left transition hover:bg-slate-50"
                  onClick={() =>
                    setChecklist((c) => ({ ...c, [item.key]: !c[item.key] }))
                  }
                >
                  {checked ? (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
                  ) : (
                    <Circle className="h-5 w-5 shrink-0 text-slate-300" />
                  )}
                  <span
                    className={`text-sm ${
                      checked
                        ? "font-semibold text-brand-ink"
                        : "text-slate-600"
                    }`}
                  >
                    {item.label}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <p className="mt-4 text-xs text-slate-500">
          Toggling a checkbox is local until you press <em>Save changes</em>.
        </p>
      </SectionCard>

      {/* Save bar */}
      <div className="card flex flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div className="space-y-1">
          <p className="text-xs text-slate-500">
            <SaveStatusLabel status={saveStatus} error={saveError} />
          </p>
          {/* SESSION_009: surface the live-AI link so managers know edits aren't cosmetic. */}
          <p className="text-xs text-slate-400">
            Saved settings shape the live sales assistant — voice, encouraged
            phrasing, banned phrases, and the payment disclaimer all flow into
            the chat engine on the next reply.
          </p>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saveStatus === "saving"}
          className="rounded-md bg-brand-blue px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-blue/90 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {saveStatus === "saving" ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}

function SaveStatusLabel({
  status,
  error,
}: {
  status: SaveStatus;
  error: string | null;
}) {
  if (status === "idle") return <>Changes are not saved until you press Save.</>;
  if (status === "saving") return <>Saving…</>;
  if (status === "saved")
    return (
      <span className="text-emerald-700">
        Saved. Live AI behavior updated.
      </span>
    );
  return (
    <span className="text-rose-600">
      Save failed: {error ?? "unknown error"}
    </span>
  );
}

// ---- Reusable section + field components -----------------------------------

interface SectionCardProps {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * SESSION_020 — Dealer Kit Status.
 *
 * Read-only summary of how the active dealer identity flows into
 * the OS shell and embed. Values mirror the Dealership profile
 * form state above, so as a manager edits the fields the card
 * updates in real time — they can preview the change before
 * committing it via Save.
 *
 * Product / kit-level identity (productName, productSubtitle,
 * logoPath) is sourced from `config/defaultDealer.ts`. Active
 * dealer values come from form state; falls back to
 * `DEFAULT_DEALER` when the form hasn't been filled in.
 */
function DealerKitStatusCard({
  dealershipName,
  storeLocation,
  brands,
  logoUrl,
}: {
  dealershipName: string;
  storeLocation: string;
  brands: string;
  logoUrl: string;
}) {
  const activeName = dealershipName.trim() || DEFAULT_DEALER.dealershipName;
  const activeLocation =
    storeLocation.trim() || DEFAULT_DEALER.storeLocation;
  const activeBrands = brands.trim() || DEFAULT_DEALER.brand;
  // SESSION_021 — same resolution rule the brand hook uses.
  const trimmedLogo = logoUrl.trim();
  const logoFromProfile = trimmedLogo.length > 0;
  const resolvedLogo = logoFromProfile ? trimmedLogo : DEFAULT_DEALER.logoPath;

  return (
    <SectionCard
      icon={<Boxes className="h-4 w-4" />}
      title="Dealer Kit Status"
      subtitle="How your dealer identity flows into the OS and the public embed."
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <StatusRow label="Product">{PRODUCT.productName}</StatusRow>
        <StatusRow label="Active dealer">{activeName}</StatusRow>
        <StatusRow label="Location">{activeLocation}</StatusRow>
        <StatusRow label="Brand(s)">{activeBrands}</StatusRow>
        <StatusRow label="Logo">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <code className="break-all font-mono text-[11px]">
              {resolvedLogo}
            </code>
            <span className="text-[11px] text-slate-500">
              {logoFromProfile ? "(from profile)" : "(static default)"}
            </span>
          </span>
        </StatusRow>
        <StatusRow label="Status">
          <span className="inline-flex items-center gap-1.5">
            <span
              aria-hidden
              className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500"
            />
            Single-dealer configuration
          </span>
        </StatusRow>
      </div>
      <p className="mt-4 text-xs leading-relaxed text-slate-500">
        Changing these fields updates the visible dealer identity across
        the OS and embed. The logo URL above falls back to the kit's
        static asset when blank — see{" "}
        <code className="font-mono text-[11px]">docs/DEALER_DUPLICATION_GUIDE.md</code>{" "}
        for the full workflow.
      </p>
    </SectionCard>
  );
}

function StatusRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="text-[10.5px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-sm text-brand-ink">{children}</div>
    </div>
  );
}

function SectionCard({
  icon,
  title,
  subtitle,
  right,
  children,
}: SectionCardProps) {
  return (
    <section className="card px-6 py-5">
      <header className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-blue/10 text-brand-blue">
            {icon}
          </div>
          <div>
            <h2 className="text-base font-bold text-brand-ink">{title}</h2>
            {subtitle ? (
              <p className="text-xs text-slate-500">{subtitle}</p>
            ) : null}
          </div>
        </div>
        {right ?? null}
      </header>
      {children}
    </section>
  );
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  multiline?: boolean;
  className?: string;
  /** Small subtext rendered beneath the input. SESSION_021. */
  helperText?: string;
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  multiline = false,
  className = "",
  helperText,
}: FieldProps) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs font-semibold text-slate-600">{label}</span>
      {multiline ? (
        <textarea
          className="input min-h-[72px] resize-y"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
      ) : (
        <input
          className="input"
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
      )}
      {helperText ? (
        <span className="text-[11px] text-slate-500">{helperText}</span>
      ) : null}
    </label>
  );
}

function LogoUploadField({
  status,
  error,
  onUpload,
}: {
  status: UploadStatus;
  error: string | null;
  onUpload: (file: File | null) => void;
}) {
  const uploading = status === "uploading";
  return (
    <div className="flex flex-col gap-1 sm:col-span-2">
      <span className="text-xs font-semibold text-slate-600">Upload logo</span>
      <label
        className={`flex min-h-20 cursor-pointer items-center justify-between gap-3 rounded-lg border border-dashed px-4 py-3 transition ${
          uploading
            ? "border-slate-200 bg-slate-50 text-slate-400"
            : "border-slate-300 bg-white text-brand-ink hover:border-brand-blue/60 hover:bg-brand-blue/5"
        }`}
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-brand-blue/10 text-brand-blue">
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-semibold">
              {uploading ? "Uploading logo..." : "Choose logo file"}
            </span>
            <span className="block text-xs text-slate-500">
              JPG, PNG, WEBP, or SVG. 2 MB max. Upload saves the logo URL to
              this profile.
            </span>
          </span>
        </span>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/svg+xml"
          className="sr-only"
          disabled={uploading}
          onChange={(event) => {
            const file = event.currentTarget.files?.[0] ?? null;
            onUpload(file);
            event.currentTarget.value = "";
          }}
        />
      </label>
      {status === "uploaded" ? (
        <span className="text-[11px] text-emerald-700">
          Logo uploaded. Save any other profile edits when ready.
        </span>
      ) : null}
      {status === "error" && error ? (
        <span className="text-[11px] text-rose-600">{error}</span>
      ) : null}
    </div>
  );
}

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}

function SelectField({ label, value, onChange, options }: SelectFieldProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-semibold text-slate-600">{label}</span>
      <select
        className="input appearance-none bg-white"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select…</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}
