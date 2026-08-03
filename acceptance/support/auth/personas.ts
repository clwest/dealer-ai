// Milestone 20 · Increment 1 (extended at M20.2) — persona registry
// for the acceptance suite. Each persona corresponds to a role or set
// of roles that a journey exercises. The `setup` project logs each
// persona in via the real UI and saves storage state; journey
// projects reuse it.
//
// M20.1 shipped: platform_operator.
// M20.2 adds:   owner, sales_manager.
// M20.3 adds:   recon_manager. (The accounting journey reuses the
//               `owner` persona — dealer_owner is a valid role for
//               the M13/M14/M17 accounting endpoints, no new
//               persona needed.)
// M20.4 adds:   bhph_collector.

export type PersonaName =
  | "platform_operator"
  | "owner"
  | "sales_manager"
  | "recon_manager";

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
};
