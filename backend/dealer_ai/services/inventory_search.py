"""V1 inventory search — Django ORM keyword matching.

PGVector semantic search will replace the scoring step in V2. The
public surface (`search_vehicles`) stays the same so the chat engine
doesn't need to change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Optional

from django.db.models import Q

from ..models import Vehicle


# Hint vocabulary mapped to model/body-style/feature signals.
KEYWORD_SIGNALS = {
    "truck": {"body_style": "truck"},
    "trucks": {"body_style": "truck"},
    "pickup": {"body_style": "truck"},
    "f-150": {"model_iexact": "F-150"},
    "f150": {"model_iexact": "F-150"},
    "ranger": {"model_iexact": "Ranger"},
    "maverick": {"model_iexact": "Maverick"},
    "suv": {"body_style": "suv"},
    "explorer": {"model_iexact": "Explorer"},
    "escape": {"model_iexact": "Escape"},
    "bronco": {"model_icontains": "Bronco"},
    "ev": {"body_style": "ev"},
    "electric": {"body_style": "ev"},
    "mach-e": {"model_icontains": "Mach-E"},
    "mache": {"model_icontains": "Mach-E"},
    "mustang": {"model_icontains": "Mustang"},
    "used": {"condition": "used"},
    "pre-owned": {"condition": "used"},
    "preowned": {"condition": "used"},
    "new": {"condition": "new"},
    "certified": {"condition": "certified"},
    "4x4": {"drivetrain_icontains": "4"},
    "awd": {"drivetrain_icontains": "AWD"},
    "4wd": {"drivetrain_icontains": "4"},
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
    """Cheap plural strip — 'trucks' → 'truck', 'F-150s' → 'F-150', etc."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def parse_filters(query: str) -> SearchFilters:
    q = query.lower()
    raw_keywords = re.findall(r"[a-zA-Z0-9\-]+", q)
    # Keep both forms so structural lookups can hit the plural OR singular.
    keywords = list({k for kw in raw_keywords for k in (kw, _singular(kw))})

    filters = SearchFilters(keywords=keywords)

    for token in keywords:
        signal = KEYWORD_SIGNALS.get(token)
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


def _build_queryset(filters: SearchFilters):
    # Item 13 — exclude debug / test vehicles from customer-facing
    # search. Sourced from chat_engine.customer_visible_vehicles()
    # so the filter pattern stays in one place.
    from .chat_engine import customer_visible_vehicles
    qs = customer_visible_vehicles()

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
) -> List[Vehicle]:
    """Return up to `limit` vehicles best matching the natural-language query.

    If `max_price` is supplied (e.g. the affordability ceiling derived from the
    customer's monthly budget), it intersects with any "under $X" price ceiling
    parsed from the text — the tighter of the two wins. Vehicles strictly above
    `max_price` are NEVER returned. This is the budget-constrained search path.

    `make` is only applied when the customer has explicitly locked a brand
    ("Ford only" / "I want a Ford"). Without it, all makes are eligible
    — used inventory at a Ford dealership often includes trade-ins from
    other brands. Ford vehicles are still ordered first.
    """
    # Ford-first ordering (dealership preference): Postgres/SQLite both
    # accept a Case expression, but a simple Python sort after limit*4 is
    # plenty fast for demo-scale inventory and works on any backend.
    def _final_order(rows: List[Vehicle]) -> List[Vehicle]:
        return sorted(
            rows,
            key=lambda v: (
                0 if (v.make or "").strip().lower() == "ford" else 1,
                -v.year,
                float(v.price),
            ),
        )

    if not query or not query.strip():
        # Item 13 — exclude debug / test vehicles.
        from .chat_engine import customer_visible_vehicles
        qs = customer_visible_vehicles()
        if max_price is not None:
            qs = qs.filter(price__lte=Decimal(str(max_price)))
        if make:
            qs = qs.filter(make__iexact=make)
        candidates = list(qs.order_by("-year", "price")[: limit * 4])
        return _final_order(candidates)[:limit]

    filters = parse_filters(query)
    if max_price is not None:
        filters.max_price = (
            min(filters.max_price, max_price)
            if filters.max_price is not None
            else max_price
        )
    if make:
        filters.make = make

    qs = _build_queryset(filters)
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
        results = list(_build_queryset(loose).order_by("-year", "price")[:limit])

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
