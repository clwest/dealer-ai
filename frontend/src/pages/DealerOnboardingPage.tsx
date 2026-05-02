// SESSION_008 — onboarding now reads/writes against
// GET|PUT /api/dealer-ai/onboarding/profile/ (singleton).
//
// Single store profile only. Multi-tenant boundaries (and the per-entity
// split sketched in docs/onboarding/ASSISTANT_AGENT_CREATION_ROADMAP.md)
// are deferred. Field shapes mirror the future schema so when the
// Dealership / DealerAssistant migration lands, columns just split.
//
// Frontend keeps camelCase state for ergonomics; transformer functions
// map to/from the snake_case API payload at the boundary.

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Building2,
  CheckCircle2,
  Circle,
  ClipboardList,
  Megaphone,
  Settings,
  Sparkles,
  UserRound,
} from "lucide-react";

import {
  fetchOnboardingProfile,
  saveOnboardingProfile,
  type OnboardingProfilePayload,
} from "@/lib/api";

interface DealershipProfile {
  name: string;
  location: string;
  brands: string;
  salesPhone: string;
  website: string;
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

interface OnboardingState {
  dealership: DealershipProfile;
  manager: ManagerPreferences;
  salesperson: SalespersonProfile;
  assistant: AssistantBehavior;
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

const SECTION_COUNT = 5; // dealership, manager, salesperson, assistant, checklist

const EMPTY_STATE: OnboardingState = {
  dealership: { name: "", location: "", brands: "", salesPhone: "", website: "" },
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
  };
}

type LoadStatus = "loading" | "loaded" | "error";
type SaveStatus = "idle" | "saving" | "saved" | "error";

export default function DealerOnboardingPage() {
  const [state, setState] = useState<OnboardingState>(EMPTY_STATE);
  const [loadStatus, setLoadStatus] = useState<LoadStatus>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

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

  const { dealership, manager, salesperson, assistant, checklist } = state;
  const setDealership = (next: DealershipProfile) =>
    setState((s) => ({ ...s, dealership: next }));
  const setManager = (next: ManagerPreferences) =>
    setState((s) => ({ ...s, manager: next }));
  const setSalesperson = (next: SalespersonProfile) =>
    setState((s) => ({ ...s, salesperson: next }));
  const setAssistant = (next: AssistantBehavior) =>
    setState((s) => ({ ...s, assistant: next }));
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
      Object.values(checklist).every(Boolean),
    ].filter(Boolean).length;
    return { sectionsDone, total: SECTION_COUNT };
  }, [dealership, manager, salesperson, assistant, checklist]);

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
          className="inline-block h-3 w-3 animate-pulse rounded-full bg-ford-blue"
          aria-hidden
        />
        Loading onboarding profile…
      </div>
    );
  }

  if (loadStatus === "error") {
    return (
      <div className="card px-6 py-5">
        <h1 className="text-lg font-bold text-ford-ink">Dealership Onboarding</h1>
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
          className="mt-4 rounded-md bg-ford-blue px-4 py-2 text-sm font-semibold text-white hover:bg-ford-blue/90"
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
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-ford-blue text-white">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-ford-ink">
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
            className="text-sm font-semibold text-ford-accent hover:underline"
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
            placeholder="Freedom Ford"
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
            placeholder="https://freedomford.example.com"
            type="url"
            className="sm:col-span-2"
          />
        </div>
      </SectionCard>

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
            className="text-xs font-semibold text-ford-accent hover:underline"
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
            placeholder="sarah@freedomford.example.com"
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
            placeholder="Hi, I'm Sarah — I've been helping families pick the right Ford for 12 years."
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
            placeholder="Welcome to Freedom Ford. Tell me what you're shopping for…"
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

      {/* Section 6 — Pilot checklist */}
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
                        ? "font-semibold text-ford-ink"
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
        <div className="text-xs text-slate-500">
          <SaveStatusLabel status={saveStatus} error={saveError} />
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saveStatus === "saving"}
          className="rounded-md bg-ford-blue px-5 py-2 text-sm font-semibold text-white transition hover:bg-ford-blue/90 disabled:cursor-not-allowed disabled:bg-slate-300"
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
    return <span className="text-emerald-700">Saved.</span>;
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
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-ford-blue/10 text-ford-blue">
            {icon}
          </div>
          <div>
            <h2 className="text-base font-bold text-ford-ink">{title}</h2>
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
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  multiline = false,
  className = "",
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
    </label>
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
