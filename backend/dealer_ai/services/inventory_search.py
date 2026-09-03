"""V1 inventory search — Django ORM keyword matching.

PGVector semantic search will replace the scoring step in V2. The
public surface (`search_vehicles`) stays the same so the chat engine
doesn't need to change.

SESSION_232 — TASK_chat-vocabulary-from-inventory + TASK_de-ford-the-kit:
the vocabulary the parser uses for make/model/body_style/drivetrain
comes from the dealership's own visible inventory, not a hardcoded
Ford-franchise map. Generic body-style / condition / drivetrain tokens
stay in :data:`GENERIC_TOKEN_SIGNALS` — a store with zero EVs still
gets "electric" parsed correctly (to the honest empty result).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional

from django.core.cache import cache
from django.db.models import Q

from ..models import Vehicle


# Generic tokens that never depend on a specific store's inventory.
# Split off from the old KEYWORD_SIGNALS so nobody re-adds a model
# name here — the name is intentionally not "KEYWORD" anything.
GENERIC_TOKEN_SIGNALS: Dict[str, Dict[str, str]] = {
    "truck": {"body_style": "truck"},
    "trucks": {"body_style": "truck"},
    "pickup": {"body_style": "truck"},
    "suv": {"body_style": "suv"},
    "ev": {"body_style": "ev"},
    "electric": {"body_style": "ev"},
    "van": {"body_style": "van"},
    "minivan": {"body_style": "van"},
    "sedan": {"body_style": "car"},
    "car": {"body_style": "car"},
    "used": {"condition": "used"},
    "pre-owned": {"condition": "used"},
    "preowned": {"condition": "used"},
    "new": {"condition": "new"},
    "certified": {"condition": "certified"},
    "cpo": {"condition": "certified"},
    "4x4": {"drivetrain_icontains": "4"},
    "4wd": {"drivetrain_icontains": "4"},
    "awd": {"drivetrain_icontains": "AWD"},
}


# Small, brand-agnostic aliases a shopper is likely to type. The only
# hardcoded proper-noun table in the module — no franchise vocabulary
# lives here.
_MAKE_ALIASES: Dict[str, str] = {
    "chevy": "chevrolet",
    "vw": "volkswagen",
    "benz": "mercedes-benz",
    "mercedes": "mercedes-benz",
    "ram": "ram",
    "dodge": "dodge",
    "gmc": "gmc",
    "mb": "mercedes-benz",
    "bmw": "bmw",
}


@dataclass
class SearchFilters:
    keywords: List[str]
    body_style: Optional[str] = None
    condition: Optional[str] = None
    model: Optional[str] = None
    model_contains: Optional[str] = None
    drivetrain_contains: Optional[str] = None
    max_price: Optional[float] = None
    min_year: Optional[int] = None
    make: Optional[str] = None


# Capture the number AND an optional 'k' multiplier so "under 65k" and
# "under $65,000" both work the way customers actually type.
PRICE_PATTERNS = [
    re.compile(r"(?:under|below|less\s+than|<)\s*\$?\s*([\d,]+)\s*(k?)", re.IGNORECASE),
]
YEAR_PATTERN = re.compile(r"(20\d{2})\s*(?:or newer|\+)?", re.IGNORECASE)


def _singular(token: str) -> str:
    """Cheap plural strip — 'trucks' → 'truck', 'silverados' → 'silverado'."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _normalise_model_token(token: str) -> str:
    """Fold spaces / hyphens / cases so 'f150', 'f-150', 'f 150' collapse
    to the same key; likewise 'cr-v'/'crv'/'cr v' → 'crv'."""
    return re.sub(r"[\s\-]+", "", token.strip().lower())


_VOCAB_CACHE_TTL_SECONDS = 300  # 5 minutes — the lot changes a few times a day.


def inventory_vocabulary(dealership) -> Dict[str, Dict[str, str]]:
    """Return a token → signal map built from ``dealership``'s
    customer-visible vehicles.

    - Every distinct ``make`` becomes a make-filter token, plus its
      generic short forms in :data:`_MAKE_ALIASES`.
    - Every distinct ``model`` becomes a ``model_iexact`` token, keyed
      by :func:`_normalise_model_token` so "f-150", "f150", "F 150" all
      hit the same row.
    - Every distinct ``body_style`` and ``drivetrain`` value adds a
      structural filter.

    Cached per dealership for :data:`_VOCAB_CACHE_TTL_SECONDS`. The
    cache key includes the dealership pk so multi-tenant queries never
    see another store's vocabulary.
    """
    from .chat_engine import customer_visible_vehicles

    cache_key = f"inventory_vocab:v1:{dealership.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    vocab: Dict[str, Dict[str, str]] = {}

    qs = customer_visible_vehicles().filter(dealership=dealership)
    makes = {(m or "").strip() for m in qs.values_list("make", flat=True) if m}
    models = {(m or "").strip() for m in qs.values_list("model", flat=True) if m}
    body_styles = {
        (b or "").strip()
        for b in qs.values_list("body_style", flat=True)
        if b
    }
    drivetrains = {
        (d or "").strip()
        for d in qs.values_list("drivetrain", flat=True)
        if d
    }

    for make in makes:
        key = make.lower()
        vocab[key] = {"make": make}
    for alias, canonical in _MAKE_ALIASES.items():
        for make in makes:
            if make.lower() == canonical:
                vocab[alias] = {"make": make}
                break

    for model_value in models:
        key = _normalise_model_token(model_value)
        if key:
            vocab[key] = {"model_iexact": model_value}
        # SESSION_232 addendum — also register the head word of a
        # multi-word model. "Silverado 1500" → head "silverado" →
        # ``model_icontains`` "Silverado" so a shopper who types
        # "silverados" (singular "silverado") hits the row without
        # having to spell out the trim/generation suffix.
        parts = model_value.strip().split()
        if len(parts) > 1:
            head_token = _normalise_model_token(parts[0])
            if head_token and head_token not in vocab:
                vocab[head_token] = {"model_icontains": parts[0]}

    for body in body_styles:
        vocab[body.lower()] = {"body_style": body}

    for drivetrain in drivetrains:
        vocab[drivetrain.lower()] = {"drivetrain_icontains": drivetrain}

    cache.set(cache_key, vocab, timeout=_VOCAB_CACHE_TTL_SECONDS)
    return vocab


def invalidate_inventory_vocabulary(dealership_pk: int) -> None:
    """Clear the per-dealership vocabulary cache — called from a
    ``post_save`` signal so a newly imported Silverado is searchable
    on the next turn instead of five minutes later."""
    cache.delete(f"inventory_vocab:v1:{dealership_pk}")


def _resolve_dealership(dealership=None):
    if dealership is not None:
        return dealership
    from .tenancy import get_default_dealership

    return get_default_dealership()


def parse_filters(query: str, dealership=None) -> SearchFilters:
    dealership = _resolve_dealership(dealership)
    vocab = inventory_vocabulary(dealership)

    q = query.lower()
    raw_keywords = re.findall(r"[a-zA-Z0-9\-]+", q)
    # Keep both forms so structural lookups can hit the plural OR singular.
    keywords = list({k for kw in raw_keywords for k in (kw, _singular(kw))})
    normalised_keywords = {_normalise_model_token(k) for k in keywords}

    filters = SearchFilters(keywords=keywords)

    for token in list(keywords) + list(normalised_keywords):
        signal = GENERIC_TOKEN_SIGNALS.get(token) or vocab.get(token)
        if not signal:
            continue
        if "body_style" in signal:
            filters.body_style = signal["body_style"]
        if "condition" in signal:
            filters.condition = signal["condition"]
        if "model_iexact" in signal:
            filters.model = signal["model_iexact"]
        if "model_icontains" in signal:
            filters.model_contains = signal["model_icontains"]
        if "drivetrain_icontains" in signal:
            filters.drivetrain_contains = signal["drivetrain_icontains"]
        if "make" in signal:
            filters.make = signal["make"]

    for pattern in PRICE_PATTERNS:
        m = pattern.search(query)
        if m:
            try:
                value = float(m.group(1).replace(",", ""))
                if (m.group(2) or "").lower() == "k":
                    value *= 1000
                filters.max_price = value
            except ValueError:
                pass
            break

    for m in YEAR_PATTERN.finditer(query):
        try:
            year = int(m.group(1))
            if 2000 <= year <= 2100:
                filters.min_year = max(filters.min_year or 0, year)
        except ValueError:
            continue

    return filters


def _build_queryset(filters: SearchFilters, dealership=None):
    # Item 13 — exclude debug / test vehicles from customer-facing
    # search. Sourced from chat_engine.customer_visible_vehicles()
    # so the filter pattern stays in one place.
    from .chat_engine import customer_visible_vehicles
    qs = customer_visible_vehicles()
    if dealership is not None:
        qs = qs.filter(dealership=dealership)

    if filters.body_style:
        qs = qs.filter(body_style=filters.body_style)
    if filters.condition:
        qs = qs.filter(condition=filters.condition)
    if filters.model:
        qs = qs.filter(model__iexact=filters.model)
    elif filters.model_contains:
        qs = qs.filter(model__icontains=filters.model_contains)
    if filters.drivetrain_contains:
        qs = qs.filter(drivetrain__icontains=filters.drivetrain_contains)
    if filters.max_price is not None:
        qs = qs.filter(price__lte=Decimal(str(filters.max_price)))
    if filters.min_year is not None:
        qs = qs.filter(year__gte=filters.min_year)
    if filters.make:
        qs = qs.filter(make__iexact=filters.make)

    keyword_q = Q()
    for kw in filters.keywords:
        if len(kw) < 3:
            continue
        keyword_q |= (
            Q(model__icontains=kw)
            | Q(trim__icontains=kw)
            | Q(description__icontains=kw)
            | Q(features__icontains=kw)
            | Q(exterior_color__icontains=kw)
        )
    if keyword_q:
        qs = qs.filter(keyword_q)

    return qs


def search_vehicles(
    query: str,
    *,
    limit: int = 5,
    max_price: Optional[float] = None,
    make: Optional[str] = None,
    dealership=None,
) -> List[Vehicle]:
    """Return up to `limit` vehicles best matching the natural-language query.

    If `max_price` is supplied (e.g. the affordability ceiling derived from the
    customer's monthly budget), it intersects with any "under $X" price ceiling
    parsed from the text — the tighter of the two wins. Vehicles strictly above
    `max_price` are NEVER returned. This is the budget-constrained search path.

    `make` is only applied when the customer has explicitly locked a
    brand ("Ford only" / "I want a Toyota"). Without it, all makes are
    eligible — mixed-lot used inventory routinely spans multiple
    brands. When ``DealerProfile.primary_make`` is set (franchise
    config), that brand's vehicles rank first; independent-dealer
    default has no OEM ranking bias.

    ``dealership`` is resolved via :func:`_resolve_dealership` when the
    caller omits it — the single-tenant default keeps the public
    signature stable while the vocabulary and queryset stay
    tenant-scoped.
    """
    from .dealer_config import get_dealer_profile

    dealership = _resolve_dealership(dealership)
    primary_make_lc = (get_dealer_profile().primary_make or "").strip().lower()

    # Primary-make-first ordering (dealership preference). Postgres and
    # SQLite both accept a Case expression, but a simple Python sort
    # after limit*4 is plenty fast for demo-scale inventory and works
    # on any backend. When primary_make is None (indie mixed-lot), the
    # make-based key is 0 for every row, so ranking falls back to
    # year-desc / price-asc — no OEM bias.
    def _final_order(rows: List[Vehicle]) -> List[Vehicle]:
        def _make_key(v: Vehicle) -> int:
            if not primary_make_lc:
                return 0
            return 0 if (v.make or "").strip().lower() == primary_make_lc else 1

        return sorted(
            rows,
            key=lambda v: (
                _make_key(v),
                -v.year,
                float(v.price),
            ),
        )

    if not query or not query.strip():
        # Item 13 — exclude debug / test vehicles.
        from .chat_engine import customer_visible_vehicles
        qs = customer_visible_vehicles().filter(dealership=dealership)
        if max_price is not None:
            qs = qs.filter(price__lte=Decimal(str(max_price)))
        if make:
            qs = qs.filter(make__iexact=make)
        candidates = list(qs.order_by("-year", "price")[: limit * 4])
        return _final_order(candidates)[:limit]

    filters = parse_filters(query, dealership=dealership)
    if max_price is not None:
        filters.max_price = (
            min(filters.max_price, max_price)
            if filters.max_price is not None
            else max_price
        )
    if make:
        filters.make = make

    qs = _build_queryset(filters, dealership=dealership)
    results = list(qs.order_by("-year", "price")[: limit * 2])

    if not results:
        # Loosen — drop keyword-only constraints, keep structural filters
        # (including max_price and make). When budget-constrained, this
        # still respects the affordability ceiling and any brand lock.
        loose = SearchFilters(
            keywords=[],
            body_style=filters.body_style,
            condition=filters.condition,
            model=filters.model,
            model_contains=filters.model_contains,
            drivetrain_contains=filters.drivetrain_contains,
            max_price=filters.max_price,
            min_year=filters.min_year,
            make=filters.make,
        )
        results = list(
            _build_queryset(loose, dealership=dealership)
            .order_by("-year", "price")[:limit]
        )

    reranked = _rerank(results, filters.keywords)
    return _final_order(reranked)[:limit]


def _rerank(vehicles: Iterable[Vehicle], keywords: Iterable[str]) -> List[Vehicle]:
    keyword_set = {k for k in keywords if len(k) >= 3}
    scored = []
    for v in vehicles:
        score = 0
        haystack = " ".join(
            [
                v.model.lower(),
                v.trim.lower(),
                v.description.lower(),
                " ".join(str(f).lower() for f in (v.features or [])),
                v.exterior_color.lower(),
            ]
        )
        for kw in keyword_set:
            if kw in haystack:
                score += 1
        scored.append((score, v))

    scored.sort(key=lambda s: (-s[0], -s[1].year, s[1].price))
    return [v for _, v in scored]
