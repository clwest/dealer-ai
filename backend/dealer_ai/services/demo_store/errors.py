"""Milestone 18 · Increment 1 (SESSION_147) — demo-store domain errors.

Per MILESTONE_18_PLANNING.md §5.c Option A (user-confirmed at
SESSION_146 open). The demo-store service exposes RuntimeError
subclasses for broken-invariant guards — a caller reaching one of
these means a programming bug in a demo-store write path, not user
input error.

Domain-error → HTTP mapping (consumed by M18.5 endpoints):

- :class:`NonDemoResetError` — 500 (never surface to user; signals
  bug that any demo-store write path was called against a
  ``Dealership`` where ``is_demo=False``).
"""

from __future__ import annotations


class NonDemoResetError(RuntimeError):
    """Raised when a demo-store write path is called against a non-demo Dealership.

    Belt-and-suspenders guard from §5.c Option A. The service verbs
    hard-refuse any write against a Dealership where ``is_demo=False``
    to prevent an accidental reset of a real (or would-be real)
    dealership. Fires as ``RuntimeError`` because reaching this state
    is a programming bug in a demo-store caller, not caller input
    validation.

    Pairs with an ``assert dealership.is_demo`` at the top of every
    demo-store write verb per M15/M16/M17 broken-invariant-guard
    pattern.
    """
