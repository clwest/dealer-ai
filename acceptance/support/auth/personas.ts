// Milestone 20 · Increment 1 (extended at M20.2 / M20.3 / M20.4 /
// M32.3) — persona registry for the acceptance suite. Each persona
// corresponds to a role or set of roles that a journey exercises.
// The `setup` project logs each persona in via the real UI and saves
// storage state; journey projects reuse it.
//
// M20.1 shipped: platform_operator.
// M20.2 adds:   owner, sales_manager.
// M20.3 adds:   recon_manager. (The accounting journey reuses the
//               `owner` persona — dealer_owner is a valid role for
//               the M13/M14/M17 accounting endpoints, no new
//               persona needed.)
// M20.4 adds:   bhph_collector — underlying role is sales_manager
//               because the M12 collections endpoints gate on
//               `IsSalesManagerOrOwnerAtActiveDealership`; the
//               model-level ROLE_COLLECTIONS constant is defined
//               but not wired to any endpoint. Persona name still
//               reflects the operational role.
// M32.3 adds:   f_and_i_manager — first F&I-role-gated journey
//               persona. Consumes the M32.1 CA-list endpoint
//               (F&I-role-gated per M32.0 §5.b D3) and the M32.3
//               `/dealer-ai-f-and-i/incoming` intake page. Uses the
//               real `f_and_i_manager` role at the migration-seeded
//               default dealership; provisioned by
//               `seed_journey_fandi_intake_receipt`.

export type PersonaName =
  | "platform_operator"
  | "owner"
  | "sales_manager"
  | "recon_manager"
  | "bhph_collector"
  | "f_and_i_manager";

export interface Persona {
  name: PersonaName;
  username: string;
  password: string;
  postLoginPath: string;
}

// Credentials MUST match what the corresponding seed_journey_* command
// provisions. Passwords are deliberately deterministic-but-not-real-
// secrets; they only work against the acceptance test DB.
export const PERSONAS: Record<PersonaName, Persona> = {
  platform_operator: {
    name: "platform_operator",
    username: "acceptance-operator",
    password: "acceptance-op-password",
    postLoginPath: "/dealer-ai-admin",
  },
  owner: {
    name: "owner",
    username: "acceptance-owner",
    password: "acceptance-owner-password",
    postLoginPath: "/dealer-ai-overview",
  },
  sales_manager: {
    name: "sales_manager",
    username: "acceptance-sales-manager",
    password: "acceptance-sm-password",
    postLoginPath: "/dealer-ai-overview",
  },
  recon_manager: {
    name: "recon_manager",
    username: "acceptance-recon-manager",
    password: "acceptance-recon-password",
    postLoginPath: "/dealer-ai-overview",
  },
  bhph_collector: {
    name: "bhph_collector",
    username: "acceptance-bhph-collector",
    password: "acceptance-bhph-password",
    postLoginPath: "/dealer-ai-overview",
  },
  f_and_i_manager: {
    name: "f_and_i_manager",
    username: "acceptance-f-and-i-manager",
    password: "acceptance-fandi-password",
    postLoginPath: "/dealer-ai-overview",
  },
};
