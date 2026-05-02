"""SESSION_010 hotfix: shape replies for the manager-chat tester.

The manager-chat endpoint (`POST /api/dealer-ai/manager-chat/`) never
renders vehicle cards — its only payload is `{"reply": text}`. When the
LLM nonetheless produces sentences that imply cards are visible
("Here are a few options", "Let me show you", "Which one of these trucks
catches your eye?"), the manager sees a broken-feeling reply that
references options that never appear.

This module provides a two-layer fix:

1. ``MANAGER_TEST_HINT`` — a system-message string the chat engine appends
   when the session is on the ``manager_test`` channel. The hint tells the
   LLM that no cards render and lists the phrasings to avoid. This is the
   primary fix; it shapes the reply at generation time rather than
   repairing it after the fact.

2. ``scrub_card_implying_phrases`` — a pure-function safety net that
   strips sentences containing card-implying phrasing on the way out of
   the manager-chat view. Runs even if the LLM ignored the hint.

Customer-facing chat is **not** affected: the engine only injects the
hint when ``session.metadata["channel"] == "manager_test"``, and the
scrub is invoked only inside the manager-chat view.
"""

from __future__ import annotations

import re
from typing import Tuple


# System-message text appended to the LLM call when the chat session is
# on the ``manager_test`` channel. The wording is verbose on purpose —
# llama3.2 needs the explicit list to reliably suppress these patterns.
MANAGER_TEST_HINT = (
    "MANAGER TEST MODE — IMPORTANT context for this turn:\n"
    "- This reply is being shown to a dealership MANAGER inside an internal "
    "testing tool. NO vehicle cards, inventory previews, or option lists "
    "are rendered alongside the text.\n"
    "- Do NOT use phrasings that imply visible options. Specifically avoid: "
    "\"Here are a few options\", \"Here are some\", \"Let me show you\", "
    "\"I'll show you\", \"Let's take a look\", \"Take a look at some\", "
    "\"These trucks/cars/SUVs/vehicles/models\", \"Which one catches your "
    "eye?\", \"Which one of these\", \"Pick one of these\", "
    "\"options below\", \"check out these\".\n"
    "- Speak as if no inventory list is visible. If you would recommend "
    "something, describe the qualities to look for or the next narrowing "
    "question. Do not promise to display options that will not appear.\n"
    "- Keep the reply tight (2-4 sentences). End with one focused "
    "next-step question."
)


# Card-implying phrase patterns. Each is a sentence-level substring
# match; if any pattern hits a sentence, the whole sentence is dropped.
# Patterns are case-insensitive; word-boundaries are loose so we catch
# minor LLM variations ("Here's a few options" / "Here are some trucks").
_CARD_IMPLYING_PATTERNS: Tuple[re.Pattern[str], ...] = (
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
    # "I've got X" / "I have X" / "I have a few X" — implies a stocked list.
    re.compile(
        r"i(?:'ve|\s+ha[vs]e)\s+(?:got\s+)?(?:a\s+few|some|several)?\s*"
        r"(?:trucks|cars|suvs|options|models|vehicles)\s+(?:for\s+you|that)",
        re.IGNORECASE,
    ),
    # "looking at some great options" — sounds like cards are visible.
    re.compile(
        r"(?:you(?:'re|\s+are)|you(?:'ll|\s+will))\s+looking\s+at\s+"
        r"(?:some|a\s+few|several|these)\s+"
        r"(?:great\s+|good\s+|solid\s+)?"
        r"(?:options|trucks|cars|suvs|vehicles|models)",
        re.IGNORECASE,
    ),
)


# Sentence splitter — same shape as the existing scrub helpers in
# chat_engine.py / onboarding_overrides.py: splits on .!? followed by
# whitespace and a capital/digit/quote, conservative enough that
# "$30,000.00" and "(W.A.C.)" don't tear.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


# Safe fallback when every sentence in the reply was card-implying.
# Keeps the manager unblocked with a deliberately direction-setting reply
# rather than an empty string. Phrased as a manager-side coaching question
# (matches one of the two acceptable shapes called out in the spec).
_SAFE_FALLBACK = (
    "Under that budget I'd start by narrowing what matters most — "
    "4WD, crew cab, towing, or lowest miles — so the conversation "
    "focuses before quoting specific inventory. What's the priority "
    "for this customer?"
)


def scrub_card_implying_phrases(reply: str) -> Tuple[str, bool]:
    """Strip sentences that imply visible vehicle cards / option lists.

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
