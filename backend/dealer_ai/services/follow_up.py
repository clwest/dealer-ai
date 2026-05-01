"""Manager Phase 4: AI follow-up draft generator for advisor workspace.

Sibling to ``services/ad_copy.py``. Generates SMS or email drafts a
salesperson can copy/edit before sending. **Read-only** with respect to
system state — no persistence, no auto-send, no channel integration.

Inputs are real lead data + the assigned advisor's profile + a channel
hint. Outputs are 1–2 drafts per request, each passed through the
shared ``llm_safety.apply_post_llm_scrubs(kind="follow_up")`` stack so:

- Rate / APR / dealer-cost language is scrubbed (chat-path parity).
- Negotiation / fake-handoff phrasing drops the variant.
- Marketing-style invented promotions ("save $X", "limited time",
  "$0 down", "guaranteed approval") are scrubbed (ad-copy parity).
- **New for follow-up:** invented appointment commitments ("I'll see
  you at 2 PM Saturday", "your appointment is confirmed for Tuesday at
  noon") are scrubbed — advisors actually book.

The advisor name is woven into the prompt as the signature, never the
customer's full PII (the prompt instructs first-name only).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..models import CustomerLead, Salesperson
from .llm.base import LLMProvider
from .llm.factory import get_llm_provider
from .llm_safety import apply_post_llm_scrubs

logger = logging.getLogger(__name__)


SUPPORTED_CHANNELS: tuple[str, ...] = ("sms", "email")
SUPPORTED_TONES: tuple[str, ...] = ("warm", "direct")
DEFAULT_DRAFT_COUNT = 2


@dataclass
class FollowUpResult:
    lead_id: int
    salesperson_slug: str
    drafts: List[dict]
    warnings: List[str]


# ---- Prompt construction ----------------------------------------------------


_SYSTEM_PROMPT = """You are a personal-message drafter for a Freedom Ford
salesperson. The salesperson will edit your draft before sending it; your job
is to produce one short, honest first draft per request.

Hard rules — these are non-negotiable:
- Use ONLY facts from the LEAD CONTEXT, INTERESTED VEHICLES, and ADVISOR
  blocks below. Never invent specs, prices, mileage, features, financing
  offers, or warranty terms.
- Use the customer's FIRST NAME only. Do not write "Hello [PII]" templates
  or use the customer's full name in any line.
- NEVER state or imply a specific interest rate, APR, financing
  percentage, or "as low as X%". If you reference payments at all,
  qualify with "with approved credit" / "W.A.C." and quote the
  estimate verbatim from PAYMENT MATH.
- NEVER mention dealer cost, invoice price, internal margin, holdback,
  acquisition cost, or any non-public pricing.
- NEVER invent discounts, rebates, "save $X", "limited time", trade
  allowances, or competitor price-match promises.
- NEVER promise a specific appointment time, day, or commitment. Say
  "what time works for you?" or "I'll line up a time that works" —
  the advisor confirms appointments, not the AI.
- NEVER promise a specific approval, financing decision, or numeric
  trade-in valuation. Defer those to the dealership.
- Sign with the advisor's first name + Freedom Ford on email; on SMS,
  the advisor's first name is enough.

Tone: {{TONE_NOTE}}

Channel constraints:
- SMS: ≤ 320 characters total (about 2 SMS segments). One short
  paragraph. No subject line.
- Email: subject ≤ 80 characters, body ≤ 600 characters. Light
  greeting, one short paragraph, signature with advisor name + dealership.

OUTPUT FORMAT — read carefully, this is enforced by an automatic parser:
- Return ONLY a JSON array. Begin your output with `[` and end with `]`.
- No prose, no greetings to me, no "Here are the drafts:", no "Sure!",
  no "Hope this helps", no commentary, no markdown code fences.
- Use null (not the string "null") when subject doesn't apply.

Schema:
[
  {
    "channel": "sms" | "email",
    "subject": "<= 80 chars" | null,
    "body": "<= 600 chars (or 320 for SMS)"
  },
  ...
]

Produce {{DRAFT_COUNT}} draft(s). Output JSON only.
"""


_TONE_NOTES: Dict[str, str] = {
    "warm": (
        "warm, friendly, low-pressure. Sound like someone who remembers "
        "the conversation."
    ),
    "direct": (
        "respectful and direct. Short. Get to the point. No filler."
    ),
}


def _format_lead_block(lead: CustomerLead) -> str:
    first_name = (lead.name or "there").split()[0] if lead.name else "there"
    lines = [
        "LEAD CONTEXT (do NOT echo these labels):",
        f"- First name: {first_name}",
        f"- Urgency: {lead.urgency or 'not stated'}",
    ]
    if lead.target_monthly_payment is not None:
        lines.append(
            f"- Target monthly payment: ${float(lead.target_monthly_payment):,.0f}/mo"
        )
    if lead.down_payment is not None:
        lines.append(f"- Down payment available: ${float(lead.down_payment):,.0f}")
    if lead.trade_in:
        lines.append(f"- Trade-in: {lead.trade_in}")
    if lead.credit_range:
        lines.append(f"- Stated credit range: {lead.credit_range}")
    if lead.conversation_summary:
        lines.append(f"- Prior conversation summary: {lead.conversation_summary}")
    if lead.recommended_next_action:
        lines.append(f"- Suggested next step: {lead.recommended_next_action}")
    return "\n".join(lines)


def _format_vehicles_block(lead: CustomerLead) -> str:
    interested = list(lead.interested_vehicles.all()[:3])
    if not interested:
        return (
            "INTERESTED VEHICLES: none flagged on this lead. Keep the message "
            "general — do NOT invent specific units."
        )
    lines = ["INTERESTED VEHICLES (real, available — use these facts only):"]
    for v in interested:
        bits = [
            f"{v.display_name}",
            f"Stock #{v.stock_number}",
            f"${float(v.price):,.0f}",
        ]
        if v.condition:
            bits.append(v.condition)
        if v.mileage is not None:
            bits.append(f"{v.mileage:,} mi")
        if v.drivetrain:
            bits.append(v.drivetrain)
        lines.append("- " + " | ".join(bits))
    return "\n".join(lines)


def _format_advisor_block(advisor: Salesperson) -> str:
    first_name = advisor.name.split()[0] if advisor.name else "your advisor"
    lines = [
        "ADVISOR (sign drafts as this person):",
        f"- Name: {advisor.name}",
        f"- First name only for signature: {first_name}",
    ]
    if advisor.title:
        lines.append(f"- Title: {advisor.title}")
    if advisor.specialties:
        lines.append(f"- Specialties: {', '.join(advisor.specialties)}")
    return "\n".join(lines)


def build_messages(
    lead: CustomerLead,
    advisor: Salesperson,
    *,
    channel: str,
    tone: str,
    draft_count: int,
) -> List[Dict[str, str]]:
    system = (
        _SYSTEM_PROMPT.replace("{{TONE_NOTE}}", _TONE_NOTES[tone]).replace(
            "{{DRAFT_COUNT}}", str(draft_count)
        )
    )
    user = (
        f"Channel: {channel}. Generate {draft_count} draft(s) now. "
        "JSON array only."
    )
    return [
        {"role": "system", "content": system},
        {"role": "system", "content": _format_lead_block(lead)},
        {"role": "system", "content": _format_vehicles_block(lead)},
        {"role": "system", "content": _format_advisor_block(advisor)},
        {"role": "user", "content": user},
    ]


# ---- LLM output parsing -----------------------------------------------------


_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text


def _strip_preamble(text: str) -> str:
    """Cut everything before the first top-level ``[`` or ``{`` if the
    preamble is short and free of JSON-like punctuation. Catches common
    LLM lead-ins like 'Here are the drafts:' or 'Sure!'."""
    for ch in ("[", "{"):
        idx = text.find(ch)
        if idx > 0:
            preamble = text[:idx]
            if (
                len(preamble) <= 200
                and "[" not in preamble
                and "{" not in preamble
            ):
                return text[idx:]
    return text


def _try_json(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _coerce_to_dict_list(parsed) -> List[dict]:
    if isinstance(parsed, list):
        return [d for d in parsed if isinstance(d, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _extract_balanced_objects(text: str) -> List[dict]:
    """Walk ``text`` and return every balanced top-level JSON object that
    parses cleanly. Tolerates prose between objects so we still recover
    when the LLM writes ``Here is one: {...}, and another: {...}``."""
    out: List[dict] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_string = False
        escape = False
        end = -1
        for j in range(i, n):
            ch = text[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end < 0:
            # Unterminated object — abort the walk; later text won't help.
            break
        candidate = text[i : end + 1]
        parsed = _try_json(candidate)
        if isinstance(parsed, dict):
            out.append(parsed)
        i = end + 1
    return out


def _parse_drafts(raw: str) -> List[dict]:
    """Layered parser. Tries (1) the whole reply as JSON, (2) the
    longest bracketed substring, (3) preamble-stripped retry, (4) any
    balanced JSON object in the prose. Returns ``[]`` only when none
    of the layers recover usable draft objects — the caller substitutes
    a deterministic fallback in that case."""
    if not raw:
        return []
    text = _strip_fences(raw.strip())

    # Layer 1: parse the whole text as JSON.
    parsed = _try_json(text)
    if parsed is not None:
        coerced = _coerce_to_dict_list(parsed)
        if coerced:
            return coerced

    # Layer 2: greedy first-to-last bracket pair.
    m = _JSON_ARRAY_RE.search(text)
    if m:
        parsed = _try_json(m.group(0))
        if parsed is not None:
            coerced = _coerce_to_dict_list(parsed)
            if coerced:
                return coerced

    # Layer 3: strip preamble ("Sure!", "Here are the drafts:", etc.) and retry
    # both whole-text and greedy-bracket parses.
    stripped = _strip_preamble(text).strip()
    if stripped != text:
        parsed = _try_json(stripped)
        if parsed is not None:
            coerced = _coerce_to_dict_list(parsed)
            if coerced:
                return coerced
        m = _JSON_ARRAY_RE.search(stripped)
        if m:
            parsed = _try_json(m.group(0))
            if parsed is not None:
                coerced = _coerce_to_dict_list(parsed)
                if coerced:
                    return coerced

    # Layer 4: walk the text and salvage any balanced ``{...}`` objects.
    objects = _extract_balanced_objects(text)
    if objects:
        return objects

    return []


def _normalize_draft(
    draft: dict, *, default_channel: str
) -> Optional[dict]:
    body = str(draft.get("body") or "").strip()
    if not body:
        return None
    channel = str(draft.get("channel") or default_channel).strip().lower()
    if channel not in SUPPORTED_CHANNELS:
        channel = default_channel
    subject_raw = draft.get("subject")
    if subject_raw is None or channel == "sms":
        subject: Optional[str] = None
    else:
        subject = str(subject_raw).strip()[:120] or None

    # Channel length caps mirror the prompt (defensive, in case the
    # model exceeds them).
    if channel == "sms":
        body = body[:320]
    else:
        body = body[:1200]

    return {
        "channel": channel,
        "subject": subject,
        "body": body,
        "source": "llm",
    }


def _scrub_draft(draft: dict) -> tuple[Optional[dict], List[str]]:
    """Run the shared post-LLM safety stack on a draft. Returns
    (cleaned_or_none, scrubs_fired). Drops the draft when a wholesale
    rewrite class fires (dealer-cost / negotiation phrasing). Preserves
    the ``source`` key (``"llm"`` or ``"fallback"``) so the UI can label
    deterministic fallbacks distinctly."""
    scrubs: List[str] = []
    cleaned = dict(draft)

    for field in ("subject", "body"):
        text = cleaned.get(field) or ""
        if not text:
            continue
        cleaned_text, scrubs_for_field, dropped_reason = apply_post_llm_scrubs(
            text, kind="follow_up"
        )
        if dropped_reason is not None:
            return None, scrubs + [f"{dropped_reason}:{field}"]
        cleaned[field] = cleaned_text.strip() or None if field == "subject" else cleaned_text.strip()
        for s in scrubs_for_field:
            scrubs.append(f"{s}:{field}")

    if not cleaned.get("body"):
        return None, scrubs + ["empty_after_scrub"]
    return cleaned, scrubs


def _build_fallback_draft(
    *, lead: CustomerLead, advisor: Salesperson, channel: str
) -> dict:
    """Compose a deterministic, safe follow-up draft from real lead and
    advisor data. Used when the LLM call fails, returns prose without
    JSON, or every variant is dropped by the safety stack. Always
    produces exactly one draft.

    Tagged with ``source="fallback"`` so the UI can label it distinctly.
    By construction it never contains rate / dealer-cost / appointment-
    promise / discount language — but it still flows through the same
    scrub stack as LLM drafts for defense in depth.
    """
    first_name = (
        (lead.name or "there").split()[0] if lead.name else "there"
    )
    advisor_first = (
        advisor.name.split()[0] if advisor.name else "your advisor"
    )

    vehicle_phrase = ""
    try:
        first_vehicle = list(lead.interested_vehicles.all()[:1])
    except Exception:  # noqa: BLE001 — never fail the fallback
        first_vehicle = []
    if first_vehicle:
        v = first_vehicle[0]
        vehicle_phrase = f" the {v.display_name} (Stock #{v.stock_number})"

    if channel == "sms":
        if vehicle_phrase:
            middle = (
                f"Following up on{vehicle_phrase} when you have a moment."
            )
        else:
            middle = (
                "Wanted to check in when you have a moment to chat about "
                "your options."
            )
        body = (
            f"Hi {first_name} — {advisor_first} from Freedom Ford. "
            f"{middle} What time works to chat? — {advisor_first}"
        ).strip()
        return {
            "channel": "sms",
            "subject": None,
            "body": body[:320],
            "source": "fallback",
        }

    subject = "Following up from Freedom Ford"
    if vehicle_phrase:
        middle = f"I wanted to follow up on{vehicle_phrase}."
    else:
        middle = (
            "I wanted to check in and see if you'd like to talk through "
            "your options."
        )
    body = (
        f"Hi {first_name},\n\n"
        f"This is {advisor_first} from Freedom Ford. "
        f"{middle} "
        "Whenever works for you, I'll line up a time to talk.\n\n"
        f"Thanks,\n{advisor_first}\nFreedom Ford"
    )
    return {
        "channel": "email",
        "subject": subject[:120],
        "body": body[:1200],
        "source": "fallback",
    }


# ---- Public entry -----------------------------------------------------------


def generate_follow_up_drafts(
    *,
    lead: CustomerLead,
    advisor: Salesperson,
    channel: str = "sms",
    tone: str = "warm",
    provider: Optional[LLMProvider] = None,
    draft_count: int = DEFAULT_DRAFT_COUNT,
) -> FollowUpResult:
    """Generate follow-up drafts for an assigned lead.

    Raises ``ValueError`` for unsupported channel or tone — the view
    translates to 400. All other failure modes (LLM offline, unparseable
    JSON, all variants scrubbed) come back as warnings on the result, so
    the UI never sees a 500.
    """
    if channel not in SUPPORTED_CHANNELS:
        raise ValueError(
            f"channel must be one of {SUPPORTED_CHANNELS}; got {channel!r}"
        )
    if tone not in SUPPORTED_TONES:
        raise ValueError(
            f"tone must be one of {SUPPORTED_TONES}; got {tone!r}"
        )

    warnings: List[str] = []
    provider = provider or get_llm_provider()
    messages = build_messages(
        lead, advisor, channel=channel, tone=tone, draft_count=draft_count
    )

    raw: Optional[str] = ""
    try:
        raw = provider.chat(messages, temperature=0.5, max_tokens=600)
    except Exception as exc:  # noqa: BLE001 — never fail the request
        logger.warning("follow_up LLM call failed: %s", exc)
        warnings.append(f"LLM call failed: {exc}")
        raw = ""

    parsed = _parse_drafts(raw or "")
    if (raw or "").strip() and not parsed:
        warnings.append(
            "LLM did not return a parseable JSON array of drafts. "
            "Showing a deterministic fallback below."
        )

    cleaned: List[dict] = []
    for idx, raw_draft in enumerate(parsed):
        normalized = _normalize_draft(raw_draft, default_channel=channel)
        if normalized is None:
            continue
        scrubbed, scrubs = _scrub_draft(normalized)
        if scrubbed is None:
            warnings.append(
                f"Draft #{idx + 1} dropped by safety stack: "
                f"{', '.join(scrubs) or 'unspecified'}."
            )
            continue
        scrubbed["scrubs_fired"] = scrubs
        cleaned.append(scrubbed)

    # Deterministic fallback: when the LLM produced nothing usable
    # (network failure, prose-only reply, every draft scrubbed), build
    # a safe draft from the lead + advisor + interested-vehicle data
    # directly. Always run it through the scrub stack for defense in
    # depth — by construction it should be a no-op.
    if not cleaned:
        fallback = _build_fallback_draft(
            lead=lead, advisor=advisor, channel=channel
        )
        scrubbed_fallback, fallback_scrubs = _scrub_draft(fallback)
        if scrubbed_fallback is not None:
            scrubbed_fallback["scrubs_fired"] = fallback_scrubs
            cleaned.append(scrubbed_fallback)
            warnings.append(
                "Showing a deterministic fallback draft assembled from "
                "the lead context — review and personalize before sending."
            )
        else:
            # Defensive: should never happen since the fallback content
            # is hand-curated, but logged loud if it does.
            logger.error(
                "follow_up fallback was rejected by the safety stack "
                "(lead=%s, advisor=%s, scrubs=%s)",
                lead.pk,
                advisor.slug,
                fallback_scrubs,
            )
            warnings.append(
                "Fallback draft was unexpectedly rejected by the safety "
                "stack — please compose the message manually."
            )

    return FollowUpResult(
        lead_id=lead.pk,
        salesperson_slug=advisor.slug,
        drafts=cleaned[:draft_count],
        warnings=warnings,
    )
