"""SESSION_010/011: shape replies for the manager chat.

The manager-chat endpoint (`POST /api/dealer-ai/manager-chat/`) is the
*coaching mode* surface — a sales-coaching advisor that explains how the
customer-facing assistant should respond to a prompt. It is not a
customer chat with the cards hidden, and it is not a fake assistant
preview. The product decision (2026-05-02 follow-up) is:

    Coaching / preview mode — help a manager understand how the assistant
    would respond, without pretending inventory cards are visible.

This module provides a three-layer fix that pins the mode at the prompt
level, scrubs known bad phrasings, and finally enforces the response
*structure* deterministically:

1. ``MANAGER_COACHING_HINT`` — system-message string the chat engine
   appends when the session is on the ``manager_test`` channel. Lists
   the two acceptable response shapes (Shape A: pure coaching;
   Shape B: coaching + quoted customer-facing preview) and the
   forbidden phrasings explicitly. SESSION_011 tightened this to
   require an explicit coaching opener.

2. ``scrub_card_implying_phrases`` — pure-function pattern scrub that
   strips card-implying *and* first-person inventory claims (e.g.,
   "We have a 2020 Chevrolet Colorado", "Our F-150 starts at...") on
   the way out of the manager-chat view. Subtractive: it can only
   remove sentences, not enforce a positive shape.

3. ``enforce_coaching_shape`` (SESSION_011) — structural validator
   that runs the scrub, then checks whether the surviving text matches
   one of the two acceptable shapes. If a customer-facing pattern is
   present (e.g. "the card", "would that be something you'd consider",
   "I can show you") OR no coaching-frame marker is present at all,
   the reply is replaced with a context-aware deterministic fallback
   built from the customer's message. This is the load-bearing piece
   that catches novel customer-facing phrasings the static scrub
   patterns don't cover (Jessica's SESSION_011 finding).

Customer-facing chat (``/dealer-ai-demo``, ``/api/dealer-ai/chat/...``)
is **not** affected: the engine only injects the hint when
``session.metadata["channel"] == "manager_test"``, and the enforcer is
invoked only inside the manager-chat view.

Trade-off — when the enforcer falls back, the dealership voice tone
saved on /dealer-ai-onboarding does not flow into the fallback text
(the LLM's tone-shaped output was the broken one we discarded). The
fallback is a fixed coaching template with vehicle-type and budget
slots filled from the customer message. Tone is preserved on the
*pass-through* path (Shape A / Shape B replies are unmodified).
The banned-phrase scrub and disclaimer logic both run upstream in
``chat_engine`` before the enforcer sees the reply, so a Shape A / B
reply still carries those guarantees through. A fallback reply is
hand-authored prose with no banned-phrase risk and no customer-
directed payment quote, so disclaimer-elision is a non-issue.
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
    "REQUIRED RESPONSE STRUCTURE — your reply MUST match one of these "
    "two shapes exactly:\n"
    "  (Shape A) Pure coaching. Open with one of these stems and stay "
    "in third-person about the assistant's behavior:\n"
    "    - \"If a customer says/asks/wants...\"\n"
    "    - \"When a customer...\"\n"
    "    - \"I'd open by...\" / \"I'd narrow...\" / \"I'd ask...\" / "
    "\"I'd respond...\" (first-person coaching, NOT first-person "
    "delivery to the customer)\n"
    "    - \"The assistant should...\" / \"A strong response is...\"\n"
    "    Example: \"If a customer asks about trucks under $30k, I'd "
    "narrow the deal first: 4WD, cab size, towing, or mileage. The "
    "assistant should ask one clean qualifying question.\"\n"
    "  (Shape B) Coaching + quoted preview. Same opener as Shape A, "
    "then quote a sample customer-facing reply in double quotes.\n"
    "    Example: \"I'd open by acknowledging the budget and narrowing "
    "priorities. A strong response: 'Absolutely — under $30k, what "
    "matters most: 4WD, crew cab, towing, or lowest miles?'\"\n"
    "\n"
    "Hard rules for coaching mode:\n"
    "- You are NOT the customer-facing assistant in this turn. NEVER "
    "address the manager (or anyone) as the customer with phrases like "
    "\"I can show you\", \"Let me show you\", \"Would that be something "
    "you'd consider\", \"Want a closer look\", \"Does that sound good\". "
    "Those phrasings belong inside QUOTED sample replies (Shape B) only.\n"
    "- No cards or inventory list is visible to the manager. NEVER "
    "reference \"the card\", \"the cards\", \"shown on the card\", "
    "\"shown above/below\", or \"in our inventory\". Cards do not "
    "exist on this surface.\n"
    "- Do NOT make first-person dealership inventory claims like \"We "
    "have a Chevrolet Colorado\", \"Our F-150 starts at\", \"One "
    "option is the Ranger\". Generic price ranges and naming a model "
    "as a coaching example are fine; specific stocked vehicles are "
    "not.\n"
    "- Do NOT use phrasings like: \"Here are some options\", \"Here "
    "are a few options\", \"Let me show you\", \"I'll show you\", "
    "\"I can show you\", \"Let's take a look\", \"Take a look at some\", "
    "\"These trucks/cars/SUVs\", \"Which one catches your eye?\", "
    "\"Pick one of these\", \"options below\", \"check out these\".\n"
    "- DO reflect the dealership voice rules in any DEALER VOICE "
    "OVERRIDES block above (tone, encouraged/banned phrases, "
    "escalation rule).\n"
    "- Keep the reply tight (2-4 sentences). End with a focused "
    "next-step question for the MANAGER (\"What's the priority for "
    "this customer?\") OR a brief note on why the suggested approach "
    "works — NEVER a closing question pointed at the customer."
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


# ---------------------------------------------------------------------------
# SESSION_011 — structural shape enforcement
# ---------------------------------------------------------------------------
#
# The pattern scrubs above are subtractive: they remove sentences that
# match a known-bad pattern. Jessica's SESSION_011 finding showed novel
# customer-facing phrasings that don't match any sentence-level pattern
# but still violate the coaching contract:
#
#   "Most sedans in our inventory fall under the payment shown on the
#    card, but I can show you some options that might fit your budget.
#    Would that be something you'd consider?"
#
# Three independent failures here: "the card" reference, "I can show
# you" delivery, and a customer-directed closing question. Each is a
# separate phrasing the static scrub patterns would have to enumerate.
# Instead, this enforcer detects any of those *families* of customer-
# facing language AND validates the reply has a coaching frame at all.
# When either check fails, the reply is replaced with a deterministic
# fallback built from the customer's message (vehicle type + budget).


# Coaching-frame markers — at least one must appear for the reply to
# be considered structurally on-shape (Shape A or Shape B). These are
# the openers the tightened MANAGER_COACHING_HINT instructs the LLM to
# use. Permissive on purpose: a coaching reply is allowed to embed a
# Shape-B quoted preview that contains customer-facing phrasing, so
# detection cares about whether the *frame* is present, not whether
# every sentence is in third-person.
_COACHING_FRAME_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:if|when)\s+(?:a|the|this|your)\s+customer\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bthe\s+(?:assistant|salesperson|sales\s+rep|sales\s+team|rep)\s+"
        r"(?:should|would|could|might|needs|ought|can|will|must)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bi(?:'d|\s+would)\s+"
        r"(?:open|start|narrow|ask|respond|reply|coach|guide|first|"
        r"acknowledge|suggest|recommend|tell|focus|frame|approach|"
        r"point|encourage|push|emphasize|clarify|qualify|probe)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:a|the)\s+(?:strong|good|clean|focused|solid|better)\s+"
        r"(?:response|reply|answer|opener|approach|move|coaching\s+"
        r"reply|coaching\s+response)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbefore\s+quoting\s+(?:any\s+)?(?:specific\s+)?"
        r"(?:inventory|vehicles?|cars?|trucks?|prices?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bthat\s+gives\s+(?:the\s+)?"
        r"(?:salesperson|assistant|customer|sales\s+rep|rep|team)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bcoaching\s+(?:reply|response|prompt|guidance|frame)\b",
        re.IGNORECASE,
    ),
)


# Customer-facing patterns. Presence of ANY of these means the reply
# is impersonating the customer-facing assistant rather than coaching.
# These run *outside* of any quoted preview — the enforcer strips
# quoted segments before scanning so Shape B replies aren't false-
# positived by their own embedded sample reply.
_CUSTOMER_FACING_PATTERNS: Tuple[re.Pattern[str], ...] = (
    # Card / inventory-display references — there are no cards on this
    # surface. Word-boundary anchored so we don't match "discard".
    re.compile(r"\bthe\s+cards?\b", re.IGNORECASE),
    re.compile(r"\bon\s+(?:the\s+)?cards?\b", re.IGNORECASE),
    re.compile(r"\bshown\s+on\s+(?:the\s+)?cards?\b", re.IGNORECASE),
    re.compile(r"\bshown\s+(?:above|below)\b", re.IGNORECASE),
    re.compile(r"\bin\s+our\s+inventory\b", re.IGNORECASE),
    # First-person delivery ("I can show you"). The static scrub catches
    # "let me show you" / "I'll show you" but NOT "I can show you" — the
    # exact wording in Jessica's failure.
    re.compile(r"\bi\s+can\s+show\s+you\b", re.IGNORECASE),
    re.compile(r"\bi(?:'m|\s+am)\s+going\s+to\s+show\s+you\b", re.IGNORECASE),
    re.compile(r"\bi(?:'m|\s+am)\s+happy\s+to\s+show\s+you\b", re.IGNORECASE),
    re.compile(r"\bi\s+could\s+show\s+you\b", re.IGNORECASE),
    # Customer-directed closing questions. These are the assistant
    # speaking AT a customer rather than coaching ABOUT one.
    re.compile(
        r"\bwould\s+that\s+(?:be\s+)?"
        r"(?:something|of\s+interest|work)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:want|would\s+you\s+like)\s+(?:to\s+)?"
        r"(?:take\s+a\s+(?:closer\s+)?look|see\s+more|hear\s+more)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdoes\s+that\s+(?:sound\s+(?:good|right|like)|work\s+for\s+you|interest\s+you)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bhow\s+does\s+that\s+(?:sound|work|grab\s+you)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:shall|should)\s+(?:we|i)\s+(?:set\s+up|schedule|book|"
        r"arrange|send\s+you)\b",
        re.IGNORECASE,
    ),
    # Customer-facing budget-fit phrasing.
    re.compile(
        r"\b(?:fit|fits|fitting)\s+your\s+budget\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bin\s+your\s+price\s+range\b",
        re.IGNORECASE,
    ),
)


# Strip quoted preview segments before checking customer-facing patterns
# so Shape B replies aren't penalized for the customer-facing phrasing
# inside their sample-reply quote. Handles both straight and curly
# double quotes.
_QUOTED_SEGMENT = re.compile(
    r'(?:"[^"]{3,}"|“[^”]{3,}”)',
)


def _strip_quoted_segments(text: str) -> str:
    return _QUOTED_SEGMENT.sub(" ", text)


# Customer-message → vehicle-type extraction for the context-aware
# fallback. Order matters — "truck" must beat "car" because the keyword
# union is greedy on first match.
_VEHICLE_TYPE_HINTS: Tuple[Tuple[str, str], ...] = (
    ("truck", "truck"),
    ("pickup", "truck"),
    ("f-150", "truck"),
    ("f150", "truck"),
    ("ranger", "truck"),
    ("maverick", "truck"),
    ("suv", "SUV"),
    ("crossover", "SUV"),
    ("explorer", "SUV"),
    ("escape", "SUV"),
    ("bronco", "SUV"),
    ("expedition", "SUV"),
    ("ev", "EV"),
    ("electric", "EV"),
    ("mach-e", "EV"),
    ("mache", "EV"),
    ("hybrid", "hybrid"),
    ("van", "van"),
    ("transit", "van"),
    ("sedan", "sedan"),
    ("coupe", "sedan"),
    ("mustang", "Mustang"),
)


# Budget extraction: looks for "$X/mo" / "X a month" / "X/month" first
# (monthly target), then a bare "$Xk" / "under X thousand" (cash
# ceiling). Returns a (kind, formatted_phrase) tuple or None.
_MONTHLY_PATTERN = re.compile(
    r"\$?\s*(\d{2,4})\s*(?:/\s*(?:mo|month)|\s+(?:a|per)\s+(?:month|mo))",
    re.IGNORECASE,
)
_CASH_PATTERN = re.compile(
    r"(?:under|less\s+than|below|up\s+to|around|about|max(?:imum)?)?\s*"
    r"\$?\s*(\d{1,3})\s*(?:k|,000|\s*thousand)\b",
    re.IGNORECASE,
)


def _detect_vehicle_word(message: str) -> str:
    msg = (message or "").lower()
    for needle, label in _VEHICLE_TYPE_HINTS:
        if needle in msg:
            return label
    return "vehicle"


def _detect_budget_phrase(message: str) -> str:
    """Return a coaching-frame budget phrase like 'around $400/mo' or
    'under $30,000', or empty string if nothing detected."""
    if not message:
        return ""
    monthly = _MONTHLY_PATTERN.search(message)
    if monthly:
        try:
            n = int(monthly.group(1))
        except ValueError:
            return ""
        if 50 <= n <= 5000:
            return f"around ${n:,}/mo"
    cash = _CASH_PATTERN.search(message)
    if cash:
        try:
            n = int(cash.group(1))
        except ValueError:
            return ""
        if 5 <= n <= 200:
            return f"under ${n * 1000:,}"
    return ""


def _coaching_fallback(customer_message: str) -> str:
    """Build a context-aware coaching fallback. Pulls vehicle type and
    budget out of the customer message, slots them into a coaching
    template that opens with "If a customer says..." (Shape A).
    Always third-person about the customer; always ends with a
    focused next-step question pointed at the manager."""
    vehicle_word = _detect_vehicle_word(customer_message)
    budget_phrase = _detect_budget_phrase(customer_message)

    article = "an" if vehicle_word[:1].lower() in "aeiou" else "a"
    budget_clause = f" {budget_phrase}" if budget_phrase else ""

    return (
        f"If a customer says they want {article} {vehicle_word}{budget_clause}, "
        f"I'd narrow the conversation before quoting any specific inventory: "
        f"down payment, trade-in, must-have features, or whether they're "
        f"flexible on year and mileage. The assistant should ask one focused "
        f"qualifying question first. What's the priority for this customer?"
    )


def enforce_coaching_shape(
    reply: str,
    customer_message: str = "",
) -> Tuple[str, str]:
    """Force the manager-chat reply into Shape A (pure coaching) or
    Shape B (coaching + quoted preview).

    Pipeline:
      1. Strip card-implying / first-person inventory sentences via
         ``scrub_card_implying_phrases`` (existing pattern scrub).
      2. Examine the surviving text outside quoted previews. If any
         customer-facing pattern matches OR no coaching-frame marker
         is present, the reply is shapeless — replace it with a
         context-aware coaching fallback.
      3. Otherwise pass the (possibly scrubbed) text through.

    Returns ``(final_text, action)`` where ``action`` is one of:

      - ``"unchanged"``   — reply was already on-shape.
      - ``"scrubbed"``    — bad sentences stripped; surviving prose is
                            on-shape.
      - ``"rewritten"``   — reply was off-shape; replaced with the
                            deterministic coaching fallback.
      - ``"empty_input"`` — reply was empty/whitespace; passed through.

    The action string drives audit metadata and tests; do not change
    these values without updating the regression suite.
    """
    if not reply or not reply.strip():
        return reply, "empty_input"

    scrubbed, scrub_fired = scrub_card_implying_phrases(reply)

    # If the scrub collapsed everything to the safe fallback, that
    # fallback IS a coaching shape. Return it as-rewritten so the
    # action stays meaningful for audits.
    if scrubbed == _SAFE_FALLBACK:
        return scrubbed, "rewritten"

    # Examine the post-scrub text outside any quoted preview block.
    inspectable = _strip_quoted_segments(scrubbed)

    customer_facing_hits = [
        p for p in _CUSTOMER_FACING_PATTERNS if p.search(inspectable)
    ]
    has_coaching_frame = any(
        p.search(inspectable) for p in _COACHING_FRAME_PATTERNS
    )

    # Hard fail: any customer-facing signal in the prose layer means
    # the LLM produced an impersonation, not coaching. Fall back even
    # if a coaching frame is also present somewhere — mixing modes is
    # the failure mode SESSION_011 is closing.
    if customer_facing_hits:
        return _coaching_fallback(customer_message), "rewritten"

    # No customer-facing pattern, but no coaching frame either: shapeless.
    if not has_coaching_frame:
        return _coaching_fallback(customer_message), "rewritten"

    return scrubbed, ("scrubbed" if scrub_fired else "unchanged")
