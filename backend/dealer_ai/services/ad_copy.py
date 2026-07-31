"""Manager Phase 3: deterministic ad-copy generation pipeline.

Orchestrates the Demand → Recommendation → Ad Draft loop:

1. Resolve real Vehicle + inventory context for a recommendation card.
2. Build a tightly-scoped prompt: dealership voice, W.A.C. compliance,
   no APR/rate/dealer-cost language, no fabricated discounts/rebates.
3. Call the LLM provider (Ollama default, OpenAI optional, MockLLMProvider
   in tests). Ask for a JSON array of 2–3 variants.
4. Run the **same post-LLM safety stack the chat path uses** on every
   variant: ``detect_unsafe_response`` → ``scrub_post_llm_override`` →
   ``scrub_rate_language`` → ``scrub_internal_directives``. Variants
   that hard-rewrite to a guard response are dropped from the output;
   variants that lose only inline directives stay (with the scrub list
   surfaced for the manager).

This is a **read endpoint** — nothing here writes Vehicle, Lead, Session,
or Message state. The caller is expected to copy/edit the variants by
hand. No auto-publish, no Facebook/Google Ads API.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import QuerySet

from ..models import Vehicle
from .dealer_config import get_dealer_name
from .llm.base import LLMProvider
from .llm.factory import get_llm_provider
from .llm_safety import apply_post_llm_scrubs

logger = logging.getLogger(__name__)


def _render(template: str) -> str:
    """Format a dealer-templated string with the current dealer name.

    The ad-copy prompt embeds a literal JSON schema (real ``{`` / ``}``
    braces) so :py:meth:`str.format` would misfire. We instead use a
    distinctive ``{{DEALER_NAME}}`` token and substitute via
    :py:meth:`str.replace` — the same convention ``follow_up.py`` uses
    for its ``{{TONE_NOTE}}`` / ``{{DRAFT_COUNT}}`` tokens.
    """
    return template.replace("{{DEALER_NAME}}", get_dealer_name())


SUPPORTED_CATEGORIES: tuple[str, ...] = ("inventory", "marketing")
DEFAULT_VARIANT_COUNT = 3
MIN_VARIANT_COUNT = 2
MAX_VEHICLE_CONTEXT = 3


# ---- Vehicle resolution -----------------------------------------------------


@dataclass
class AdCopyContext:
    """Resolved real-data context handed to the LLM. Never contains
    invented numbers — every field traces back to a Vehicle row or the
    recommendation evidence."""

    recommendation_id: str
    category: str
    title: str
    explanation: str
    action_text: str
    evidence: dict
    vehicles: List[Vehicle]
    band_label: Optional[str] = None
    monthly_low: Optional[int] = None
    monthly_high: Optional[int] = None
    price_low: Optional[int] = None
    price_high: Optional[int] = None
    model_hint: Optional[str] = None


def _resolve_vehicles_for_recommendation(
    recommendation: dict, *, vehicle_id: Optional[int], dealership
) -> List[Vehicle]:
    """Return a small set of real, available vehicles to anchor the ad copy.

    Milestone 1 · Increment 4D — every ``Vehicle.objects`` query is
    tenant-scoped via ``dealership=``. An owner at Dealership A cannot
    reference Dealership B's vehicles even when supplying an explicit
    ``vehicle_id``.

    Resolution order:

    1. ``vehicle_id`` → exact match if present, available, and in the
       caller's dealership.
    2. Inventory recommendation with ``evidence.band_label`` → top
       primary-make-first vehicles whose price falls in the band
       (indie mixed-lot: newest / cheapest first, no OEM bias).
    3. Marketing recommendation with ``evidence.model`` → top units of
       that model in available inventory.
    4. Marketing recommendation with ``evidence.stock_number`` → that
       specific unit (highlight cards).
    5. Otherwise → empty list (caller signals via warnings).
    """
    if vehicle_id is not None:
        try:
            v = Vehicle.objects.get(
                pk=vehicle_id, dealership=dealership, is_available=True
            )
            return [v]
        except Vehicle.DoesNotExist:
            return []

    evidence = recommendation.get("evidence") or {}
    category = recommendation.get("category")

    if category == "inventory":
        # Inventory recs include numeric band edges via the recommendation
        # cta.params. Prefer those when present; otherwise fall back to
        # parsing band_label.
        cta = recommendation.get("cta") or {}
        params = cta.get("params") or {}
        monthly_low = params.get("monthly_low")
        monthly_high = params.get("monthly_high")
        price_low, price_high = _payment_band_to_price_range(
            monthly_low=monthly_low, monthly_high=monthly_high
        )
        if price_low is None:
            return []
        qs: QuerySet[Vehicle] = Vehicle.objects.filter(
            dealership=dealership, is_available=True
        )
        if price_high is not None:
            qs = qs.filter(
                price__gte=Decimal(str(price_low)),
                price__lte=Decimal(str(price_high)),
            )
        else:
            qs = qs.filter(price__gte=Decimal(str(price_low)))
        return _primary_make_first_top(qs, MAX_VEHICLE_CONTEXT)

    if category == "marketing":
        stock_number = evidence.get("stock_number")
        if stock_number:
            try:
                return [
                    Vehicle.objects.get(
                        stock_number=stock_number,
                        dealership=dealership,
                        is_available=True,
                    )
                ]
            except Vehicle.DoesNotExist:
                return []
        model = evidence.get("model") or evidence.get("vehicle_type")
        if model:
            qs = Vehicle.objects.filter(
                dealership=dealership,
                is_available=True,
                model__icontains=model,
            )
            return _primary_make_first_top(qs, MAX_VEHICLE_CONTEXT)

    return []


def _payment_band_to_price_range(
    *, monthly_low: Any, monthly_high: Any
) -> tuple[Optional[int], Optional[int]]:
    """Convert a band's monthly edges to a sticker-price range using the
    same math the demand panel uses. Returns (price_low, price_high) or
    (None, None) when no usable edges are supplied.

    Imported lazily to avoid a circular import — pipeline.py imports
    chat_engine indirectly via this module's scrub helpers, and we don't
    want the pipeline → ad_copy → pipeline cycle at module load."""
    from .pipeline import _band_price_range  # local import; see docstring

    if monthly_low is None and monthly_high is None:
        return None, None
    band = {
        "monthly_low": int(monthly_low) if monthly_low is not None else 0,
        "monthly_high": int(monthly_high) if monthly_high is not None else None,
    }
    return _band_price_range(band)


def _primary_make_first_top(qs: QuerySet[Vehicle], limit: int) -> List[Vehicle]:
    """Pull a small set, then sort primary-make-first / newest / cheapest
    in Python. Mirrors the chat path's ranking preference so ad copy
    leads with the dealership's primary brand when one is configured
    (franchise config); indie mixed-lot has no OEM bias so ranking
    falls back to newest-year / cheapest."""
    from .dealer_config import get_dealer_profile

    primary_make_lc = (get_dealer_profile().primary_make or "").strip().lower()

    rows = list(qs.order_by("-year", "price")[: limit * 4])

    def _make_key(v: Vehicle) -> int:
        if not primary_make_lc:
            return 0
        return 0 if (v.make or "").strip().lower() == primary_make_lc else 1

    rows.sort(
        key=lambda v: (
            _make_key(v),
            -int(v.year or 0),
            float(v.price),
        )
    )
    return rows[:limit]


# ---- Prompt construction ----------------------------------------------------


_AD_SYSTEM_PROMPT = """You are a marketing copywriter for {{DEALER_NAME}}.
You write short, honest ad drafts that a manager will review and edit
before posting.

Hard rules — these are non-negotiable, the system will reject violations:
- Use ONLY facts from the CONTEXT block below. Never invent specs, financing
  offers, rebates, prices, mileage, features, or warranty terms.
- NEVER state or imply a specific interest rate, APR, financing percentage,
  or "as low as X%". Always use "with approved credit (W.A.C.)" if you
  reference monthly payments at all.
- NEVER mention dealer cost, invoice price, internal margin, holdback,
  acquisition cost, or any non-public pricing.
- NEVER fabricate discounts, rebates, "save $X today", "limited time",
  trade allowances, or competitor price-match guarantees. The dealership
  has not authorized any such promotion in this draft.
- NEVER promise availability, a guaranteed appointment time, a specific
  approval, or any commitment a real advisor would have to confirm.
- Mention an "estimated" payment ONLY if the CONTEXT shows one — and quote
  it verbatim with the W.A.C. qualifier and the term length.
- If the CONTEXT shows a real Stock # for a vehicle, you may cite it. Do
  NOT invent stock numbers.

Tone: friendly, plain-spoken, low-pressure. Short copy a manager can drop
into Facebook, Instagram, an email blast, or a Google search ad.

Output format — return ONLY a JSON array, no prose, no markdown fences:

[
  {
    "platform_hint": "facebook" | "instagram" | "email" | "google_search" | "showroom",
    "headline": "<= 8 words",
    "body": "<= 220 characters, 1-2 short sentences",
    "cta": "<= 6 words"
  },
  ...
]

Produce 3 variants total, each targeting a different platform.
"""


def _format_recommendation_block(rec: dict) -> str:
    lines = [
        "RECOMMENDATION (drives this ad — do NOT echo the labels):",
        f"- Category: {rec.get('category', 'unknown')}",
        f"- Title: {rec.get('title', '')}",
        f"- Explanation: {rec.get('explanation', '')}",
        f"- Suggested action: {rec.get('action_text', '')}",
    ]
    evidence = rec.get("evidence") or {}
    if evidence:
        lines.append("- Evidence:")
        for k, v in evidence.items():
            lines.append(f"    · {k}: {v}")
    return "\n".join(lines)


def _format_vehicle_block(vehicles: List[Vehicle]) -> str:
    if not vehicles:
        return (
            "VEHICLES: none specifically attached. Keep claims generic to "
            "the dealership's inventory range; do NOT invent specific units."
        )
    lines = ["VEHICLES (real, available inventory — use these facts only):"]
    for v in vehicles:
        bits = [
            f"{v.display_name}",
            f"Stock #{v.stock_number}",
            f"{v.condition.upper()}",
            f"${float(v.price):,.0f}",
        ]
        if v.mileage is not None:
            bits.append(f"{v.mileage:,} mi")
        if v.drivetrain:
            bits.append(v.drivetrain)
        if v.engine:
            bits.append(v.engine)
        feature_preview = ", ".join(map(str, (v.features or [])[:4]))
        line = "- " + " | ".join(bits)
        if feature_preview:
            line += f" | features: {feature_preview}"
        lines.append(line)
    return "\n".join(lines)


def build_messages(rec: dict, vehicles: List[Vehicle]) -> List[Dict[str, str]]:
    user_request = (
        "Generate the JSON array of ad variants now. 3 variants. Real data only."
    )
    return [
        {"role": "system", "content": _render(_AD_SYSTEM_PROMPT)},
        {"role": "system", "content": _format_recommendation_block(rec)},
        {"role": "system", "content": _format_vehicle_block(vehicles)},
        {"role": "user", "content": user_request},
    ]


# ---- LLM output parsing -----------------------------------------------------


_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _parse_variants(raw: str) -> List[dict]:
    """Parse the model's reply into a list of variant dicts. Tolerates
    code-fence wrappers and prose around the JSON array. Returns [] when
    no parse is possible."""
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    candidates: List[str] = [text]
    m = _JSON_ARRAY_RE.search(text)
    if m:
        candidates.append(m.group(0))
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            return [v for v in data if isinstance(v, dict)]
    return []


_PLATFORMS_ALLOWED = {"facebook", "instagram", "email", "google_search", "showroom"}


def _normalize_variant(variant: dict, *, default_platform: str) -> Optional[dict]:
    """Coerce the variant fields to the contract. Returns None if the
    variant is missing required content."""
    headline = str(variant.get("headline") or "").strip()
    body = str(variant.get("body") or "").strip()
    cta = str(variant.get("cta") or "").strip()
    if not headline or not body:
        return None
    platform = str(variant.get("platform_hint") or default_platform).strip().lower()
    if platform not in _PLATFORMS_ALLOWED:
        platform = default_platform
    return {
        "platform_hint": platform,
        "headline": headline[:120],
        "body": body[:600],
        "cta": cta[:60] or "Learn more",
    }


# ---- Safety pipeline --------------------------------------------------------


def _scrub_variant(variant: dict) -> tuple[Optional[dict], List[str]]:
    """Run the shared post-LLM safety stack on a variant's three fields.

    Returns (cleaned_variant_or_none, scrubs_fired). Returns (None, [...])
    when a wholesale rewrite fires on any field — the variant is dropped
    rather than rendering GUARD_RESPONSE / NEGOTIATION_RESPONSE /
    HANDOFF_RESPONSE as ad copy.

    Delegates to :func:`services.llm_safety.apply_post_llm_scrubs` with
    ``kind="ad"`` so the same scrub stack the chat path uses applies here,
    plus the marketing-specific ``invented_promotion`` scrub.
    """
    scrubs: List[str] = []
    cleaned = dict(variant)

    for field in ("headline", "body", "cta"):
        text = cleaned.get(field, "")
        cleaned_text, scrubs_for_field, dropped_reason = apply_post_llm_scrubs(
            text, kind="ad"
        )
        if dropped_reason is not None:
            return None, scrubs + [f"{dropped_reason}:{field}"]
        cleaned[field] = cleaned_text.strip()
        for s in scrubs_for_field:
            scrubs.append(f"{s}:{field}")

    # Drop variants that scrubbed to empty content (defensive).
    if not cleaned.get("headline") or not cleaned.get("body"):
        return None, scrubs + ["empty_after_scrub"]

    return cleaned, scrubs


# ---- Public entry -----------------------------------------------------------


@dataclass
class AdCopyResult:
    recommendation_id: str
    variants: List[dict]
    warnings: List[str]
    vehicles_used: List[Vehicle]


def generate_ad_copy(
    *,
    recommendation: dict,
    vehicle_id: Optional[int] = None,
    provider: Optional[LLMProvider] = None,
    dealership=None,
) -> AdCopyResult:
    """Generate 2–3 ad variants for a recommendation. Pure orchestration —
    raises ValueError on contract violations the caller (the view) is
    responsible for translating into 4xx responses.

    Milestone 1 · Increment 4D — tenant-scoped. ``dealership=None``
    resolves to the seeded default (backwards compat for tests
    predating multi-tenancy); the admin view passes
    ``dealership=get_current_dealership(request)``.
    """
    from .tenancy import get_default_dealership

    d = dealership or get_default_dealership()

    if not isinstance(recommendation, dict):
        raise ValueError("recommendation must be an object")
    rec_id = recommendation.get("id")
    if not isinstance(rec_id, str) or not rec_id:
        raise ValueError("recommendation.id is required")
    category = recommendation.get("category")
    if category not in SUPPORTED_CATEGORIES:
        raise ValueError(
            f"category must be one of {SUPPORTED_CATEGORIES}; got {category!r}"
        )

    warnings: List[str] = []
    vehicles = _resolve_vehicles_for_recommendation(
        recommendation, vehicle_id=vehicle_id, dealership=d
    )
    if vehicle_id is not None and not vehicles:
        warnings.append(
            "Specified vehicle_id was not found or is not available — "
            "generating without a specific unit."
        )
    elif not vehicles:
        warnings.append(
            "No matching inventory was resolved for this recommendation — "
            "the draft references the dealership's general inventory only."
        )

    provider = provider or get_llm_provider()
    messages = build_messages(recommendation, vehicles)

    try:
        raw = provider.chat(messages, temperature=0.7, max_tokens=900)
    except Exception as exc:  # noqa: BLE001 — surface to caller as warning
        logger.warning("ad_copy LLM call failed: %s", exc)
        return AdCopyResult(
            recommendation_id=rec_id,
            variants=[],
            warnings=warnings + [f"LLM call failed: {exc}"],
            vehicles_used=vehicles,
        )

    parsed = _parse_variants(raw)
    if not parsed:
        warnings.append(
            "LLM did not return a parseable JSON array of variants. "
            "Manager should retry or compose copy manually."
        )

    default_platforms = ("facebook", "instagram", "email", "google_search")
    cleaned_variants: List[dict] = []
    drops = 0
    for idx, raw_variant in enumerate(parsed):
        normalized = _normalize_variant(
            raw_variant,
            default_platform=default_platforms[idx % len(default_platforms)],
        )
        if normalized is None:
            drops += 1
            continue
        scrubbed, scrubs = _scrub_variant(normalized)
        if scrubbed is None:
            drops += 1
            warnings.append(
                f"Variant #{idx + 1} dropped by safety stack: {', '.join(scrubs) or 'unspecified'}."
            )
            continue
        scrubbed["scrubs_fired"] = scrubs
        cleaned_variants.append(scrubbed)

    if drops > 0:
        logger.info(
            "ad_copy: %d variant(s) dropped by safety scrub for rec=%s",
            drops,
            rec_id,
        )

    if len(cleaned_variants) < MIN_VARIANT_COUNT:
        warnings.append(
            f"Only {len(cleaned_variants)} variant(s) survived safety review. "
            "Manager can retry to get more options."
        )

    # Cap at 3 even if the LLM returned more.
    cleaned_variants = cleaned_variants[:DEFAULT_VARIANT_COUNT]

    return AdCopyResult(
        recommendation_id=rec_id,
        variants=cleaned_variants,
        warnings=warnings,
        vehicles_used=vehicles,
    )
