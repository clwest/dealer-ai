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
- ``"vendor_comm"`` — partial scrubs + ``invented_recon_fact``.
  Fires on AI-drafted vendor communications (M4.5). Callers pass
  ``recon_source_bundle=`` — a structured dict of the
  human-authored facts the draft was rendered from
  (see :func:`_scrub_invented_recon_fact` docstring). Any
  finding ID / part number / dollar amount / date in the draft
  that is NOT present in the source bundle is stripped.
- ``"parts_order"`` — same scrub set as ``"vendor_comm"``.
  Subtype used by the M4.5 parts-order path so aggregation /
  metrics can distinguish parts orders from other vendor comms,
  but the invented-fact regex families are identical.

This module performs **no** state writes. It is import-safe and
side-effect-free. Tests live in ``test_llm_safety.py`` and
(for the M4.5 recon scrub) ``test_llm_safety_recon_scrub.py``.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from .chat_engine import (
    detect_unsafe_response,
    scrub_default_assumption_language,
    scrub_internal_directives,
    scrub_post_llm_override,
    scrub_rate_language,
)
from .dealer_config import get_dealer_profile


SafetyKind = str
# Valid kinds: "chat" | "vehicle_ask" | "ad" | "follow_up" |
# "vendor_comm" | "parts_order". The recon kinds land in M4.5.


# Kinds that trigger the invented-recon-fact scrub. Kept module-level
# so tests can import and lock the exact set.
_RECON_COMM_KINDS: frozenset[str] = frozenset({"vendor_comm", "parts_order"})


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


# ---- Acquisition-price scrub (Milestone 2 · Increment 5) -------------------
#
# Defense-in-depth against internal acquisition / investment figures
# leaking into any customer-facing AI output. Runs on every ``kind``
# because ledger data is equally wrong anywhere it appears; not
# gated on dealer type. Text-only — no DB access, no ledger reads,
# no Vehicle/Dealership lookups. Deterministic.
#
# Design principles (SESSION_051 brief):
#
# - Verbal framing is the primary signal. Patterns anchor on
#   cost-ownership verbs ("we paid", "our cost", "our investment",
#   "acquired", "spent on recon", "purchase price was") rather than
#   proximity to a dollar amount. A generic dollar detector would
#   over-fire on legitimate customer-facing pricing.
# - Favor false negatives over broad false positives. A missed
#   obscure phrase can be added later; a scrub that damages valid
#   pricing language breaks the product today.
# - Substitutions are neutral phrases, never fabricated
#   customer-facing numbers. Prefer "our current pricing" or
#   "a strong value" or removal-of-the-offending-clause over any
#   made-up figure.
# - Ordering: this scrub does NOT reference a numbered "stage."
#   The pipeline count is a documentation concept, not a code
#   contract; introducing "stage 17" here would create ordering
#   dependencies future scrubs could invalidate. This scrub simply
#   joins the always-runs section of ``apply_post_llm_scrubs``.

_ACQUISITION_PRICE_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    # "we paid $X for (this|the|it) ..." OR "we paid $X at auction/wholesale"
    # Deliberately requires the vehicle-context suffix ("for this"/
    # "at auction") to avoid firing on unrelated "we paid $X to the DMV"
    # style disclosures about customer bills. The scrub's job is
    # cost-ownership language, not any-first-person-payment language.
    (
        re.compile(
            r"\bwe\s+paid\s+\$?\s*\d[\d,]*(?:\.\d+)?"
            r"(?:"
            r"\s+for\s+(?:this|the|it)\b[^.!?\n]*"
            r"|\s+at\s+(?:auction|wholesale|the\s+auction)"
            r"|\s+for\s+(?:this|the)\s+\w+\s+at\s+(?:auction|wholesale)"
            r")",
            re.IGNORECASE,
        ),
        "we picked this one up carefully",
    ),
    # "our cost (on this / on the / of / was / is) $X"
    (
        re.compile(
            r"\bour\s+cost"
            r"(?:\s+on\s+(?:this|the)\s+\w+)?"
            r"\s+(?:was|is|of)\s+\$?\s*\d[\d,]*(?:\.\d+)?",
            re.IGNORECASE,
        ),
        "our current pricing reflects the market",
    ),
    # "we're in it for $X" / "we are in it for $X" / "we're in this for $X"
    (
        re.compile(
            r"\bwe(?:'re|\s+are)?\s+in\s+(?:it|this)\s+for\s+\$?\s*\d[\d,]*(?:\.\d+)?",
            re.IGNORECASE,
        ),
        "we've set a competitive price",
    ),
    # "we've got $X in (this|the) <vehicle-word>" /
    # "we have $X in (this|the) <vehicle-word>"
    (
        re.compile(
            r"\bwe(?:'ve|\s+have)\s+(?:got\s+)?\$?\s*\d[\d,]*(?:\.\d+)?"
            r"\s+in\s+(?:this|the)\s+\w+",
            re.IGNORECASE,
        ),
        "we've set a competitive price",
    ),
    # "our purchase price (was|is|of|for) $X" — "our" makes ownership
    # explicit; safe to match any tense.
    (
        re.compile(
            r"\bour\s+purchase\s+price"
            r"(?:\s+(?:was|is|of|for|on)\s+\$?\s*\d[\d,]*(?:\.\d+)?)?",
            re.IGNORECASE,
        ),
        "our current pricing",
    ),
    # "purchase price was $X" / "purchase price of $X"
    # Deliberately NOT matching "purchase price is $X" — that could
    # be customer-facing sticker phrasing.
    (
        re.compile(
            r"\bpurchase\s+price\s+(?:was|of)\s+\$?\s*\d[\d,]*(?:\.\d+)?",
            re.IGNORECASE,
        ),
        "our current pricing is what matters",
    ),
    # "acquired [this|the|it] [<one or two intervening words>] (for|at) $X"
    # Allows a short noun phrase between "acquired" and the price
    # anchor (e.g. "acquired the used vehicle for $X", "acquired this
    # truck at $X"). Non-greedy 0-3 intervening words to catch the
    # common shapes without over-generalizing.
    (
        re.compile(
            r"\bacquired\s+(?:\w+\s+){0,3}?(?:for|at)\s+\$?\s*\d[\d,]*(?:\.\d+)?",
            re.IGNORECASE,
        ),
        "brought this into inventory carefully",
    ),
    # "our investment in (this|the) <word>" — matches with or without
    # a trailing dollar amount so the "our investment on this piece"
    # phrasing (no explicit $ figure) also fires.
    (
        re.compile(
            r"\bour\s+investment\s+in\s+(?:this|the)\s+\w+"
            r"(?:\s+(?:is|of|was)\s+\$?\s*\d[\d,]*(?:\.\d+)?)?",
            re.IGNORECASE,
        ),
        "our commitment to a fair price",
    ),
    # "total investment (is|of|was)? $X" / "total investment $X"
    # Matches "our total investment is $22,000" and "total investment
    # $22,000" without requiring "our" — dealer's total investment
    # in any vehicle is inherently internal.
    (
        re.compile(
            r"\b(?:our\s+)?total\s+investment"
            r"(?:\s+(?:is|of|was))?"
            r"\s+\$?\s*\d[\d,]*(?:\.\d+)?",
            re.IGNORECASE,
        ),
        "a strong value",
    ),
    # "floor plan interest" / "floor-plan interest" — always internal
    # regardless of whether an amount is mentioned. Customers never
    # talk about floor plan; internal-ops term only.
    (
        re.compile(
            r"\bfloor[- ]plan\s+interest"
            r"(?:\s+(?:of|is|was|totals?|amounts?\s+to)\s+\$?\s*\d[\d,]*(?:\.\d+)?)?",
            re.IGNORECASE,
        ),
        "",
    ),
    # "we spent $X on recon" / "spent $X on reconditioning" / "spent
    # $X on repair"
    (
        re.compile(
            r"\b(?:we\s+)?spent\s+\$?\s*\d[\d,]*(?:\.\d+)?"
            r"\s+on\s+(?:recon|reconditioning|repair|repairs)"
            r"[^.!?\n]*",
            re.IGNORECASE,
        ),
        "invested time in preparing the vehicle",
    ),
    # "recon (cost|costs|expense|expenses) (was|were|of|is|are) $X"
    (
        re.compile(
            r"\brecon(?:ditioning)?\s+(?:costs?|expenses?)"
            r"\s+(?:were|was|of|is|are)\s+\$?\s*\d[\d,]*(?:\.\d+)?",
            re.IGNORECASE,
        ),
        "the vehicle was carefully prepared",
    ),
]


def _scrub_acquisition_price(text: str) -> Tuple[str, bool]:
    """Strip internal cost-ownership language from a reply.

    Text-only. No I/O. No ledger reads. Deterministic — same input,
    same output.

    Callers do NOT gate on dealer type (unlike
    :func:`_scrub_indie_prohibited`); ledger data is sensitive
    regardless of independent vs. franchise.
    """
    if not text:
        return text, False
    cleaned = text
    changed = False
    for pattern, replacement in _ACQUISITION_PRICE_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub(replacement, cleaned)
            changed = True
    if changed:
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
        cleaned = cleaned.strip()
    return cleaned, changed


# ---- Recon-communication scrub (Milestone 4 · Increment 5) ------------------
#
# Fires on ``kind in _RECON_COMM_KINDS`` (i.e. ``"vendor_comm"`` or
# ``"parts_order"``). Unlike the other post-LLM scrubs which are pure
# text-only pattern matchers, this scrub takes a structured
# ``source_bundle`` — the human-authored facts the vendor-comm draft
# was rendered from — and strips any claim in the LLM's output that
# does not trace back to that source.
#
# The source bundle is defined at ``MILESTONE_4_PLANNING.md`` §5.g:
#
#   {
#     "vehicle": {stock, year, make, model, vin_last_6},
#     "vendor": {name},
#     "findings": [{id, category, severity, description}, ...],
#     "authorized_cost": str_two_decimals or None,
#     "estimated_completion_date": iso or None,
#     "parts_needed": [{name, part_number, quantity, unit_cost, source_type}, ...],
#     "operator_notes": str,
#   }
#
# Four regex families run per §5.g:
#
# 1. Invented finding IDs — ``Finding #<n>`` where ``n`` is not in
#    ``source["findings"][*]["id"]``.
# 2. Invented part numbers — ``[A-Z0-9-]{5,}`` tokens not in
#    ``source["parts_needed"][*]["part_number"]``.
# 3. Invented dollar amounts — ``$<n>`` not equal to
#    ``source["authorized_cost"]`` and not equal to
#    ``sum(source["parts_needed"][*].unit_cost * quantity)`` for any
#    subset.
# 4. Invented dates — ISO ``YYYY-MM-DD`` tokens not equal to
#    ``source["estimated_completion_date"]``.
#
# Rewrite strategy: strip the invented reference and substitute a
# generic phrase. The scrub does NOT delete the whole draft (that's
# the caller's job to review). It returns ``(cleaned_text,
# changed_bool)`` matching every other scrub in this module.

# Part-number token pattern per §5.g: [A-Z0-9-]{5,}. Anchored on word
# boundaries so we don't match segments of longer alphanumeric runs.
_RECON_PART_NUMBER_PATTERN = re.compile(r"\b[A-Z][A-Z0-9-]{4,}\b")

# Finding reference pattern per §5.g.
_RECON_FINDING_REF_PATTERN = re.compile(
    r"\bFinding\s*#\s*(\d+)\b", re.IGNORECASE
)

# Dollar-amount pattern — matches "$123", "$1,234", "$1234.56".
_RECON_DOLLAR_PATTERN = re.compile(r"\$([\d,]+(?:\.\d{1,2})?)")

# ISO date pattern — matches "YYYY-MM-DD" (the format the source
# bundle uses per §5.g). Free-text dates like "October 15" are not
# scrubbed — too much false-positive risk for a text-only pass.
# Operator review + M4.7 UI provenance rendering are the compensating
# controls per §5.g.
_RECON_ISO_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _valid_finding_ids(source_bundle: dict) -> set:
    """Extract the set of legitimate finding IDs (as strings) from the
    source bundle."""
    ids = set()
    for finding in source_bundle.get("findings") or ():
        fid = finding.get("id") if isinstance(finding, dict) else None
        if fid is not None:
            ids.add(str(fid))
    return ids


def _valid_part_numbers(source_bundle: dict) -> set:
    """Extract the set of legitimate part-number strings from the
    source bundle."""
    numbers = set()
    for part in source_bundle.get("parts_needed") or ():
        pn = part.get("part_number") if isinstance(part, dict) else None
        if pn:
            numbers.add(str(pn).strip())
    return numbers


def _valid_dollar_strings(source_bundle: dict) -> set:
    """Return the set of legitimate dollar-amount strings the LLM may
    reference. Includes ``authorized_cost`` and every
    ``unit_cost * quantity`` product for parts. Every amount is
    represented in three normalized forms — bare integer
    (``"500"``), two-decimal (``"500.00"``), and comma-grouped
    (``"1,234.00"``) — so a match against any of the three forms
    counts as legitimate."""
    def _forms(amount) -> set:
        try:
            dec = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            return set()
        result = {
            f"{dec:.2f}",  # two-decimal
            f"{int(dec)}" if dec == dec.to_integral_value() else f"{dec}",
        }
        # Comma-grouped two-decimal (e.g. "1,234.00").
        if dec >= 1000:
            result.add(f"{dec:,.2f}")
            if dec == dec.to_integral_value():
                result.add(f"{int(dec):,}")
        return result

    valid: set[str] = set()
    authorized_cost = source_bundle.get("authorized_cost")
    if authorized_cost is not None:
        valid.update(_forms(authorized_cost))
    for part in source_bundle.get("parts_needed") or ():
        if not isinstance(part, dict):
            continue
        unit = part.get("unit_cost")
        qty = part.get("quantity", 1) or 1
        if unit is None:
            continue
        try:
            total = Decimal(str(unit)) * Decimal(str(qty))
        except (InvalidOperation, TypeError, ValueError):
            continue
        valid.update(_forms(total))
    return valid


def _valid_iso_dates(source_bundle: dict) -> set:
    """Return the set of legitimate ISO date strings the LLM may
    reference — currently just ``estimated_completion_date`` from
    the source bundle."""
    valid = set()
    ecd = source_bundle.get("estimated_completion_date")
    if ecd:
        valid.add(str(ecd).strip())
    return valid


def _scrub_invented_recon_fact(
    text: str, *, source_bundle: dict
) -> Tuple[str, bool]:
    """Strip invented finding IDs, part numbers, dollar amounts, and
    ISO dates from a vendor-comm draft.

    Text-only. No DB access. Deterministic — same input, same
    output. Callers thread the ``source_bundle`` dict at
    :func:`apply_post_llm_scrubs` call-time.

    Rewrite strategy per §5.g:

    - Invented ``Finding #<n>`` → ``"the finding"``. Preserves the
      surrounding sentence so the human-authored description can
      still land in the reader's context.
    - Invented part number → ``"the part"``. Stripping the specific
      identifier while preserving the sentence is safer than
      dropping the whole clause (which might strand a "please
      order" clause without an object).
    - Invented ``$<amount>`` → ``"the quoted amount"``. Operator
      reviews before send per §5.g human-approval invariant.
    - Invented ``YYYY-MM-DD`` → ``"the scheduled date"``.

    A NIL ``source_bundle`` (empty dict) treats every referenced
    fact as invented — the LLM should not fabricate facts when the
    caller provided no source. Returns ``(text, False)`` for empty
    input.

    Returns ``(cleaned_text, changed_bool)`` matching the shape of
    every other scrub in this module.
    """
    if not text:
        return text, False

    source_bundle = source_bundle or {}
    valid_findings = _valid_finding_ids(source_bundle)
    valid_parts = _valid_part_numbers(source_bundle)
    valid_amounts = _valid_dollar_strings(source_bundle)
    valid_dates = _valid_iso_dates(source_bundle)

    cleaned = text
    changed = False

    # 1. Invented finding IDs.
    def _finding_sub(match: re.Match) -> str:
        nonlocal changed
        fid = match.group(1)
        if fid in valid_findings:
            return match.group(0)
        changed = True
        return "the finding"

    cleaned = _RECON_FINDING_REF_PATTERN.sub(_finding_sub, cleaned)

    # 2. Invented part numbers.
    def _part_sub(match: re.Match) -> str:
        nonlocal changed
        pn = match.group(0)
        if pn in valid_parts:
            return pn
        changed = True
        return "the part"

    cleaned = _RECON_PART_NUMBER_PATTERN.sub(_part_sub, cleaned)

    # 3. Invented dollar amounts.
    def _dollar_sub(match: re.Match) -> str:
        nonlocal changed
        # Normalize the captured number for comparison — the source
        # bundle's forms include stripped, comma-grouped, and
        # decimal variants.
        raw = match.group(1)
        stripped = raw.replace(",", "")
        try:
            dec = Decimal(stripped)
        except InvalidOperation:
            return match.group(0)
        candidates = {
            f"{dec:.2f}",
            f"{int(dec)}" if dec == dec.to_integral_value() else f"{dec}",
            raw,
        }
        if dec >= 1000:
            candidates.add(f"{dec:,.2f}")
            if dec == dec.to_integral_value():
                candidates.add(f"{int(dec):,}")
        if candidates & valid_amounts:
            return match.group(0)
        changed = True
        return "the quoted amount"

    cleaned = _RECON_DOLLAR_PATTERN.sub(_dollar_sub, cleaned)

    # 4. Invented ISO dates.
    def _date_sub(match: re.Match) -> str:
        nonlocal changed
        d = match.group(1)
        if d in valid_dates:
            return d
        changed = True
        return "the scheduled date"

    cleaned = _RECON_ISO_DATE_PATTERN.sub(_date_sub, cleaned)

    if changed:
        # Same whitespace normalization the other scrubs use.
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
        cleaned = cleaned.strip()

    return cleaned, changed


# ---- Public entry -----------------------------------------------------------


def apply_post_llm_scrubs(
    text: str,
    *,
    kind: SafetyKind = "chat",
    recon_source_bundle: Optional[dict] = None,
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
    - ``"vendor_comm"`` / ``"parts_order"``: +
      ``invented_recon_fact`` (M4.5). Callers thread
      ``recon_source_bundle=`` — a dict of the human-authored
      facts the draft was rendered from. Any finding ID / part
      number / dollar amount / ISO date in the LLM output that
      is not present in the source bundle is stripped. See
      :func:`_scrub_invented_recon_fact` for the full contract.

    ``recon_source_bundle`` is only consulted when ``kind`` is one of
    the recon-comm kinds. Text-only callers (chat / vehicle_ask /
    ad / follow_up) may leave it as ``None``.
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

    # 2b. Acquisition-price scrub (Milestone 2 · Increment 5).
    #     Runs on every ``kind`` because ledger-leakage phrasing is
    #     equally wrong anywhere. No dealer-type gating (unlike the
    #     indie-prohibited scrub below) — investment figures are
    #     sensitive regardless of independent vs. franchise. Text-
    #     only; no DB access.
    cleaned, acquisition_price_changed = _scrub_acquisition_price(cleaned)
    if acquisition_price_changed:
        scrubs.append("acquisition_price")

    # 2c. Recon-fact scrub (Milestone 4 · Increment 5).
    #     Fires on ``vendor_comm`` / ``parts_order`` kinds. Requires
    #     the caller to pass ``recon_source_bundle`` — the structured
    #     dict of human-authored facts the draft was rendered from.
    #     A missing bundle treats every referenced fact as invented
    #     (the LLM should not fabricate when the caller has no
    #     source). Text-only; no DB access.
    if kind in _RECON_COMM_KINDS:
        cleaned, recon_changed = _scrub_invented_recon_fact(
            cleaned, source_bundle=recon_source_bundle or {}
        )
        if recon_changed:
            scrubs.append("invented_recon_fact")

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
