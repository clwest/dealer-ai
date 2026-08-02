"""Milestone 18 · Increment 1 (SESSION_147) — synthetic data helpers.

Per MILESTONE_18_PLANNING.md §5.g Option A (user-confirmed at
SESSION_146 open). Helpers that produce unmistakably-synthetic
values for demo-store scenario builders. Three independent safety
layers:

- **VINs** prefixed ``DEMO`` + archetype code — never a valid
  decodable 17-char VIN (real VINs never start with "D" per SAE
  J853 first-character position rules for country/manufacturer
  identifiers, and even if they did, the "DEMO" prefix consumes
  4 chars of the country+manufacturer+plant window).
- **Phones** use the ``555-01xx`` block — reserved by NANP for
  fiction / documentation; never routes to a real number.
- **Emails** use the ``@demo.dealer-ai.example`` domain —
  ``.example`` is one of IANA's reserved special-use TLDs
  (RFC 2606) and never resolves to a mail server that would
  accept a message.

**Determinism.** Every helper is a pure function of its inputs;
re-running an archetype builder with the same seed produces the
same values. Enables ``reset_demo_store`` to yield an identical
canonical starting state on every reset per §5.g reset guarantee.
"""

from __future__ import annotations

import hashlib


# Archetype → 2-char code for VIN prefix. Fixed vocab per §5.b.
_ARCHETYPE_CODE: dict[str, str] = {
    "retail_subprime": "RS",
    "floor_planned": "FP",
    "bhph": "BH",
}


def synthetic_vin(archetype: str, index: int) -> str:
    """Return a 17-char synthetic VIN prefixed ``DEMO`` + archetype code.

    Format: ``DEMO`` (4) + 2-char archetype code + 11 hex chars =
    17 chars total. Deterministic hex derived from ``sha256(archetype
    + str(index))`` so re-running an archetype builder produces
    identical VINs.

    Real 17-char VINs never start with "D" as the first position (SAE
    J853 country codes 1-5 = North America, 6-9 = Oceania/South
    America/Asia, A-C = Africa, J-R = Asia, S-Z = Europe). Even if
    that convention were bypassed, no VIN decoder recognizes
    ``DEMO`` as a valid country+manufacturer prefix — the value is
    unmistakably synthetic on inspection.
    """
    code = _ARCHETYPE_CODE.get(archetype)
    if code is None:
        raise ValueError(
            f"synthetic_vin received unknown archetype={archetype!r}. "
            f"Known archetypes: {sorted(_ARCHETYPE_CODE)}."
        )
    digest = hashlib.sha256(f"{archetype}-{index}".encode("utf-8")).hexdigest()
    return f"DEMO{code}{digest[:11].upper()}"


def synthetic_phone(index: int) -> str:
    """Return a ``555-01xx`` NANP fiction-block phone number.

    The 555-0100 through 555-0199 range is reserved by the North
    American Numbering Plan Administration for fictional / example
    use — no real subscriber can be assigned these numbers, so any
    accidental outbound call or SMS would fail at the carrier
    layer rather than routing to a real person.

    ``index`` is taken modulo 100 so a large archetype still stays
    within the fiction block. Format: ``555-01xx`` (no area code
    prefix; add via archetype builder if needed).
    """
    tail = index % 100
    return f"555-01{tail:02d}"


def synthetic_email(name: str) -> str:
    """Return an ``<slug>@demo.dealer-ai.example`` email address.

    The ``.example`` TLD is reserved by IANA (RFC 2606) for
    documentation and testing; no root nameserver will resolve it,
    so any accidental outbound email fails DNS lookup before
    reaching a mail server. The ``demo.dealer-ai`` subdomain
    is a further namespace marker so a tester or log reader
    instantly recognizes the address as synthetic.

    ``name`` may contain spaces or unusual casing — slugified to
    lowercase alphanumerics separated by dots. Empty / all-non-alpha
    names default to ``anonymous``.
    """
    slug = "".join(
        ch.lower() if ch.isalnum() else "." for ch in name.strip()
    ).strip(".")
    # Collapse consecutive dots.
    while ".." in slug:
        slug = slug.replace("..", ".")
    if not slug:
        slug = "anonymous"
    return f"{slug}@demo.dealer-ai.example"
