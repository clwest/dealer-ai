// TASK_label-pass §1 + §5 — one place a guard flag or category gets
// its human label. The overview's Recent activity card and the manager
// audit panel both render these; keeping the maps in one module means
// a new scrub only needs an entry here to fix both screens at once.
// The backend guard test ``test_audit_flag_coverage.py`` enforces
// that every flag the services layer emits is categorized in
// ``_FLAG_CATEGORIES``; this file mirrors that surface for display.

export const FLAG_DISPLAY_NAMES: Record<string, string> = {
  // Pre-LLM short-circuits (customer asked something the AI shouldn't
  // answer; deterministic refusal).
  prompt_injection: "Prompt injection attempt",
  rate_inquiry: "Rate / APR question",
  external_value_inquiry: "Blue Book / KBB / trade-in value",
  identity_request: "Identity question (are you real?)",
  negotiation_request: "Price negotiation",
  handoff_request: "Live agent / handoff request",
  image_request: "Picture / image request",
  image_request_needs_vehicle: "Image request (no vehicle context)",
  appointment_request: "Appointment / test drive",
  appointment_request_needs_vehicle: "Appointment (no vehicle context)",
  // Post-LLM wholesale rewrites.
  post_llm_safety_rewrite: "Post-LLM safety rewrite",
  internal_confusion_fallback: "Internal-confusion fallback",
  fabricated_inventory: "Fabricated inventory scrubbed",
  post_llm_override: "Post-LLM override",
  // Post-LLM partial scrubs.
  rate_language_scrubbed: "Rate language scrubbed",
  internal_directive_scrubbed: "Internal directive scrubbed",
  default_assumption_scrubbed: "Default-assumption scrubbed",
  category_label_scrubbed: "Category label scrubbed",
  meta_narration_scrubbed: "Meta-narration scrubbed",
  list_shape_scrubbed: "List shape scrubbed",
  banned_phrase_scrubbed: "Banned phrase scrubbed",
  payment_drift_scrubbed: "Payment drift scrubbed",
  extra_payment_quote_scrubbed: "Extra payment quote scrubbed",
  followup_question_scrubbed: "Follow-up question scrubbed",
  generic_use_case_scrubbed: "Generic use-case scrubbed",
  followup_anchors_scrubbed: "Follow-up anchors scrubbed",
  drivetrain_claim_scrubbed: "Drivetrain claim scrubbed",
  financing_language_scrubbed: "Financing language scrubbed",
  fallback_stall_scrubbed: "Fallback stall scrubbed",
  both_wording_scrubbed: '"Both" wording rewritten',
  multiple_scrubs_fired: "Multiple scrubs fired",
  // Upstream provider outage — not a guard action.
  provider_unavailable: "AI provider unavailable",
};

export const CATEGORY_LABELS: Record<string, string> = {
  pre_llm_guard: "Pre-LLM guard",
  post_llm_rewrite: "Post-LLM rewrite",
  post_llm_override: "Post-LLM override",
  scrub: "Partial scrub",
  provider_outage: "Provider outage",
  unknown: "Other",
};

/** Human label for a flag, with a title-cased fallback. */
export function flagDisplayName(flag: string): string {
  return FLAG_DISPLAY_NAMES[flag] ?? titleCase(flag);
}

/** Human label for a category, with a title-cased fallback. */
export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? titleCase(category);
}

function titleCase(token: string): string {
  return token
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase());
}
