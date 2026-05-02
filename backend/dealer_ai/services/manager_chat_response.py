"""SESSION_010 (+ coaching follow-up): shape replies for the manager chat.

The manager-chat endpoint (`POST /api/dealer-ai/manager-chat/`) is the
*coaching mode* surface — a sales-coaching advisor that explains how the
customer-facing assistant should respond to a prompt. It is not a
customer chat with the cards hidden, and it is not a fake assistant
preview. The product decision (2026-05-02 follow-up) is:

    Coaching / preview mode — help a manager understand how the assistant
    would respond, without pretending inventory cards are visible.

This module provides a two-layer fix that pins the mode at both the
prompt and the response level:

1. ``MANAGER_COACHING_HINT`` — a system-message string the chat engine
   appends when the session is on the ``manager_test`` channel. The
   hint flips the LLM's role to "internal sales-coaching advisor" and
   lists the forbidden phrasings explicitly. This is the primary fix.

2. ``scrub_card_implying_phrases`` — a pure-function safety net that
   strips card-implying *and* first-person inventory claims (e.g.,
   "We have a 2020 Chevrolet Colorado", "Our F-150 starts at...") on
   the way out of the manager-chat view. Runs even if the LLM ignored
   the hint.

Customer-facing chat (``/dealer-ai-demo``, ``/api/dealer-ai/chat/...``)
is **not** affected: the engine only injects the hint when
``session.metadata["channel"] == "manager_test"``, and the scrub is
invoked only inside the manager-chat view.
"""

from __future__ import annotations

import re
from typing import Tuple


# System-message text appended to the LLM call when the chat session is
# on the ``manager_test`` channel. Verbose on purpose — llama3.2 needs
# both the role re-frame ("you are NOT the customer-facing assistant")
# AND the explicit forbidden-phrasing list to reliably stay in coaching
# mode. The marker phrase "MANAGER COACHING MODE" is asserted by the
# regression tests, so don't change it without updating the tests.
MANAGER_COACHING_HINT = (
    "MANAGER COACHING MODE — your role for this turn:\n"
    "You are the dealership's INTERNAL SALES COACHING ADVISOR. A "
    "dealership manager is testing how their customer-facing assistant "
    "should guide customers; the message above is a sample customer "
    "prompt. Your job is to explain to the manager how the assistant "
    "should respond — not to BE the assistant directly.\n"
    "\n"
    "Two acceptable response shapes:\n"
    "  (a) Pure coaching: explain what the assistant should do.\n"
    "      Example: \"If a customer asks about trucks under $30k, I'd "
    "narrow the deal first: 4WD, cab size, towing, or mileage. The "
    "assistant should ask one clean qualifying question.\"\n"
    "  (b) Quoted preview: describe the approach, then quote a sample "
    "reply.\n"
    "      Example: \"I'd open by acknowledging the budget and "
    "narrowing priorities. A strong response: 'Absolutely — under "
    "$30k, what matters most: 4WD, crew cab, towing, or lowest "
    "miles?'\"\n"
    "\n"
    "Hard rules for coaching mode:\n"
    "- You are NOT the customer-facing assistant in this turn. Speak "
    "in third-person about what the assistant should do, OR provide a "
    "brief sample reply in quotes.\n"
    "- No cards or inventory list is visible to the manager. Do NOT "
    "pretend they are.\n"
    "- Do NOT make first-person dealership inventory claims like \"We "
    "have a Chevrolet Colorado\", \"Our F-150 starts at\", \"One "
    "option is the Ranger\". Generic price ranges and naming a model "
    "as a coaching example are fine; specific stocked vehicles are "
    "not.\n"
    "- Do NOT use phrasings like: \"Here are some options\", \"Here "
    "are a few options\", \"Let me show you\", \"I'll show you\", "
    "\"Let's take a look\", \"Take a look at some\", \"These trucks/"
    "cars/SUVs\", \"Which one catches your eye?\", \"Pick one of "
    "these\", \"options below\", \"check out these\".\n"
    "- DO reflect the dealership voice rules in any DEALER VOICE "
    "OVERRIDES block above (tone, encouraged/banned phrases, "
    "escalation rule).\n"
    "- Keep the reply tight (2-4 sentences). End with a focused "
    "next-step question OR a brief note on why the suggested approach "
    "works."
)


# Backwards-compat alias for any external imports of the old name. Safe
# to remove once nothing references MANAGER_TEST_HINT.
MANAGER_TEST_HINT = MANAGER_COACHING_HINT


# Card-implying phrase patterns. Each pattern matches at the sentence
# level; if a sentence matches, the whole sentence is dropped. Patterns
# are case-insensitive and conservative on word boundaries so we catch
# minor LLM variations.
_CARD_IMPLYING_PATTERNS: Tuple[re.Pattern[str], ...] = (
    # "Here are/'s a few options" / "Here is some trucks" / "Here are some"
    re.compile(
        r"here(?:'s|\s+(?:are|is))?\s+(?:a\s+few|some|several|the)?\s*"
        r"(?:options|trucks|cars|suvs|vehicles|models)",
        re.IGNORECASE,
    ),
    re.compile(r"let\s+me\s+show\s+you", re.IGNORECASE),
    re.compile(r"i(?:'|\s+wi)ll\s+show\s+you", re.IGNORECASE),
    re.compile(
        r"these\s+(?:vehicles|trucks|cars|suvs|models|options)",
        re.IGNORECASE,
    ),
    re.compile(
        r"which\s+(?:one\s+)?(?:of\s+these\s+)?"
        r"(?:catches|grabs|appeals|interests|sounds)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:let(?:'s|\s+us)\s+)?take\s+a\s+look\s+at\s+"
        r"(?:these|some|the|a\s+few)",
        re.IGNORECASE,
    ),
    re.compile(r"pick\s+one\s+of\s+these", re.IGNORECASE),
    re.compile(r"options\s+below", re.IGNORECASE),
    re.compile(
        r"check\s+(?:out\s+)?(?:these|some)\s+"
        r"(?:trucks|cars|suvs|options|models|vehicles)",
        re.IGNORECASE,
    ),
    # First-person LLM claim of stocked inventory.
    re.compile(
        r"i(?:'ve|\s+ha[vs]e)\s+(?:got\s+)?(?:a\s+few|some|several)?\s*"
        r"(?:trucks|cars|suvs|options|models|vehicles)\s+(?:for\s+you|that)",
        re.IGNORECASE,
    ),
    # "you're looking at some great options" — implies cards visible.
    re.compile(
        r"(?:you(?:'re|\s+are)|you(?:'ll|\s+will))\s+looking\s+at\s+"
        r"(?:some|a\s+few|several|these)\s+"
        r"(?:great\s+|good\s+|solid\s+)?"
        r"(?:options|trucks|cars|suvs|vehicles|models)",
        re.IGNORECASE,
    ),
    # ----- Coaching-mode follow-up: first-person inventory claims -----
    # "We have a 2020 ..." / "We've got the F-150" / "We carry several Rangers"
    # Tight: requires a determiner-or-year token after "we have/carry/stock/got".
    re.compile(
        r"\bwe(?:\s+(?:have|has|carry|stock|got)|'(?:ve|d|re))\s+"
        r"(?:got\s+)?"
        r"(?:a|an|the|some|several|a\s+few|a\s+\d{4}|\d{4})\b",
        re.IGNORECASE,
    ),
    # Possessive dealership claim: "Our F-150" / "Our Bronco Sport"
    # Anchored to known make / model names so we don't strip "our customers".
    re.compile(
        r"\bour\s+("
        r"Ford|Chevrolet|Chevy|Toyota|Honda|GMC|Ram|Nissan|Hyundai|Kia|"
        r"Jeep|Dodge|Cadillac|Subaru|Mazda|Volkswagen|BMW|Mercedes|Audi|"
        r"Lexus|Acura|Buick|Lincoln|Tesla|"
        r"F-?\d+|F-?\d+\s+\w+|"
        r"Ranger|Maverick|Bronco|Explorer|Escape|Mustang|Edge|Expedition|"
        r"Fusion|Focus|Fiesta|Taurus|"
        r"Colorado|Tundra|Silverado|Tacoma|Tahoe|Suburban|Equinox|Trailblazer|"
        r"Camry|Civic|Accord|Highlander|Pilot|RAV4|CR-V|Corolla"
        r")\b",
        re.IGNORECASE,
    ),
    # "One option is the X" / "Another model is the Y" / "Next vehicle would be..."
    re.compile(
        r"\b(?:one|another|the\s+next|next)\s+"
        r"(?:option|model|choice|vehicle|truck|car|suv)\s+"
        r"(?:is|would\s+be)\s+(?:the\s+)?[A-Z][\w-]*",
        re.IGNORECASE,
    ),
    # "starts at $X" / "starting around $X" — concrete inventory price claim.
    re.compile(
        r"\bstart(?:s|ing)\s+(?:at|around|from)\s*"
        r"(?:around\s+|about\s+|approximately\s+|roughly\s+)?"
        r"\$\d",
        re.IGNORECASE,
    ),
)


# Sentence splitter — same shape as the existing scrub helpers in
# chat_engine.py / onboarding_overrides.py: splits on .!? followed by
# whitespace and a capital/digit/quote, conservative enough that
# "$30,000.00" and "(W.A.C.)" don't tear.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


# Safe fallback when every sentence in the reply was card-implying or
# inventory-claiming. Phrased as a manager-side coaching prompt.
_SAFE_FALLBACK = (
    "Under that budget I'd start by narrowing what matters most — "
    "4WD, crew cab, towing, or lowest miles — so the conversation "
    "focuses before quoting specific inventory. What's the priority "
    "for this customer?"
)


def scrub_card_implying_phrases(reply: str) -> Tuple[str, bool]:
    """Strip sentences that imply visible vehicle cards or make first-
    person inventory claims.

    Returns ``(cleaned, fired)``. Fired is True when at least one
    sentence matched any of the patterns. If the scrub strips every
    sentence, ``cleaned`` is the safe fallback (so the manager is never
    handed back an empty reply).

    No-op when the reply is empty or no patterns match.
    """
    if not reply:
        return reply, False

    sentences = _SENTENCE_SPLIT.split(reply.strip())
    if not sentences:
        return reply, False

    kept: list = []
    fired = False
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        if any(p.search(stripped) for p in _CARD_IMPLYING_PATTERNS):
            fired = True
            continue
        kept.append(stripped)

    if not fired:
        return reply, False

    if not kept:
        return _SAFE_FALLBACK, True

    return " ".join(kept), True
