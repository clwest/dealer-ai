// Milestone 20 · Increment 1 — persona registry for the acceptance
// suite. Each persona corresponds to a role or set of roles that a
// journey exercises. The `setup` project logs each persona in via the
// real UI and saves storage state; journey projects reuse it.
//
// M20.1 ships one persona (platform_operator) because the canonical
// pilot onboarding journey is the only in-scope journey this
// increment. Additional personas (owner, sales_manager, advisor,
// recon_manager, office_manager, bhph_collector) land alongside their
// journeys in M20.2–M20.4.

export type PersonaName = "platform_operator";

export interface Persona {
  name: PersonaName;
  username: string;
  password: string;
  postLoginPath: string;
}

// Credentials MUST match what the `seed_journey_pilot_onboarding`
// management command provisions. The password is deliberately
// deterministic-but-not-a-real-secret; it is only usable against the
// acceptance test DB.
export const PERSONAS: Record<PersonaName, Persona> = {
  platform_operator: {
    name: "platform_operator",
    username: "acceptance-operator",
    password: "acceptance-op-password",
    postLoginPath: "/dealer-ai-admin",
  },
};
