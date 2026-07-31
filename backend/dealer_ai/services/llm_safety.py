"""Shared post-LLM safety scrub stack.

Manager Phase 4 — closes PROJECT_PIPELINE.md §6.1.

This module is the single source of truth for the order and behaviour of
the post-LLM scrubs that **every** LLM-touching surface must apply
before the model's output reaches a customer or a manager:

- ``chat_engine`` (customer chat reply)
- ``vehicle_assistant`` (per-vehicle Q&A reply)
- ``ad_copy`` (manager ad-copy variants)
- ``follow_up`` (advisor follow-up drafts)

The chat path's existing scrub functions live in ``chat_engine`` for
backwards-compatibility (their behaviour is locked by ~580 tests). This
module **delegates to those functions** rather than re-implementing
them, so no behaviour changes anywhere; we just gain a shared call site.

``apply_post_llm_scrubs(text, *, kind)`` returns ``(cleaned_text,
scrubs_fired, dropped_reason)``:

- ``cleaned_text`` is the text after partial scrubs.
- ``scrubs_fired`` is a list of strings naming the partial scrubs that
  ran (e.g. ``"rate_language"``, ``"internal_directive"``,
  ``"invented_promotion"``, ``"invented_appointment"``).
- ``dropped_reason`` is non-None when a wholesale-rewrite class fired
  (``"dealer_cost_safety"`` or ``"post_llm_override:negotiation"``).
  Callers decide whether to drop the variant entirely (ad-copy /
  follow-up) or substitute the canned guard reply (chat path).

The ``kind`` argument selects which optional scrubs run on top of the
core stack:

- ``"chat"`` — partial scrubs only; the chat path's wholesale-rewrite
  branches are handled by ``chat_engine`` itself (it has special-case
  flag plumbing).
- ``"vehicle_ask"`` — same partial scrub set as chat, applied to the
  per-vehicle endpoint's draft reply (closes §6.1).
- ``"ad"`` — partial scrubs + ``invented_promotion`` (the
  marketing-only "save $X" / "limited time" / "$0 down" /
  "guaranteed approval" patterns).
- ``"follow_up"`` — partial scrubs + ``invented_promotion`` +
  ``invented_appointment`` (the AI must not promise a specific
  appointment time / confirmation).

This module performs **no** state writes. It is import-safe and
side-effect-free. Tests live in ``test_llm_safety.py``.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .chat_engine import (
    detect_unsafe_response,
    scrub_default_assumption_language,
    scrub_internal_directives,
    scrub_post_llm_override,
    scrub_rate_language,
)
from .dealer_config import get_dealer_profile


SafetyKind = str  # "chat" | "vehicle_ask" | "ad" | "follow_up"


# ---- Indie-only scrub: OEM / new-inventory / captive-finance leaks ----------
#
# Independent used lots don't sell "brand new" units, don't offer
# manufacturer CPO programs, don't have OEM-captive lenders (Ford Credit,
# Toyota Financial, etc.), and rarely offer 0% APR promotions. These
# scrubs strip that copy so the assistant can't accidentally imply
# franchise-style benefits to a customer. Only active when the
# configured dealer profile reports ``dealer_type == "independent"`` —
# franchise deployments keep the full range of options.

_INDIE_PROHIBITED_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    # Brand-new claims — indie lots sell used only.
    (re.compile(r"\bbrand[- ]new\b", re.IGNORECASE), "great-condition"),
    # Manufacturer CPO programs are OEM-issued; indies can't offer them.
    (re.compile(r"\bcertified\s+pre[- ]owned\b", re.IGNORECASE), ""),
    (re.compile(r"\bCPO\b"), ""),  # case-sensitive to avoid stock-number
                                    # false positives; LLM writes "CPO"
                                    # or "cpo" only for the acronym.
    (re.compile(r"\bcpo\b"), ""),
    # OEM warranty language — indies offer their own limited warranty,
    # not the manufacturer's remaining coverage.
    (
        re.compile(r"\bmanufacturer'?s?\s+warranty\b", re.IGNORECASE),
        "limited powertrain warranty",
    ),
    (
        re.compile(r"\bfactory\s+warranty\b", re.IGNORECASE),
        "limited powertrain warranty",
    ),
    # OEM captive lenders — indie financing runs through subprime /
    # prime lender panels + in-house BHPH, not manufacturer captives.
    (
        re.compile(r"\bford\s+credit\b", re.IGNORECASE),
        "our lending partners",
    ),
    (
        re.compile(
            r"\btoyota\s+financial(?:\s+services?)?\b", re.IGNORECASE
        ),
        "our lending partners",
    ),
    (
        re.compile(
            r"\bhonda\s+financial(?:\s+services?)?\b", re.IGNORECASE
        ),
        "our lending partners",
    ),
    (
        re.compile(r"\bgm\s+financial\b", re.IGNORECASE),
        "our lending partners",
    ),
    (
        re.compile(
            r"\bnissan\s+motor\s+acceptance(?:\s+corp(?:oration)?)?\b",
            re.IGNORECASE,
        ),
        "our lending partners",
    ),
    (
        re.compile(r"\bchrysler\s+capital\b", re.IGNORECASE),
        "our lending partners",
    ),
    # 0% APR promotions — captive-lender territory, not indie.
    (re.compile(r"\b0\s*%\s*apr\b", re.IGNORECASE), ""),
    (
        re.compile(
            r"\bzero\s+percent\s+(?:apr|financing|interest)\b",
            re.IGNORECASE,
        ),
        "",
    ),
]


def _scrub_indie_prohibited(text: str) -> Tuple[str, bool]:
    """Strip OEM / new-inventory / captive-finance copy from a reply.

    No-op for franchise deployments. Callers should gate on
    ``get_dealer_profile().dealer_type == "independent"`` before
    invoking (kept as a separate concern so the scrub is testable in
    isolation with any input).
    """
    if not text:
        return text, False
    cleaned = text
    changed = False
    for pattern, replacement in _INDIE_PROHIBITED_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub(replacement, cleaned)
            changed = True
    if changed:
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
        cleaned = cleaned.strip()
    return cleaned, changed


# ---- Marketing / ad-only scrub: invented promotions -------------------------
#
# These patterns catch advertising language the dealership has not
# authorized — fabricated discounts, time-pressure copy, and promises the
# AI cannot make on the dealership's behalf.

_INVENTED_PROMOTION_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    # "Save $500 today", "save up to $1,000"
    (
        re.compile(
            r"\bsave\s+(?:up\s+to\s+)?\$\s*\d{1,3}(?:[,.]?\d{3})*\b",
            re.IGNORECASE,
        ),
        "",
    ),
    # "$500 off", "$1,000 off"
    (
        re.compile(
            r"\$\s*\d{1,3}(?:[,.]?\d{3})*\s+off\b", re.IGNORECASE
        ),
        "",
    ),
    # "as low as", "from $X"
    (re.compile(r"\bas\s+low\s+as\b", re.IGNORECASE), ""),
    # "limited time" / "today only" / "this weekend only" / "act fast" / etc.
    (
        re.compile(
            r"\b(?:limited[- ]time|today\s+only|this\s+weekend\s+only|"
            r"act\s+fast|don'?t\s+miss\s+out|hurry)\b",
            re.IGNORECASE,
        ),
        "",
    ),
    # "$0 down" framed as authorized promotion
    (re.compile(r"\$\s*0\s+down\b", re.IGNORECASE), ""),
    # "rebate of $X" / "$X rebate"
    (
        re.compile(
            r"\b(?:rebate\s+of\s+)?\$\s*\d{1,3}(?:[,.]?\d{3})*\s+rebate\b",
            re.IGNORECASE,
        ),
        "",
    ),
    (re.compile(r"\brebate\s+of\s+\$\s*\d", re.IGNORECASE), "rebate of"),
    # "guaranteed approval" / "guaranteed financing"
    (
        re.compile(
            r"\bguaranteed\s+(?:approval|financing|credit)\b", re.IGNORECASE
        ),
        "",
    ),
]


def _scrub_invented_promotion(text: str) -> Tuple[str, bool]:
    if not text:
        return text, False
    cleaned = text
    changed = False
    for pattern, replacement in _INVENTED_PROMOTION_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub(replacement, cleaned)
            changed = True
    if changed:
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
        cleaned = cleaned.strip()
    return cleaned, changed


# ---- Follow-up only: invented appointment commitments ----------------------
#
# Advisors actually book appointments — the AI must not claim a specific
# slot. Strip phrases like "your appointment is confirmed for", "I'll see
# you at 2 PM Saturday", "I have you down for Tuesday at noon", etc.

_INVENTED_APPOINTMENT_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    # "I'll see you Saturday at 2 PM" / "I'll see you on Tuesday" / "I'll see
    # you at 2 PM" — covers the (day [at time])? and (at time)? shapes.
    (
        re.compile(
            r"\bi'?ll\s+see\s+you\s+"
            r"(?:(?:at|on)\s+)?"
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
            r"tomorrow|tonight|today|next\s+\w+|\d{1,2}(?::\d{2})?\s*(?:am|pm))"
            r"[^.!?\n]*",
            re.IGNORECASE,
        ),
        "I'll be in touch to confirm a time",
    ),
    (
        re.compile(
            r"\bi\s+will\s+see\s+you\s+"
            r"(?:(?:at|on)\s+)?"
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
            r"tomorrow|tonight|today|next\s+\w+|\d{1,2}(?::\d{2})?\s*(?:am|pm))"
            r"[^.!?\n]*",
            re.IGNORECASE,
        ),
        "I will be in touch to confirm a time",
    ),
    # "your appointment is (confirmed|set|booked|scheduled) (for|at|on) X"
    (
        re.compile(
            r"\byour\s+appointment\s+is\s+(?:confirmed|set|booked|scheduled)"
            r"(?:\s+(?:for|at|on)\s+\S[^.!?\n]*)?",
            re.IGNORECASE,
        ),
        "I'll confirm a time when you're ready",
    ),
    # "I have you (down|booked|scheduled) for ..."
    (
        re.compile(
            r"\bi\s+have\s+you\s+(?:down|booked|scheduled)\s+for\s+\S[^.!?\n]*",
            re.IGNORECASE,
        ),
        "I'll confirm a time when you're ready",
    ),
    # "see you (at|on) <day/time>"
    (
        re.compile(
            r"\bsee\s+you\s+(?:at|on)\s+(?:Monday|Tuesday|Wednesday|Thursday|"
            r"Friday|Saturday|Sunday|tomorrow|tonight|today|next\s+\w+)"
            r"[^.!?\n]*",
            re.IGNORECASE,
        ),
        "talk soon",
    ),
    # "confirmed for <time>" / "booked for <time>"
    (
        re.compile(
            r"\b(?:confirmed|booked|reserved)\s+for\s+"
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
            r"tomorrow|tonight|today|\d{1,2}(?::\d{2})?\s*(?:am|pm))"
            r"[^.!?\n]*",
            re.IGNORECASE,
        ),
        "",
    ),
    # "available (Monday|Tuesday|...) at <time>"
    (
        re.compile(
            r"\bavailable\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
            r"Saturday|Sunday)\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)"
            r"[^.!?\n]*",
            re.IGNORECASE,
        ),
        "",
    ),
]


def _scrub_invented_appointment(text: str) -> Tuple[str, bool]:
    if not text:
        return text, False
    cleaned = text
    changed = False
    for pattern, replacement in _INVENTED_APPOINTMENT_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub(replacement, cleaned)
            changed = True
    if changed:
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
        cleaned = cleaned.strip()
    return cleaned, changed


# ---- Public entry -----------------------------------------------------------


def apply_post_llm_scrubs(
    text: str, *, kind: SafetyKind = "chat"
) -> Tuple[str, List[str], Optional[str]]:
    """Run the shared post-LLM safety stack on ``text``.

    Returns ``(cleaned_text, scrubs_fired, dropped_reason)``:

    - ``dropped_reason`` is set when a wholesale-rewrite class fires:
      either ``"dealer_cost_safety"`` (sensitive-pricing leakage) or
      ``"post_llm_override:negotiation"`` /
      ``"post_llm_override:handoff"`` (negotiation / fake-transfer
      phrasing). Callers should drop the variant or replace it with
      their canned guard reply when this is non-None.
    - ``scrubs_fired`` lists the partial scrubs that ran. Used for
      audit / metadata flags.

    The ``kind`` argument controls which optional partial scrubs run on
    top of the core (rate / directive / default-assumption) stack:

    - ``"chat"``: partial scrubs only.
    - ``"vehicle_ask"``: same as chat — closes §6.1 by giving the
      per-vehicle endpoint the same safety net.
    - ``"ad"``: + ``invented_promotion``.
    - ``"follow_up"``: + ``invented_promotion`` + ``invented_appointment``.
    """
    if not text:
        return text, [], None

    # 1. Hard-rewrite classes — return early when they fire.
    if detect_unsafe_response(text):
        return text, [], "dealer_cost_safety"
    _, override_kind = scrub_post_llm_override(text)
    if override_kind is not None:
        return text, [], f"post_llm_override:{override_kind}"

    cleaned = text
    scrubs: List[str] = []

    # 2. Core partial scrubs — same order chat_engine uses.
    cleaned, rate_changed = scrub_rate_language(cleaned)
    if rate_changed:
        scrubs.append("rate_language")
    cleaned, dir_changed = scrub_internal_directives(cleaned)
    if dir_changed:
        scrubs.append("internal_directive")
    cleaned, default_changed = scrub_default_assumption_language(cleaned)
    if default_changed:
        scrubs.append("default_assumption")

    # 3. Kind-specific scrubs.
    if kind in ("ad", "follow_up"):
        cleaned, promo_changed = _scrub_invented_promotion(cleaned)
        if promo_changed:
            scrubs.append("invented_promotion")
    if kind == "follow_up":
        cleaned, appt_changed = _scrub_invented_appointment(cleaned)
        if appt_changed:
            scrubs.append("invented_appointment")

    # 4. Independent-dealer-only scrub. Runs on every kind (chat,
    #    vehicle_ask, ad, follow_up) because the prohibited copy is
    #    equally wrong in every surface. Gated on the runtime dealer
    #    profile so franchise deployments are unaffected.
    if get_dealer_profile().dealer_type == "independent":
        cleaned, indie_changed = _scrub_indie_prohibited(cleaned)
        if indie_changed:
            scrubs.append("indie_prohibited_copy")

    return cleaned, scrubs, None
