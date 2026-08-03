"""Milestone 19 · Increment 1 (SESSION_154) — pilot onboarding domain errors.

Per MILESTONE_19_PLANNING.md §5.d Option A + §5.h Option A (user-
confirmed at SESSION_153 open) + §0.a M19.1 decisions.

Domain-error → HTTP mapping (consumed by M19.3 endpoints):

- :class:`PilotAlreadyExistsError` — 409 (slug collision on pilot
  create; either an existing pilot, demo, or live dealership already
  uses the slug).
- :class:`NonPilotTerminationError` — 500 (broken-invariant guard;
  ``terminate_pilot`` should never be called against a non-pilot
  Dealership).
- :class:`PilotReadinessNotConfirmedError` — 409 (advance-step guard;
  ``readiness_confirmed`` cannot be completed before every prior
  step's row exists with ``completed_at`` populated).
"""

from __future__ import annotations


class PilotAlreadyExistsError(ValueError):
    """Raised when a pilot slug collides with an existing Dealership.

    Mapped to HTTP 409 at the endpoint layer — caller-input error.
    The IntegrityError from the DB-level unique constraint is caught
    at the service boundary + re-raised as this domain exception per
    M17 §6 lesson 4 pattern.
    """


class NonPilotTerminationError(RuntimeError):
    """Raised when ``terminate_pilot`` is called against a non-pilot Dealership.

    Belt-and-suspenders guard from §5.h Option A + M18.1
    ``NonDemoResetError`` pattern. Fires as ``RuntimeError`` because
    reaching this state is a programming bug in a demo-store-owned
    caller, not caller input validation.

    Pairs with an ``assert dealership.is_pilot`` at the top of every
    pilot-write verb per M15/M16/M17/M18 broken-invariant-guard
    pattern.
    """


class PilotReadinessNotConfirmedError(ValueError):
    """Raised when advancing ``readiness_confirmed`` before prior steps complete.

    Per §5.f Option A — ``readiness_confirmed`` is the final operator
    sign-off step; the checklist verb refuses to advance it until
    every prior step's row exists with ``completed_at`` populated.
    Mapped to HTTP 409 at the endpoint layer — the operator asked for
    a state transition that the invariants prevent.
    """
