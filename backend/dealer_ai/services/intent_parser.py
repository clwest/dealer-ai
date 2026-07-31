"""Structured intent extraction from a single user message.

Two-stage:
1. Regex pre-pass for high-confidence numeric/keyword fields.
2. LLM call asked to return strict JSON for the remaining fields, given the
   regex hints as additional context (so the LLM doesn't fight the numbers).

The result is a flat dict the chat engine merges into ChatSession.extracted_profile.
Only non-null/non-empty values are merged so we never overwrite known data with None.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Iterable, Optional

from .llm.base import LLMProvider

logger = logging.getLogger(__name__)


# ---- Schema -----------------------------------------------------------------

INTENT_VALUES = (
    "vehicle_search",
    "payment_estimate",
    "compare_vehicles",
    "trade_in",
    "financing_help",
    "service_question",
    "salesperson_handoff",
)

VEHICLE_TYPES = ("truck", "suv", "car", "ev", "van", "hybrid")
CONDITIONS = ("new", "used", "certified", "any")
URGENCIES = ("immediate", "this_week", "this_month", "researching")
CREDIT_RANGES = ("excellent", "good", "fair", "poor", "rebuilding", "unknown")
DRIVETRAINS = ("4WD", "AWD", "RWD", "FWD", "any")

# Fields the parser may emit. Used both as the LLM contract and as the
# allow-list when merging into the session profile.
PROFILE_FIELDS: tuple[str, ...] = (
    "intent",
    "vehicle_type",
    "make",
    "make_lock",
    "model",
    "condition",
    "target_monthly_payment",
    "down_payment",
    "term_months",
    "trade_in",
    "credit_range",
    "urgency",
    "financing_interest",
    "service_interest",
    # Phase 8n — current vehicle anchor for follow-up turns. Set when an
    # ordinal reference ("the first one") resolves against the previous
    # turn's matched_vehicles, when a turn surfaces exactly one matched
    # vehicle, or when the user explicitly names a model/stock that
    # resolves to a single inventory row. Read by pronoun-resolution
    # ("tell me more about it"), image-request, and appointment-request
    # short-circuits so follow-ups stay anchored to the right vehicle.
    "current_vehicle_id",
    "current_vehicle_stock",
    # Phase 8q — drivetrain preference. Canonical values: "4WD" / "AWD"
    # / "RWD" / "FWD". Captured by regex_extract from explicit customer
    # mentions ("4wd", "4x4", "four-wheel drive", "AWD", "all-wheel
    # drive", "RWD", "FWD", "2wd", "4x2"). Honored by
    # build_budget_context as a structural filter so a customer asking
    # for "4WD" is never shown a 4x2 as their primary option.
    "drivetrain",
    # Phase 8r — cash-budget ceiling. Captured by regex_extract from
    # explicit customer mentions like "$17,000 cash", "under $20k",
    # "less than $15,000", "up to $25k", "max $30,000", "budget of
    # $20k". Routed into search_vehicles' existing max_price kwarg in
    # the non-budget keyword search path so over-budget vehicles never
    # surface for a customer who has stated a sticker-price ceiling.
    "max_price",
)


# ---- Regex pre-pass ---------------------------------------------------------

_MONTHLY_PATTERNS = [
    re.compile(
        r"\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(?:/|\s*per\s*|\s*a\s*)\s*(?:mo|month|months)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:around|about|roughly|target(?:ing)?|payment\s+of|payments?\s+of)\s*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(?:/|\s*per\s*|\s*a\s*)?\s*(?:mo|month|months)?\b",
        re.IGNORECASE,
    ),
]

_TERM_YEAR_PATTERN = re.compile(
    r"\b(\d{1,2})\s*(?:-\s*)?(?:year|yr)s?\b", re.IGNORECASE
)
_TERM_MONTH_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(?:-\s*)?months?\b", re.IGNORECASE
)

# Phase 8r — cash-budget / max-sticker patterns. Each capture group 1 is
# the dollar amount; group 2 is the optional `k` multiplier ("17k" → 17000).
# A negative lookahead after the amount rejects monthly forms ("/mo", "per
# month", "a month", "monthly") so "$500/mo" is not mis-captured as
# max_price; the existing _MONTHLY_PATTERNS handles those.
_MAX_PRICE_MONTHLY_GUARD = (
    r"(?!\s*(?:/\s*|per\s+|a\s+|each\s+)?(?:mo|month|monthly)\b)"
)
_MAX_PRICE_PATTERNS = [
    # "$17,000 cash" / "$17k cash" / "17000 in cash" — "cash" is an
    # unambiguous max-price signal so no monthly-guard needed.
    re.compile(
        r"\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k)?\s+(?:in\s+)?cash\b",
        re.IGNORECASE,
    ),
    # "(cash )?budget of $X" / "budget of $20k"
    re.compile(
        r"\b(?:cash\s+)?budget\s+of\s+\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k)?"
        + _MAX_PRICE_MONTHLY_GUARD,
        re.IGNORECASE,
    ),
    # "under / below / less than / no more than $X"
    re.compile(
        r"\b(?:under|below|less\s+than|no\s+more\s+than)\s+\$?\s*"
        r"(\d{1,3}(?:,\d{3})*|\d+)\s*(k)?"
        + _MAX_PRICE_MONTHLY_GUARD,
        re.IGNORECASE,
    ),
    # "up to $X" / "max $X" / "maximum (of) $X"
    re.compile(
        r"\b(?:up\s+to|max(?:imum)?(?:\s+of)?)\s+\$?\s*"
        r"(\d{1,3}(?:,\d{3})*|\d+)\s*(k)?"
        + _MAX_PRICE_MONTHLY_GUARD,
        re.IGNORECASE,
    ),
    # "spend $X" / "spend up to $X"
    re.compile(
        r"\bspend\s+(?:up\s+to\s+)?\$\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k)?"
        + _MAX_PRICE_MONTHLY_GUARD,
        re.IGNORECASE,
    ),
]


_DOWN_PATTERNS = [
    re.compile(
        r"\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k)?\s*(?:dollars?\s+)?down\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"down\s*(?:payment)?\s*(?:of)?\s*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(k)?\b",
        re.IGNORECASE,
    ),
]

_INTENT_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(compare|vs\.?|versus|difference)\b", re.IGNORECASE), "compare_vehicles"),
    (re.compile(r"\b(trade[- ]?in|my\s+(car|truck|suv))\s*(worth|value)", re.IGNORECASE), "trade_in"),
    (re.compile(r"\b(finance|financing|loan|interest rate|apr|approved|approval)\b", re.IGNORECASE), "financing_help"),
    (re.compile(r"\b(service|oil change|recall|maintenance|repair)\b", re.IGNORECASE), "service_question"),
    (re.compile(r"\b(salesperson|sales rep|talk to (someone|a person|a human)|call me|book an? appointment)\b", re.IGNORECASE), "salesperson_handoff"),
    (re.compile(r"\b(payment|monthly|afford|budget)\b", re.IGNORECASE), "payment_estimate"),
    (re.compile(r"\b(show me|looking for|interested in|need|want)\b.*\b(truck|suv|car|ev|hybrid|f-?150|ranger|maverick|bronco|escape|explorer|mustang|mach-?e)\b", re.IGNORECASE), "vehicle_search"),
]

_VEHICLE_TYPE_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(trucks?|pickups?)\b", re.IGNORECASE), "truck"),
    (re.compile(r"\b(suvs?|crossovers?)\b", re.IGNORECASE), "suv"),
    (re.compile(r"\b(evs?|electrics?|all[- ]?electric)\b", re.IGNORECASE), "ev"),
    (re.compile(r"\bhybrids?\b", re.IGNORECASE), "hybrid"),
    (re.compile(r"\b(sedans?|coupes?|cars?)\b", re.IGNORECASE), "car"),
    (re.compile(r"\b(vans?|minivans?)\b", re.IGNORECASE), "van"),
]

# Phase 8q: drivetrain extraction. The customer says "4wd truck" or "AWD
# Bronco Sport" and we capture a canonical token ("4WD" / "AWD" / "RWD"
# / "FWD") into the profile so build_budget_context can apply it as a
# structural filter. Without this, drivetrain hints are silently dropped
# in budget mode and the customer gets shown wrong-drivetrain options.
#
# Phase 8s/UX (lever-accept): a separate "release" canonical "any" lets
# the customer loosen a prior drivetrain constraint mid-conversation.
# Release patterns are listed FIRST so a phrasing like "2WD is fine"
# (intent: drop the 4WD lock) wins over the strict "2wd" lock pattern
# that would otherwise capture drivetrain="RWD".
_DRIVETRAIN_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    # Release patterns — the customer is loosening a prior drivetrain
    # constraint. Map to the "any" sentinel so build_budget_context's
    # drivetrain filter chain falls through to no-filter.
    (
        re.compile(
            r"\b(?:any|all|either|whatever)\s+drive(?:train)?\b",
            re.IGNORECASE,
        ),
        "any",
    ),
    (
        re.compile(
            r"\bdrop\s+(?:the\s+)?(?:4[- ]?wd|4x4|awd|rwd|fwd|drivetrain)\b",
            re.IGNORECASE,
        ),
        "any",
    ),
    (
        re.compile(
            r"\b(?:i'?m\s+)?(?:open|flexible)\s+(?:to|on|with|about)\s+"
            r"(?:the\s+)?drive(?:train)?\b",
            re.IGNORECASE,
        ),
        "any",
    ),
    (
        # "2WD is fine" / "4x2 works" — release a prior 4WD lock. We
        # deliberately omit "fwd"/"rwd" from this pattern: those are
        # explicit car/sedan drivetrains the customer may genuinely
        # be locking, not loosening (test_fwd_phrasings expects "FWD
        # is fine" to remain a strict FWD lock).
        re.compile(
            r"\b(?:2[- ]?wd|4x2)\s+(?:is\s+(?:fine|ok|okay)|"
            r"works?(?:\s+(?:too|also|fine))?|too|also)\b",
            re.IGNORECASE,
        ),
        "any",
    ),
    (
        re.compile(
            r"\bdon'?t\s+need\s+(?:the\s+)?(?:4[- ]?wd|4x4|awd)\b",
            re.IGNORECASE,
        ),
        "any",
    ),
    # Strict locks — customer is naming a specific drivetrain.
    (
        re.compile(
            r"\b4[- ]?wd\b|\b4x4\b|\b(?:four|4)[- ]?wheel\s+drive\b",
            re.IGNORECASE,
        ),
        "4WD",
    ),
    (
        re.compile(
            r"\bawd\b|\ball[- ]?wheel\s+drive\b", re.IGNORECASE
        ),
        "AWD",
    ),
    (
        re.compile(
            # 4x2 / 2wd / RWD / rear-wheel drive — all map to RWD canonical
            # because dealership trucks tagged "4x2" carry drivetrain="RWD"
            # in the seed inventory.
            r"\b4x2\b|\b2[- ]?wd\b|\brwd\b|\brear[- ]?wheel\s+drive\b",
            re.IGNORECASE,
        ),
        "RWD",
    ),
    (
        re.compile(
            r"\bfwd\b|\bfront[- ]?wheel\s+drive\b", re.IGNORECASE
        ),
        "FWD",
    ),
]

_CONDITION_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(certified|cpo)\b", re.IGNORECASE), "certified"),
    (re.compile(r"\b(used|pre[- ]?owned|second[- ]?hand)\b", re.IGNORECASE), "used"),
    (re.compile(r"\bbrand[- ]?new\b", re.IGNORECASE), "new"),
    (re.compile(r"\bnew\b", re.IGNORECASE), "new"),
]

_URGENCY_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(today|right now|immediate|asap|this weekend)\b", re.IGNORECASE), "immediate"),
    (re.compile(r"\bthis week\b", re.IGNORECASE), "this_week"),
    (re.compile(r"\b(this month|next few weeks)\b", re.IGNORECASE), "this_month"),
    (re.compile(r"\b(just (looking|researching|browsing)|not sure yet|window shop)", re.IGNORECASE), "researching"),
]

_MODEL_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bf[- ]?150s?\b", re.IGNORECASE), "F-150"),
    (re.compile(r"\brangers?\b", re.IGNORECASE), "Ranger"),
    (re.compile(r"\bmavericks?\b", re.IGNORECASE), "Maverick"),
    (re.compile(r"\bbronco\s+sports?\b", re.IGNORECASE), "Bronco Sport"),
    (re.compile(r"\bbroncos?\b", re.IGNORECASE), "Bronco"),
    (re.compile(r"\bexplorers?\b", re.IGNORECASE), "Explorer"),
    (re.compile(r"\bescapes?\b", re.IGNORECASE), "Escape"),
    (re.compile(r"\bmach[- ]?es?\b", re.IGNORECASE), "Mustang Mach-E"),
    (re.compile(r"\bmustangs?\b", re.IGNORECASE), "Mustang"),
]

# Model → OEM make so :func:`regex_extract` can infer the make when a
# customer names a model without naming its brand ("show me F-150s"
# implies Ford). Non-Ford models can join this map without touching the
# inference logic; the regex list above stays lean until Phase 2's
# indie-inventory-shape work expands it. If a detected model isn't in
# this map, make inference is skipped (safer than a Ford-shaped
# guess).
_MODEL_TO_MAKE: dict[str, str] = {
    "F-150": "Ford",
    "Ranger": "Ford",
    "Maverick": "Ford",
    "Bronco Sport": "Ford",
    "Bronco": "Ford",
    "Explorer": "Ford",
    "Escape": "Ford",
    "Mustang Mach-E": "Ford",
    "Mustang": "Ford",
}

# Brand-lock detection: triggers when the customer explicitly restricts to a
# single make. Used dealership inventory typically includes other brands too
# (trade-ins, auctions), so the search defaults to all-makes — only filter
# when the customer has clearly said they want only one brand.
_KNOWN_MAKES = (
    "Ford", "Toyota", "Honda", "Chevrolet", "Chevy", "Ram", "Dodge",
    "GMC", "Nissan", "Hyundai", "Kia", "Subaru", "Mazda", "Jeep",
    "Volkswagen", "VW", "BMW", "Audi", "Lexus", "Tesla",
)
_MAKE_ALIAS = {"chevy": "Chevrolet", "vw": "Volkswagen"}
_MAKE_LOCK_PATTERNS = [
    re.compile(rf"\b({'|'.join(_KNOWN_MAKES)})\s+only\b", re.IGNORECASE),
    re.compile(rf"\bonly\s+({'|'.join(_KNOWN_MAKES)})\b", re.IGNORECASE),
    re.compile(rf"\bjust\s+({'|'.join(_KNOWN_MAKES)})\b", re.IGNORECASE),
    re.compile(rf"\bstick\s+(?:with|to)\s+({'|'.join(_KNOWN_MAKES)})\b", re.IGNORECASE),
    re.compile(rf"\bi\s+(?:want|need|prefer)\s+(?:an?\s+)?({'|'.join(_KNOWN_MAKES)})\b", re.IGNORECASE),
    re.compile(rf"\bno\s+(?:other|non)[- ]?({'|'.join(_KNOWN_MAKES)})\b", re.IGNORECASE),
]

# Phase 8s/UX (lever-accept guard) — does the message contain a real
# currency / monthly cue, or is the LLM extracting a budget out of
# thin air? If a numeric profile field comes back from the LLM but
# regex didn't pick it up AND this regex doesn't match either, the
# value is dropped before merge.
_CURRENCY_SIGNAL_RE = re.compile(
    r"\$|"  # explicit dollar sign
    r"\b(?:budget|cash|spend|price|payment|monthly|mo\b|/mo|per\s+mo|"
    r"per\s+month|a\s+month|down(?:\s+payment)?|under|less\s+than|"
    r"up\s+to|max(?:imum)?)\b",
    re.IGNORECASE,
)


_TRADE_IN_HINT = re.compile(r"\b(trade[- ]?in|trading in|my\s+(car|truck|suv|vehicle))\b", re.IGNORECASE)
_FINANCING_HINT = re.compile(r"\b(finance|financing|loan|approved|monthly payment|apr|interest rate)\b", re.IGNORECASE)
_SERVICE_HINT = re.compile(r"\b(service|oil change|recall|maintenance|tires|brakes)\b", re.IGNORECASE)


def _to_int_money(raw: str) -> Optional[int]:
    try:
        return int(raw.replace(",", "").strip())
    except ValueError:
        return None


def _first_match(patterns: Iterable[tuple[re.Pattern[str], str]], text: str) -> Optional[str]:
    for pattern, value in patterns:
        if pattern.search(text):
            return value
    return None


def regex_extract(message: str) -> Dict[str, Any]:
    """Cheap, deterministic pre-pass — used as ground truth for numbers."""
    out: Dict[str, Any] = {}
    if not message:
        return out

    for pattern in _MONTHLY_PATTERNS:
        m = pattern.search(message)
        if m:
            value = _to_int_money(m.group(1))
            if value and 50 <= value <= 5000:
                out["target_monthly_payment"] = value
                break

    for pattern in _DOWN_PATTERNS:
        m = pattern.search(message)
        if m:
            value = _to_int_money(m.group(1))
            if value is not None:
                # k-suffix expansion: "$3k down" / "down 5k" → multiply by 1000.
                if m.group(2):
                    value *= 1000
                if 0 <= value <= 200000:
                    out["down_payment"] = value
                    break

    # Phase 8r — cash-budget / max-sticker capture. Each pattern's
    # negative lookahead rejects monthly forms so "$500/mo" is never
    # mis-captured here. k-suffix expansion mirrors the down-payment
    # logic ("$17k cash" → 17000).
    for pattern in _MAX_PRICE_PATTERNS:
        m = pattern.search(message)
        if m:
            value = _to_int_money(m.group(1))
            if value is not None:
                if m.group(2):
                    value *= 1000
                if 1_000 <= value <= 1_000_000:
                    out["max_price"] = value
                    break

    # Term: years take precedence (clearer signal); months as a backup.
    m = _TERM_YEAR_PATTERN.search(message)
    if m:
        try:
            years = int(m.group(1))
            if 1 <= years <= 8:
                out["term_months"] = years * 12
        except ValueError:
            pass
    if "term_months" not in out:
        m = _TERM_MONTH_PATTERN.search(message)
        if m:
            try:
                months = int(m.group(1))
                if 12 <= months <= 96:
                    out["term_months"] = months
            except ValueError:
                pass

    intent = _first_match(_INTENT_KEYWORDS, message)
    if intent:
        out["intent"] = intent

    vt = _first_match(_VEHICLE_TYPE_KEYWORDS, message)
    if vt:
        out["vehicle_type"] = vt

    cond = _first_match(_CONDITION_KEYWORDS, message)
    if cond:
        out["condition"] = cond

    drivetrain = _first_match(_DRIVETRAIN_KEYWORDS, message)
    if drivetrain:
        out["drivetrain"] = drivetrain

    urg = _first_match(_URGENCY_KEYWORDS, message)
    if urg:
        out["urgency"] = urg

    model = _first_match(_MODEL_KEYWORDS, message)
    if model:
        out["model"] = model
        inferred_make = _MODEL_TO_MAKE.get(model)
        if inferred_make:
            out.setdefault("make", inferred_make)

    # Brand-lock: only fires for explicit single-make requests like "Ford only"
    # or "I want a Toyota". Mentioning a model alone (e.g. "Show me F-150s")
    # does NOT lock the make — the customer might still be open to a
    # comparable trade-in from another brand if it fits.
    for pattern in _MAKE_LOCK_PATTERNS:
        m = pattern.search(message)
        if m:
            raw = m.group(1)
            canonical = _MAKE_ALIAS.get(raw.lower(), raw.title())
            out["make"] = canonical
            out["make_lock"] = True
            break

    if _TRADE_IN_HINT.search(message):
        out["trade_in"] = True
    if _FINANCING_HINT.search(message):
        out["financing_interest"] = True
    if _SERVICE_HINT.search(message):
        out["service_interest"] = True

    return out


# ---- LLM extraction ---------------------------------------------------------

_EXTRACT_PROMPT = """You extract a structured customer profile from a single car-shopping message.

Return ONLY a single JSON object — no prose, no markdown, no code fences.
If a field is not clearly stated or implied, omit it (do not guess).
Use these enums where applicable; otherwise use plain strings/numbers.

Schema:
{
  "intent": "vehicle_search|payment_estimate|compare_vehicles|trade_in|financing_help|service_question|salesperson_handoff",
  "vehicle_type": "truck|suv|car|ev|van|hybrid",
  "make": "Ford|Toyota|Honda|Chevy|Nissan|Kia|Ram|GMC|Hyundai|Jeep|Subaru|...",
  "model": "F-150|Ranger|Maverick|Bronco Sport|Tacoma|Tundra|Silverado|Colorado|Civic|Accord|Camry|Corolla|Altima|Wrangler|...",
  "condition": "new|used|certified|any",
  "target_monthly_payment": 500,
  "down_payment": 2000,
  "trade_in": true,
  "credit_range": "excellent|good|fair|poor|rebuilding|unknown",
  "urgency": "immediate|this_week|this_month|researching",
  "financing_interest": true,
  "service_interest": true
}

Rules:
- Output MUST be valid JSON parseable by json.loads.
- Numbers must be plain integers (no $ or commas).
- Only include fields you are confident about.
- If the user asked something unrelated, output {}.
"""


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _safe_json_loads(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    text = text.strip()
    # Strip common code-fence wrappers if the model ignored instructions.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            logger.debug("intent_parser: LLM output was not valid JSON: %r", text[:200])
            return {}


def _validate(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce + drop fields that don't match the schema."""
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in raw.items():
        if key not in PROFILE_FIELDS:
            continue
        if value in (None, "", []):
            continue
        if key == "intent" and value not in INTENT_VALUES:
            continue
        if key == "vehicle_type" and str(value).lower() not in VEHICLE_TYPES:
            continue
        if key == "condition" and str(value).lower() not in CONDITIONS:
            continue
        if key == "urgency" and str(value).lower() not in URGENCIES:
            continue
        if key == "credit_range" and str(value).lower() not in CREDIT_RANGES:
            continue
        if key == "drivetrain":
            # Canonicalize and validate. Accept both "4wd" and "4WD"
            # case-insensitively; emit canonical uppercase.
            canon = str(value).upper()
            if canon not in DRIVETRAINS:
                continue
            value = canon
        if key in ("target_monthly_payment", "down_payment"):
            try:
                value = int(float(value))
            except (TypeError, ValueError):
                continue
            if value < 0 or value > 1_000_000:
                continue
        if key == "max_price":
            try:
                value = int(float(value))
            except (TypeError, ValueError):
                continue
            if value < 1_000 or value > 1_000_000:
                continue
        if key == "term_months":
            try:
                value = int(float(value))
            except (TypeError, ValueError):
                continue
            if value < 12 or value > 96:
                continue
        if key in ("trade_in", "financing_interest", "service_interest", "make_lock"):
            if isinstance(value, str):
                value = value.strip().lower() in ("true", "yes", "y", "1")
            else:
                value = bool(value)
        if key in ("make", "model"):
            value = str(value).strip()
        if isinstance(value, str):
            value = value.lower() if key in ("intent", "vehicle_type", "condition", "urgency", "credit_range") else value
        out[key] = value
    return out


def parse_intent(
    message: str,
    *,
    provider: Optional[LLMProvider] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """Return a flat dict of extracted profile fields. Empty when nothing is detected."""
    message = (message or "").strip()
    if not message:
        return {}

    regex_hits = regex_extract(message)

    if not use_llm or provider is None:
        return regex_hits

    user_prompt = (
        f"Customer message:\n\"\"\"{message}\"\"\"\n\n"
        f"Regex pre-pass found: {json.dumps(regex_hits)}\n\n"
        "Return the JSON object now."
    )
    try:
        raw = provider.chat(
            [
                {"role": "system", "content": _EXTRACT_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=300,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("intent_parser LLM call failed: %s", exc)
        return regex_hits

    llm_data = _validate(_safe_json_loads(raw))

    # Phase 8s/UX (lever-accept) — guard against LLM hallucinating
    # numeric fields the message doesn't actually carry. Smaller local
    # models (Ollama llama3.1) have been observed emitting
    # target_monthly_payment=84 from "yes try 84 months" because they
    # latched onto the bare number. Regex is ground truth: if regex
    # didn't find a numeric field AND the message has no obvious
    # currency / monthly cue, drop the LLM's value rather than
    # poisoning the profile.
    has_currency_signal = bool(_CURRENCY_SIGNAL_RE.search(message))
    for numeric_field in ("target_monthly_payment", "down_payment", "max_price"):
        if numeric_field in llm_data and numeric_field not in regex_hits:
            if not has_currency_signal:
                llm_data.pop(numeric_field, None)

    # Regex wins on numeric fields (deterministic ground truth).
    merged = {**llm_data, **regex_hits}
    return merged


# ---- Profile merge ----------------------------------------------------------

def merge_profile(
    existing: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Shallow merge, ignoring empty values in `new`. Never drops known data."""
    base = dict(existing or {})
    if not new:
        return base
    for key, value in new.items():
        if key not in PROFILE_FIELDS:
            continue
        if value in (None, "", [], {}):
            continue
        base[key] = value
    return base


# ---- Phase 8s/UX (lever-accept) helpers ------------------------------------

# Bare confirmations the customer types after a lever-offer turn. Without
# the prior turn's context, "yes" doesn't tell us which lever to flex,
# so chat_engine routes these to a clarifier reply rather than guessing.
_BARE_CONFIRMATION_RE = re.compile(
    r"^\s*(?:yes|yeah|yep|yup|sure|ok|okay|sounds good|ok\s+then|alright|"
    r"all\s+right|that\s+works?|let'?s\s+try(?:\s+(?:it|that))?|"
    r"sure\s+thing|why\s+not|please|please\s+do)"
    r"(?:\s+(?:please|thanks|thank\s+you|do\s+that|do\s+it|"
    r"sounds\s+good|that\s+works?|let'?s\s+try))?"
    r"[\s.!?]*$",
    re.IGNORECASE,
)


def is_bare_confirmation(message: str) -> bool:
    """True when the customer typed a short generic agreement (e.g. "yes",
    "sure", "let's try it") with no specific lever named.

    Used by the lever-accept flow: after the assistant offered levers
    (longer term / more down / trade-in / drivetrain flexibility), a
    bare "yes" is ambiguous — chat_engine asks a one-line clarifier
    instead of picking a default lever for the customer.
    """
    return bool(_BARE_CONFIRMATION_RE.match((message or "").strip()))


# Numberless lever asks — the customer has named a lever direction but
# omitted the number (term length / down amount). chat_engine asks for
# the specific value before re-running the search; never reruns blindly.
_LONGER_TERM_NUMBERLESS_RE = re.compile(
    r"\b(?:try|let'?s\s*do|do|go\s*with|stretch\s*(?:to|out))\s+"
    r"(?:a\s+)?(?:longer|extended|bigger)\s+(?:term|loan)\b",
    re.IGNORECASE,
)
_LONGER_TERM_NUMBERLESS_ALT_RE = re.compile(
    r"\b(?:longer|extended)\s+(?:term|loan)(?:\s+(?:please|works?|ok))?\b",
    re.IGNORECASE,
)
_MORE_DOWN_NUMBERLESS_RE = re.compile(
    r"\b(?:put|do|go|add|throw)\s+(?:a\s+)?(?:bit\s+)?more\s+down\b"
    r"|\b(?:i\s+)?(?:can|could|will)\s+(?:put|do|go|add)\s+"
    r"(?:a\s+)?(?:bit\s+)?more\s+down\b"
    r"|\b(?:bigger|larger)\s+down(?:\s*payment)?\b",
    re.IGNORECASE,
)


def lever_intent(message: str) -> Optional[str]:
    """Return the lever name the customer asked for without specifying a
    number, or None.

    Returns:
      - "longer_term" — customer wants a longer term but didn't say which
        ("try a longer term", "longer loan please")
      - "more_down"   — customer wants to put more down but didn't say
        how much ("I can put more down", "bigger down payment")
      - None — message either named a specific number (already handled
        by regex_extract → term_months / down_payment) or didn't ask
        for a lever at all.

    Used by chat_engine to ask one focused clarifier ("How much down can
    you go to?") instead of re-running the search blindly. The numeric
    follow-up answer is then captured by the existing regex paths.
    """
    text = (message or "").strip()
    if not text:
        return None
    # If the message already carries a specific number, defer to
    # regex_extract — those values flow through the normal merge path.
    if regex_extract(text).get("term_months") or regex_extract(text).get(
        "down_payment"
    ):
        return None
    if _LONGER_TERM_NUMBERLESS_RE.search(text) or _LONGER_TERM_NUMBERLESS_ALT_RE.search(
        text
    ):
        return "longer_term"
    if _MORE_DOWN_NUMBERLESS_RE.search(text):
        return "more_down"
    return None
