"""SESSION_232 — TASK_de-ford-the-kit Part 3+4.

Deterministic drivetrain / exterior color / image_url derivation for
seeded vehicles. The seed fills the fields the showroom and assistant
cards were built against; the placeholder SVGs live under
``dealer_ai/static/dealer_ai/placeholders/`` and are served through
Django's ``STATIC_URL`` (dev: proxied by Vite's ``/static`` route).

Every function is a pure derivation of stock / trim / body_style so
re-seeding the store yields identical values. Kept out of any archetype
module so both the archetype builders and the auto-demo expansion
importer route through the same rules.
"""

from __future__ import annotations

from django.templatetags.static import static


# Yuma indie lot palette — colours a small used store would actually
# carry. Deterministic pick by stock-number hash.
_EXTERIOR_COLORS: tuple[str, ...] = (
    "White",
    "Silver",
    "Gray",
    "Black",
    "Blue",
    "Red",
    "Tan",
)

# Body-style → placeholder file name. EVs share the car silhouette.
_PLACEHOLDER_BY_BODY: dict[str, str] = {
    "car": "car.svg",
    "suv": "suv.svg",
    "truck": "truck.svg",
    "van": "van.svg",
    "ev": "car.svg",
}


def _stock_parity(stock: str) -> int:
    """Stable 0/1 from the numeric tail of a stock number (falls back
    to summed char codes if there is no numeric tail)."""
    digits = "".join(ch for ch in stock if ch.isdigit())
    if digits:
        return int(digits) % 2
    return sum(ord(c) for c in stock) % 2


def derive_drivetrain(*, stock: str, trim: str, model: str, body_style: str) -> str:
    """Never blank. Trim/model strings that already announce AWD, 4WD,
    4x4 or 4×4 pass through; the rest split by body class and stable
    stock parity."""
    haystack = f"{trim or ''} {model or ''}".lower()
    if "4x4" in haystack or "4×4" in haystack or "4wd" in haystack:
        return "4WD"
    if "awd" in haystack:
        return "AWD"
    parity = _stock_parity(stock)
    if body_style == "truck":
        return "4WD" if parity == 0 else "RWD"
    if body_style == "suv":
        return "AWD" if parity == 0 else "FWD"
    # Cars, EVs, vans, and anything else default FWD (the honest
    # majority for the lot's price band).
    return "FWD"


def derive_exterior_color(*, stock: str) -> str:
    """Never blank. Deterministic pick from the store's palette."""
    key = sum(ord(c) for c in stock)
    return _EXTERIOR_COLORS[key % len(_EXTERIOR_COLORS)]


def derive_image_url(*, body_style: str) -> str:
    """Return the STATIC_URL-qualified placeholder for ``body_style``.
    Never blank — unrecognised body styles fall through to the ``car``
    silhouette."""
    filename = _PLACEHOLDER_BY_BODY.get(body_style, "car.svg")
    return static(f"dealer_ai/placeholders/{filename}")
