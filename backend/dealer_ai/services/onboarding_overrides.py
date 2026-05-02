"""SESSION_009: load the dealer onboarding profile + apply it to chat output.

Pure-ish helpers. ``load_overrides`` is the only function that touches the
DB; everything else takes data as input and returns transformed data. The
chat engine calls ``load_overrides`` once per chat turn (not per token /
not per scrub) so the cost is one indexed lookup against the singleton
``DealerOnboardingProfile`` row.

What this module wires (and explicitly does NOT wire):

- DOES: pre-LLM "store voice" system block (greeting hint, tone, approved
  phrases, escalation rule).
- DOES: post-LLM banned-phrases scrub (sentence-strip, case-insensitive
  substring match).
- DOES: post-LLM payment-disclaimer append (gated by cash_mode and
  payment-language detection, deduplicated).
- DOES NOT: change the demo behavior in absence of a saved profile —
  every helper falls back to "do nothing" when the relevant onboarding
  field is empty.
- DOES NOT: rewrite the chat engine's existing scrub stack. The W.A.C.
  rate scrub still uses its compiled patterns; this module only ADDS
  the dealer-configured disclaimer at the end if appropriate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple


# --- Loader ----------------------------------------------------------------


@dataclass(frozen=True)
class OnboardingOverrides:
    """In-memory snapshot of the persisted onboarding fields used by the
    chat engine. Empty strings / empty lists mean "no override; demo
    behavior wins". Frozen so a single load can be passed to multiple
    helpers without surprise mutation."""

    greeting: str = ""
    sales_tone: str = ""
    approved_phrases: List[str] = field(default_factory=list)
    banned_phrases: List[str] = field(default_factory=list)
    payment_disclaimer: str = ""
    escalation_rule: str = ""

    @property
    def is_empty(self) -> bool:
        """True when no override field has any usable value. The chat
        engine uses this to skip injecting the store-voice block when
        the dealer hasn't configured anything yet."""
        return not (
            self.greeting
            or self.sales_tone
            or self.approved_phrases
            or self.banned_phrases
            or self.payment_disclaimer
            or self.escalation_rule
        )


def load_overrides() -> OnboardingOverrides:
    """Load the singleton ``DealerOnboardingProfile`` if present.

    Returns an empty ``OnboardingOverrides`` if no row exists. The chat
    engine treats that case as "demo defaults", which is identical to
    the pre-SESSION_009 behavior — that's the rule the spec calls
    out: *fallback behavior identical if no profile exists*.
    """
    # Imported inline so this module doesn't pull Django at import time
    # (matches the lazy-import pattern used elsewhere in services/).
    from dealer_ai.models import DealerOnboardingProfile

    profile = DealerOnboardingProfile.objects.first()
    if profile is None:
        return OnboardingOverrides()

    return OnboardingOverrides(
        greeting=(profile.dealership_greeting or "").strip(),
        sales_tone=(profile.sales_tone or "").strip(),
        approved_phrases=parse_phrase_list(profile.approved_phrases or ""),
        banned_phrases=parse_phrase_list(profile.banned_phrases or ""),
        payment_disclaimer=(profile.payment_disclaimer or "").strip(),
        escalation_rule=(profile.escalation_rule or "").strip(),
    )


# --- Phrase list parsing ---------------------------------------------------


def parse_phrase_list(text: str) -> List[str]:
    """Split a multi-line free-text field into a clean list of phrases.

    The onboarding UI captures approved / banned phrases as one-per-line
    text. Strips whitespace, drops empties, drops duplicates while
    preserving order. Comma-separated lines are NOT split — a manager
    might legitimately want a phrase containing a comma — but each line
    is treated as one phrase.
    """
    if not text:
        return []
    seen: set = set()
    out: List[str] = []
    for raw in text.splitlines():
        cleaned = raw.strip()
        if not cleaned:
            continue
        # Strip wrapping quotes if present so "guaranteed approval" and
        # guaranteed approval map to the same phrase.
        if (
            len(cleaned) >= 2
            and cleaned[0] == cleaned[-1]
            and cleaned[0] in ('"', "'")
        ):
            cleaned = cleaned[1:-1].strip()
            if not cleaned:
                continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


# --- Tone directive --------------------------------------------------------


# Mapped at module scope so we can introspect it for tests + audits.
# Keys are case-insensitive substring matches against the persisted
# ``sales_tone`` field. The frontend's ``SALES_TONE_OPTIONS`` list uses
# strings like "Warm + consultative", so we look for the load-bearing
# word ("consultative") rather than requiring an exact match.
_TONE_DIRECTIVES: List[Tuple[str, str]] = [
    (
        "consultative",
        (
            "Voice: warm and consultative. Help the customer think through "
            "the decision; never pressure. Lead with what fits, name one "
            "concrete tradeoff, then ask a single low-pressure follow-up."
        ),
    ),
    (
        "direct",
        (
            "Voice: direct and decisive. Two short paragraphs max. Pick a "
            "concrete recommendation up front, anchor it in numbers, and "
            "close with a clear next-step question."
        ),
    ),
    (
        "fast-paced",
        (
            "Voice: direct and fast-paced. Keep replies tight and "
            "decision-forward. Lead with the recommendation, anchor in "
            "numbers, end with a single concrete next step."
        ),
    ),
    (
        "formal",
        (
            "Voice: formal and professional. Polished phrasing, complete "
            "sentences, no slang. Stay concise (two short paragraphs max) "
            "and end with a clear, respectful next-step question."
        ),
    ),
    (
        "friendly",
        (
            "Voice: warm and conversational. Sound like a helpful neighbor, "
            "not a script. Stay concise (two short paragraphs max) and end "
            "with a relaxed next-step question."
        ),
    ),
    (
        "casual",
        (
            "Voice: relaxed and approachable. Sound like a helpful neighbor. "
            "Stay concise (two short paragraphs max) and end with a casual "
            "next-step question."
        ),
    ),
]


def tone_directive(tone: str) -> str:
    """Return a one-paragraph tone directive for the given persisted
    sales-tone label, or an empty string if no mapping matches.

    Matching is case-insensitive substring match against the keys in
    ``_TONE_DIRECTIVES``, in declared order. Empty input returns "".
    """
    if not tone:
        return ""
    needle = tone.lower()
    for key, directive in _TONE_DIRECTIVES:
        if key in needle:
            return directive
    return ""


# --- Store-voice system block ---------------------------------------------


def format_store_voice_block(overrides: OnboardingOverrides) -> str:
    """Build the system-message block that injects dealer voice rules.

    Returns the empty string when there is nothing to inject — the
    caller should NOT add an empty system message to the LLM payload.

    The block is intentionally short: voice/context hints, not hard
    rules. The hard rules live in ``SYSTEM_PROMPT``. This block layers
    on top so the dealer can shape voice without rewriting the contract.
    """
    if overrides.is_empty:
        return ""

    lines: List[str] = ["DEALER VOICE OVERRIDES (apply on top of the base style rules above):"]

    if overrides.greeting:
        lines.append(
            f'- Store greeting (use as a tone hint, do NOT repeat verbatim every reply): "{overrides.greeting}"'
        )

    directive = tone_directive(overrides.sales_tone)
    if directive:
        lines.append(f"- {directive}")
    elif overrides.sales_tone:
        # Manager wrote a tone label we don't have a built-in directive for —
        # pass it through verbatim so the LLM at least sees it.
        lines.append(
            f'- Voice / tone preference (free-form from manager): "{overrides.sales_tone}"'
        )

    if overrides.approved_phrases:
        # Cap the list so we don't blow out the prompt if a manager
        # pastes 50 phrases. Top-of-list wins.
        capped = overrides.approved_phrases[:10]
        formatted = "; ".join(f'"{p}"' for p in capped)
        lines.append(
            "- Encouraged phrasing (use naturally when the moment fits — do "
            f"NOT phrase-stuff): {formatted}"
        )

    if overrides.banned_phrases:
        capped = overrides.banned_phrases[:10]
        formatted = "; ".join(f'"{p}"' for p in capped)
        lines.append(
            "- Phrasings the dealership has explicitly disallowed — "
            f"do not use any of these: {formatted}"
        )

    if overrides.escalation_rule:
        lines.append(
            "- Soft-handoff rule (use this as guidance for when to suggest a "
            f'human follow-up): "{overrides.escalation_rule}"'
        )

    return "\n".join(lines)


# --- Banned-phrase scrub ---------------------------------------------------


# Sentence splitter mirroring scrub_meta_narration's approach: split on
# . / ! / ? boundaries while keeping the trailing punctuation. Conservative
# enough that "$15,000.00" is not torn apart (the dot is followed by a digit,
# not whitespace).
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def scrub_banned_phrases(
    reply: str, banned: List[str]
) -> Tuple[str, bool, List[str]]:
    """Strip sentences containing any banned phrase.

    Returns ``(cleaned_text, fired_flag, hit_list)`` where ``hit_list`` is
    the deduplicated list of banned phrases that were matched at least
    once (useful for audit metadata).

    Scope:
      - Case-insensitive substring match.
      - Sentence-level removal: if a banned phrase appears anywhere in a
        sentence, the whole sentence is dropped. This is safer than
        word-level surgery, which can leave grammatical wreckage.
      - Whitespace is normalized after removal so we don't leave double
        blank lines.
      - Empty banned list or empty reply → no-op, no flag fired.
    """
    if not reply or not banned:
        return reply, False, []

    needles = [b.lower() for b in banned if b]
    if not needles:
        return reply, False, []

    sentences = _SENTENCE_SPLIT.split(reply.strip())
    if not sentences:
        return reply, False, []

    kept: List[str] = []
    hit_phrases: List[str] = []
    seen_hits: set = set()
    fired = False
    for sentence in sentences:
        lowered = sentence.lower()
        match = next((n for n in needles if n and n in lowered), None)
        if match is None:
            kept.append(sentence)
            continue
        fired = True
        if match not in seen_hits:
            seen_hits.add(match)
            # Surface the original-cased phrase from ``banned`` for audit.
            for original in banned:
                if original.lower() == match:
                    hit_phrases.append(original)
                    break

    if not fired:
        return reply, False, []

    if not kept:
        # Every sentence was banned — fall back to a safe re-engagement
        # rather than returning an empty reply. This case is unlikely in
        # practice (the LLM wouldn't *only* produce banned phrases) but
        # the guard keeps downstream code from receiving "".
        return (
            "Let me make sure I'm helping you the right way — what matters "
            "most for your next vehicle?",
            True,
            hit_phrases,
        )

    cleaned = " ".join(s.strip() for s in kept if s.strip())
    return cleaned, True, hit_phrases


# --- Payment-disclaimer append --------------------------------------------


# Markers that say "this reply mentions payments / financing in a way the
# disclaimer is meaningful for". We're intentionally narrow so we don't
# tag a reply that merely says the word "payment" in passing.
_PAYMENT_MARKERS = (
    re.compile(r"\$\s*\d[\d,]*\s*/\s*mo\b", re.IGNORECASE),
    re.compile(r"\b\d[\d,]*\s+per\s+month\b", re.IGNORECASE),
    re.compile(r"\bmonthly\s+payment", re.IGNORECASE),
    re.compile(r"\bestimated\s+payment", re.IGNORECASE),
    re.compile(r"\bfinanc(?:e|ing)\b", re.IGNORECASE),
)


def reply_mentions_payment(reply: str) -> bool:
    """True when the reply contains payment-or-financing language that
    the disclaimer should accompany."""
    if not reply:
        return False
    for pattern in _PAYMENT_MARKERS:
        if pattern.search(reply):
            return True
    return False


def disclaimer_already_present(reply: str, disclaimer: str) -> bool:
    """True when the configured disclaimer text (or a strong substring of
    it) is already in the reply. We use a short canonical fingerprint
    rather than full-string match because the LLM may have lightly
    paraphrased the disclaimer."""
    if not reply or not disclaimer:
        return False
    haystack = reply.lower()
    # Full-string match first.
    if disclaimer.strip().lower() in haystack:
        return True
    # Fingerprint fallback: the W.A.C. wording is the most distinctive
    # part of the standard disclaimer. If the reply already contains
    # "(W.A.C.)" or "with approved credit", consider the disclaimer
    # covered for de-dup purposes — the rate scrub already inserts that
    # phrasing where appropriate.
    needle = disclaimer.lower()
    if "w.a.c." in needle and "w.a.c." in haystack:
        return True
    if "approved credit" in needle and "approved credit" in haystack:
        return True
    return False


def should_append_disclaimer(
    reply: str, *, cash_mode: bool, disclaimer: str
) -> bool:
    """Decide whether to append the configured payment disclaimer.

    Rules (per SESSION_009 spec):
      1. No disclaimer configured → never append.
      2. Cash-mode reply → never append (disclaimer is finance-language;
         the cash scrub explicitly strips finance prose from cash mode).
      3. Reply doesn't mention payments / financing → never append (the
         disclaimer is irrelevant noise on a non-payment reply).
      4. Disclaimer (or a fingerprint of it) is already present → don't
         duplicate.
      5. Otherwise → append.
    """
    if not disclaimer:
        return False
    if cash_mode:
        return False
    if not reply_mentions_payment(reply):
        return False
    if disclaimer_already_present(reply, disclaimer):
        return False
    return True


def append_disclaimer(reply: str, disclaimer: str) -> str:
    """Append the disclaimer with a clean separator. Caller is responsible
    for the gating decision (use ``should_append_disclaimer``)."""
    base = (reply or "").rstrip()
    if not base:
        return disclaimer.strip()
    sep = "" if base.endswith(("\n", " ")) else " "
    return f"{base}{sep}{disclaimer.strip()}"
