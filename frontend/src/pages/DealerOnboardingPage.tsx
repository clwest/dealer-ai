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
  DollarSign,
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
  fetchPaymentPreview,
  saveOnboardingProfile,
  uploadOnboardingLogo,
  type OnboardingProfilePayload,
  type PaymentPreviewResponse,
} from "@/lib/api";

interface DealershipProfile {
  name: string;
  location: string;
  /** SESSION_239 — structured address parts. `location` (aka
   *  `store_location`) stays as the free-text line the header
   *  renders; the four parts below are what the tax rate label and
   *  the next session's per-store time zone read from. `location`
   *  derives from these once all four are set. */
  streetAddress: string;
  city: string;
  state: string;
  postalCode: string;
  brands: string;
  salesPhone: string;
  website: string;
  /** SESSION_021 — hosted logo URL. Empty string keeps the static
   *  fallback (`DEFAULT_DEALER.logoPath`) in play via useBrand(). */
  logoUrl: string;
  /** SESSION_240 (walk finding 28) — the store's IANA time zone.
   *  Backed by ``Dealership.timezone``; consumed by every business-
   *  day decision (ledger, aging, be-back detector, BHPH day-counts)
   *  and by the store-zone formatter that renders dates on the
   *  operator screens. Empty on first load only. */
  timezone: string;
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

// SESSION_238 — per-store payment defaults for the est-payment line.
// Empty string = "unset — payment_engine fallback (7.49 / 72 / 10)".
// Kept as strings so the numeric inputs can render empty vs. zero
// without a null/NaN dance.
interface PaymentDefaults {
  defaultApr: string;
  defaultTermMonths: string;
  defaultDownPaymentPct: string;
  // SESSION_239 — per-store tax rate and doc fees. Same empty-
  // string convention: "" = "unset — payment_engine fallback
  // (4.5% / $599)".
  salesTaxRatePct: string;
  docFees: string;
}

interface OnboardingState {
  dealership: DealershipProfile;
  manager: ManagerPreferences;
  salesperson: SalespersonProfile;
  assistant: AssistantBehavior;
  indie: IndieBusiness;
  payments: PaymentDefaults;
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

// SESSION_238 — kept in sync with services/payment_engine.py and
// backend/dealer_ai/serializers.py PAYMENT_DEFAULT_* bounds. Any
// change here needs the matching change on the backend (the preview
// endpoint validates against the backend constants).
const PAYMENT_APR_MIN = 0;
const PAYMENT_APR_MAX = 40;
const PAYMENT_TERM_MIN = 12;
const PAYMENT_TERM_MAX = 96;
const PAYMENT_DOWN_MIN = 0;
const PAYMENT_DOWN_MAX = 50;
const PAYMENT_TAX_RATE_MIN = 0;
const PAYMENT_TAX_RATE_MAX = 15;
const PAYMENT_DOC_FEES_MIN = 0;
const PAYMENT_DOC_FEES_MAX = 2000;
const PAYMENT_FALLBACK_APR = 7.49;
const PAYMENT_FALLBACK_TERM = 72;
const PAYMENT_FALLBACK_DOWN_PCT = 10;
const PAYMENT_FALLBACK_TAX_RATE = 4.5;
const PAYMENT_FALLBACK_DOC_FEES = 599;

const SECTION_COUNT = 7; // dealership, manager, salesperson, assistant, indie, payments, checklist

const EMPTY_STATE: OnboardingState = {
  dealership: {
    name: "",
    location: "",
    streetAddress: "",
    city: "",
    state: "",
    postalCode: "",
    brands: "",
    salesPhone: "",
    website: "",
    logoUrl: "",
    timezone: "America/Chicago",
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
  payments: {
    defaultApr: "",
    defaultTermMonths: "",
    defaultDownPaymentPct: "",
    salesTaxRatePct: "",
    docFees: "",
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
      streetAddress: payload.street_address ?? "",
      city: payload.city ?? "",
      state: payload.state ?? "",
      postalCode: payload.postal_code ?? "",
      brands: payload.main_brands,
      salesPhone: payload.sales_phone,
      website: payload.website,
      logoUrl: payload.logo_url ?? "",
      timezone: payload.dealership_timezone ?? "America/Chicago",
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
    payments: {
      defaultApr:
        payload.default_apr === null || payload.default_apr === undefined
          ? ""
          : String(payload.default_apr),
      defaultTermMonths:
        payload.default_term_months === null ||
        payload.default_term_months === undefined
          ? ""
          : String(payload.default_term_months),
      defaultDownPaymentPct:
        payload.default_down_payment_pct === null ||
        payload.default_down_payment_pct === undefined
          ? ""
          : String(payload.default_down_payment_pct),
      salesTaxRatePct:
        payload.sales_tax_rate_pct === null ||
        payload.sales_tax_rate_pct === undefined
          ? ""
          : String(payload.sales_tax_rate_pct),
      docFees:
        payload.doc_fees === null || payload.doc_fees === undefined
          ? ""
          : String(payload.doc_fees),
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
    street_address: state.dealership.streetAddress,
    city: state.dealership.city,
    state: state.dealership.state,
    postal_code: state.dealership.postalCode,
    dealership_timezone: state.dealership.timezone,
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
    // SESSION_238 — empty string maps to null so the backend
    // treats the field as unset and cards fall back to the
    // payment_engine constants.
    default_apr:
      state.payments.defaultApr.trim() === ""
        ? null
        : Number(state.payments.defaultApr),
    default_term_months:
      state.payments.defaultTermMonths.trim() === ""
        ? null
        : Number(state.payments.defaultTermMonths),
    default_down_payment_pct:
      state.payments.defaultDownPaymentPct.trim() === ""
        ? null
        : Number(state.payments.defaultDownPaymentPct),
    // SESSION_239 — same empty-string maps to null convention.
    sales_tax_rate_pct:
      state.payments.salesTaxRatePct.trim() === ""
        ? null
        : Number(state.payments.salesTaxRatePct),
    doc_fees:
      state.payments.docFees.trim() === ""
        ? null
        : Number(state.payments.docFees),
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

  const { dealership, manager, salesperson, assistant, indie, payments, checklist } = state;
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
  const setPayments = (updater: (prev: PaymentDefaults) => PaymentDefaults) =>
    setState((s) => ({ ...s, payments: updater(s.payments) }));
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
      // SESSION_238 + SESSION_239 — payment defaults section is
      // complete only when all five fields are populated (APR / term
      // / down%, plus the store's tax rate and doc fees). Falling
      // back silently to the module constants is not a real answer.
      Boolean(
        payments.defaultApr.trim() &&
          payments.defaultTermMonths.trim() &&
          payments.defaultDownPaymentPct.trim() &&
          payments.salesTaxRatePct.trim() &&
          payments.docFees.trim(),
      ),
      Object.values(checklist).every(Boolean),
    ].filter(Boolean).length;
    return { sectionsDone, total: SECTION_COUNT };
  }, [dealership, manager, salesperson, assistant, indie, payments, checklist]);

  // SESSION_238 — gate save on the payment-defaults validators so a
  // dealer can't PUT an out-of-range APR / term / down%. Backend
  // validates too; the frontend gate is UX so the button doesn't
  // send a request we already know will 400.
  const paymentDefaultsHasError =
    validatePaymentField(
      payments.defaultApr,
      PAYMENT_APR_MIN,
      PAYMENT_APR_MAX,
      "APR",
    ) !== null ||
    validatePaymentField(
      payments.defaultTermMonths,
      PAYMENT_TERM_MIN,
      PAYMENT_TERM_MAX,
      "Term",
      { integer: true },
    ) !== null ||
    validatePaymentField(
      payments.defaultDownPaymentPct,
      PAYMENT_DOWN_MIN,
      PAYMENT_DOWN_MAX,
      "Down payment",
    ) !== null ||
    validatePaymentField(
      payments.salesTaxRatePct,
      PAYMENT_TAX_RATE_MIN,
      PAYMENT_TAX_RATE_MAX,
      "Sales tax rate",
    ) !== null ||
    validatePaymentField(
      payments.docFees,
      PAYMENT_DOC_FEES_MIN,
      PAYMENT_DOC_FEES_MAX,
      "Doc / admin fee",
    ) !== null;

  const handleSave = async () => {
    if (paymentDefaultsHasError) {
      setSaveStatus("error");
      setSaveError(
        "Fix the payment estimate errors before saving.",
      );
      return;
    }
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
          {/* SESSION_239 — one free-text "Store location" became four
              inputs. The header + assistant prompt still read
              ``store_location``; the backend derives it from these
              four once all are set. Same card, no new section. */}
          <Field
            label="Street address"
            value={dealership.streetAddress}
            onChange={(v) => setDealership({ ...dealership, streetAddress: v })}
            placeholder="1420 Frontage Rd"
          />
          <Field
            label="City"
            value={dealership.city}
            onChange={(v) => setDealership({ ...dealership, city: v })}
            placeholder="Yuma"
          />
          <Field
            label="State"
            value={dealership.state}
            onChange={(v) => setDealership({ ...dealership, state: v })}
            placeholder="AZ"
            helperText="Two-letter US code (AL, AK, AZ, …)."
          />
          <Field
            label="ZIP / postal code"
            value={dealership.postalCode}
            onChange={(v) => setDealership({ ...dealership, postalCode: v })}
            placeholder="85364"
          />
          {/* SESSION_240 (walk finding 28) — time zone picker + live
              local time. Dropdown lists a short common-US set; a
              store on a coast we haven't listed can still save any
              IANA name via the API. The clock beside it re-renders
              once a minute so the operator sees proof the zone they
              picked matches the store's wall clock. */}
          <TimezoneField
            value={dealership.timezone}
            state={dealership.state}
            onChange={(v) =>
              setDealership({ ...dealership, timezone: v })
            }
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

      {/* Section 7 — Payment estimates (SESSION_238) */}
      <PaymentDefaultsSection
        payments={payments}
        onChange={setPayments}
      />

      {/* Section 8 — Pilot checklist */}
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
          disabled={saveStatus === "saving" || paymentDefaultsHasError}
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

// SESSION_238 — payment-defaults block. Three numeric fields with
// dealer-word labels, an effective-value placeholder that reads the
// current fallback aloud ("using 7.49% until you set one"), and a
// live example line for a $12,000 car that mirrors the assistant
// card's est-payment string. The example is fetched from the backend
// (POST /onboarding/payment-preview/) rather than recomputed here so
// there is one formula in the app.
function parseNumericInput(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}

function validatePaymentField(
  raw: string,
  lo: number,
  hi: number,
  label: string,
  { integer = false }: { integer?: boolean } = {},
): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value)) {
    return `${label} must be a number.`;
  }
  if (integer && !Number.isInteger(value)) {
    return `${label} must be a whole number.`;
  }
  if (value < lo || value > hi) {
    return `${label} must be between ${lo} and ${hi}.`;
  }
  return null;
}

function PaymentDefaultsSection({
  payments,
  onChange,
}: {
  payments: PaymentDefaults;
  onChange: (updater: (prev: PaymentDefaults) => PaymentDefaults) => void;
}) {
  const aprError = validatePaymentField(
    payments.defaultApr,
    PAYMENT_APR_MIN,
    PAYMENT_APR_MAX,
    "APR",
  );
  const termError = validatePaymentField(
    payments.defaultTermMonths,
    PAYMENT_TERM_MIN,
    PAYMENT_TERM_MAX,
    "Term",
    { integer: true },
  );
  const downError = validatePaymentField(
    payments.defaultDownPaymentPct,
    PAYMENT_DOWN_MIN,
    PAYMENT_DOWN_MAX,
    "Down payment",
  );
  // SESSION_239 — tax rate and doc fees join the same card.
  const taxError = validatePaymentField(
    payments.salesTaxRatePct,
    PAYMENT_TAX_RATE_MIN,
    PAYMENT_TAX_RATE_MAX,
    "Sales tax rate",
  );
  const feesError = validatePaymentField(
    payments.docFees,
    PAYMENT_DOC_FEES_MIN,
    PAYMENT_DOC_FEES_MAX,
    "Doc / admin fee",
  );

  const anyError = Boolean(
    aprError || termError || downError || taxError || feesError,
  );

  // Debounce the preview so a running edit doesn't fire a request
  // per keystroke. 250 ms is short enough to feel live and long
  // enough to skip most in-flight typing.
  const [preview, setPreview] = useState<PaymentPreviewResponse | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (anyError) {
      setPreview(null);
      setPreviewError(null);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const apr = parseNumericInput(payments.defaultApr);
      const termMonths = parseNumericInput(payments.defaultTermMonths);
      const downPaymentPct = parseNumericInput(payments.defaultDownPaymentPct);
      const taxRate = parseNumericInput(payments.salesTaxRatePct);
      const docFees = parseNumericInput(payments.docFees);
      fetchPaymentPreview({
        apr: apr ?? undefined,
        termMonths: termMonths ?? undefined,
        downPaymentPct: downPaymentPct ?? undefined,
        taxRate: taxRate ?? undefined,
        docFees: docFees ?? undefined,
      })
        .then((response) => {
          if (controller.signal.aborted) return;
          setPreview(response);
          setPreviewError(null);
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          setPreview(null);
          setPreviewError(err instanceof Error ? err.message : String(err));
        });
    }, 250);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [
    anyError,
    payments.defaultApr,
    payments.defaultTermMonths,
    payments.defaultDownPaymentPct,
    payments.salesTaxRatePct,
    payments.docFees,
  ]);

  // SESSION_239 label pass — the three payment-fallback placeholders
  // now read the same way ("default <value>") and none clips at the
  // narrower Term column. The prior mix ("using 7.49%", "default 72",
  // "using 10% u…") had two different verbs and one clip.
  const aprPlaceholder = `default ${PAYMENT_FALLBACK_APR}%`;
  const termPlaceholder = `default ${PAYMENT_FALLBACK_TERM}`;
  const downPlaceholder = `default ${PAYMENT_FALLBACK_DOWN_PCT}%`;
  const taxPlaceholder = `default ${PAYMENT_FALLBACK_TAX_RATE}%`;
  const feesPlaceholder = `default $${PAYMENT_FALLBACK_DOC_FEES}`;

  return (
    <SectionCard
      icon={<DollarSign className="h-4 w-4" />}
      title="Payment estimates"
      subtitle="Your store's numbers for the est. $/mo line on every showroom card and the AI assistant's reply."
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <NumericField
          label="Starting APR for estimates"
          value={payments.defaultApr}
          onChange={(v) => onChange((p) => ({ ...p, defaultApr: v }))}
          placeholder={aprPlaceholder}
          helperText="0–40% range. Sales confirms the real rate at handoff."
          suffix="%"
          error={aprError}
          step="0.01"
        />
        <NumericField
          label="Term (months)"
          value={payments.defaultTermMonths}
          onChange={(v) => onChange((p) => ({ ...p, defaultTermMonths: v }))}
          placeholder={termPlaceholder}
          helperText="12–96 months. Common bands: 36, 48, 60, 72, 84."
          error={termError}
          step="1"
        />
        <NumericField
          label="Down payment (% of price)"
          value={payments.defaultDownPaymentPct}
          onChange={(v) =>
            onChange((p) => ({ ...p, defaultDownPaymentPct: v }))
          }
          placeholder={downPlaceholder}
          helperText="0–50% range. Chat overrides with the buyer's stated down."
          suffix="%"
          error={downError}
          step="0.01"
        />
        {/* SESSION_239 — tax + fees on the same card. Two rows on the
            grid; the sm:grid-cols-3 layout wraps them under the top
            row without adding a new section. */}
        <NumericField
          label="Sales tax rate"
          value={payments.salesTaxRatePct}
          onChange={(v) => onChange((p) => ({ ...p, salesTaxRatePct: v }))}
          placeholder={taxPlaceholder}
          helperText="Combined state + city + county rate on a vehicle sale — not the state rate alone."
          suffix="%"
          error={taxError}
          step="0.01"
        />
        <NumericField
          label="Doc / admin fee"
          value={payments.docFees}
          onChange={(v) => onChange((p) => ({ ...p, docFees: v }))}
          placeholder={feesPlaceholder}
          helperText="Dollar amount. Some states cap this; check yours."
          suffix="$"
          error={feesError}
          step="1"
        />
      </div>
      <div
        className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-4 py-3"
        data-testid="payment-preview"
      >
        <div className="text-[10.5px] font-semibold uppercase tracking-wide text-slate-500">
          Live example — a $12,000 car
        </div>
        <div className="mt-1 text-sm text-brand-ink">
          {anyError ? (
            <span className="text-slate-400">Fix the errors above to see the example.</span>
          ) : previewError ? (
            <span className="text-rose-600">Preview failed: {previewError}</span>
          ) : preview ? (
            <div className="space-y-1">
              <div>
                A $12,000 car would show{" "}
                <span className="font-semibold">{preview.line.label}</span>
              </div>
              {/* SESSION_239 — second line spells out the tax and fee
                  contribution so a dealer can see the $1,139 of "not
                  the sticker price" that this task exists to expose. */}
              <div className="text-xs text-slate-500">
                $
                {preview.price.toLocaleString()} + $
                {preview.line.taxes.toLocaleString(undefined, {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                })}{" "}
                tax + $
                {preview.line.fees.toLocaleString(undefined, {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                })}{" "}
                fees − $
                {preview.line.down_payment.toLocaleString()} down = $
                {preview.line.total_financed.toLocaleString(undefined, {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                })}{" "}
                financed
              </div>
            </div>
          ) : (
            <span className="text-slate-400">Loading example…</span>
          )}
        </div>
      </div>
    </SectionCard>
  );
}

interface NumericFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  helperText?: string;
  suffix?: string;
  error?: string | null;
  step?: string;
}

function NumericField({
  label,
  value,
  onChange,
  placeholder,
  helperText,
  suffix,
  error,
  step,
}: NumericFieldProps) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-semibold text-slate-600">{label}</span>
      <div className="relative flex items-center">
        <input
          type="number"
          inputMode="decimal"
          className={`input pr-9 ${error ? "border-rose-400 focus-visible:ring-rose-300" : ""}`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          step={step}
          aria-invalid={error ? "true" : undefined}
        />
        {suffix ? (
          <span className="pointer-events-none absolute right-3 text-xs text-slate-400">
            {suffix}
          </span>
        ) : null}
      </div>
      {error ? (
        <span className="text-[11px] text-rose-600">{error}</span>
      ) : helperText ? (
        <span className="text-[11px] text-slate-500">{helperText}</span>
      ) : null}
    </label>
  );
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

// SESSION_240 (walk finding 28) — IANA time-zone picker with live
// local time. Common US zones are the visible options; a store on a
// coast we haven't listed can still save any IANA name via the API.
// The clock beside the picker re-renders once a minute so an operator
// sees proof that the zone they chose matches their wall clock.
const TIMEZONE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "America/New_York", label: "Eastern (New York)" },
  { value: "America/Chicago", label: "Central (Chicago)" },
  { value: "America/Denver", label: "Mountain (Denver)" },
  { value: "America/Phoenix", label: "Mountain / Arizona (Phoenix)" },
  { value: "America/Los_Angeles", label: "Pacific (Los Angeles)" },
  { value: "America/Anchorage", label: "Alaska" },
  { value: "Pacific/Honolulu", label: "Hawaii" },
  {
    value: "America/Indiana/Indianapolis",
    label: "Eastern / Indiana (Indianapolis)",
  },
  { value: "America/Detroit", label: "Eastern / Michigan (Detroit)" },
];

// Multi-zone states — the onboarding page says so on screen when the
// selected state spans zones so the operator knows the picker is not
// a lookup that guessed one for them. Matches the "None" returns in
// backend services.store_time.suggest_timezone_for_state.
const MULTI_ZONE_STATES = new Set([
  "FL",
  "IN",
  "KY",
  "MI",
  "ND",
  "SD",
  "TN",
  "TX",
]);

function TimezoneField({
  value,
  state,
  onChange,
}: {
  value: string;
  state: string;
  onChange: (v: string) => void;
}) {
  // Re-render every minute so "It is 3:12 PM at the store right now"
  // stays honest without a WebSocket. A single interval per field
  // is cheap; the parent re-render cost is bounded to this label.
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  const zoneLabel = value
    ? new Intl.DateTimeFormat("en-US", {
        timeZone: value,
        hour: "numeric",
        minute: "2-digit",
      }).format(now)
    : "—";

  const isMultiZoneState = state ? MULTI_ZONE_STATES.has(state) : false;
  // Show the picked zone verbatim in the dropdown even if it isn't
  // in the shortlist — otherwise a store on a coast we haven't listed
  // would see its saved value get reset to Chicago on first render.
  const options = TIMEZONE_OPTIONS.some((opt) => opt.value === value)
    ? TIMEZONE_OPTIONS
    : [...TIMEZONE_OPTIONS, { value, label: value }];

  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-semibold text-slate-600">Time zone</span>
      <select
        className="input appearance-none bg-white"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <span className="text-[11px] text-slate-500">
        It is <strong>{zoneLabel}</strong> at the store right now.
        {isMultiZoneState
          ? " Your state has more than one zone — pick the one your store keeps."
          : null}
      </span>
    </label>
  );
}
