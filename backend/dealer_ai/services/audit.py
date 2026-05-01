"""Manager Phase 1: AI safety / guard event aggregation.

Surfaces the Phase 8m–8r guard activity stored in
ChatMessage.metadata.flag so the manager dashboard can show "what the
AI declined / scrubbed today". Aggregation is in-memory (SQLite +
Postgres portable, demo-scale).

Public surface:

- ``audit_events_snapshot(since_hours, recent_limit)`` → ``dict``
  Used by ``GET /api/dealer-ai/admin/audit-events/``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from ..models import ChatMessage


# Categorize every flag value the chat engine + vehicle-ask path can
# emit. Severity drives frontend color coding.
#
#   info  — pre-LLM short-circuit (customer asked something the AI
#           shouldn't answer; deterministic refusal). Healthy signal.
#   warn  — post-LLM rewrite or override. The model produced something
#           unsafe and the safety layer caught it. Worth investigating
#           if rates trend up.
#   muted — partial post-LLM scrub. Self-healing; lowest urgency.
_FLAG_CATEGORIES: Dict[str, str] = {
    # Pre-LLM short-circuits
    "prompt_injection": "pre_llm_guard",
    "rate_inquiry": "pre_llm_guard",
    "external_value_inquiry": "pre_llm_guard",
    "identity_request": "pre_llm_guard",
    "negotiation_request": "pre_llm_guard",
    "handoff_request": "pre_llm_guard",
    "image_request": "pre_llm_guard",
    "image_request_needs_vehicle": "pre_llm_guard",
    "appointment_request": "pre_llm_guard",
    "appointment_request_needs_vehicle": "pre_llm_guard",
    # Post-LLM wholesale rewrites
    "post_llm_safety_rewrite": "post_llm_rewrite",
    "internal_confusion_fallback": "post_llm_rewrite",
    "fabricated_inventory": "post_llm_rewrite",
    # Post-LLM override (negotiation / fake-transfer leakage)
    "post_llm_override": "post_llm_override",
    # Post-LLM partial scrubs
    "rate_language_scrubbed": "scrub",
    "internal_directive_scrubbed": "scrub",
    "default_assumption_scrubbed": "scrub",
    "category_label_scrubbed": "scrub",
    "multiple_scrubs_fired": "scrub",
}

_CATEGORY_SEVERITY: Dict[str, str] = {
    "pre_llm_guard": "info",
    "post_llm_rewrite": "warn",
    "post_llm_override": "warn",
    "scrub": "muted",
}


_SUPPORTED_WINDOWS: Dict[str, int] = {
    "24h": 24,
    "7d": 24 * 7,
    "30d": 24 * 30,
}


def _resolve_window(since: Optional[str]) -> tuple[str, int]:
    """Return (canonical_label, hours). Falls back to 24h on garbage."""
    if since in _SUPPORTED_WINDOWS:
        return since, _SUPPORTED_WINDOWS[since]
    return "24h", _SUPPORTED_WINDOWS["24h"]


def _excerpt(text: Optional[str], limit: int = 160) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _preceding_user_message(msg: ChatMessage) -> Optional[ChatMessage]:
    """Return the most recent user message in the same session that
    came strictly before this assistant message — i.e., the prompt
    that triggered the guard."""
    if msg.session_id is None:
        return None
    return (
        ChatMessage.objects.filter(
            session_id=msg.session_id,
            role="user",
            created_at__lt=msg.created_at,
        )
        .order_by("-created_at")
        .first()
    )


def audit_events_snapshot(
    since: str = "24h", recent_limit: int = 50
) -> Dict[str, Any]:
    """Return a snapshot of guard events in the requested time window.

    Shape (deterministic, additive on the existing `metadata` field;
    no schema change anywhere):

    .. code-block:: json

        {
          "since": "24h",
          "window_hours": 24,
          "generated_at": "2026-05-01T...Z",
          "totals": {
            "total_guard_events": int,
            "pre_llm_short_circuits": int,
            "post_llm_rewrites": int,
            "post_llm_overrides": int,
            "scrubs_fired": int
          },
          "by_flag": [{flag, count, category, severity}, ...],
          "recent_events": [{session_id, message_id, created_at, flag,
                              category, user_message_excerpt,
                              assistant_excerpt, scrubs, override_kind}, ...]
        }
    """
    canonical_since, hours = _resolve_window(since)
    cutoff = timezone.now() - timedelta(hours=hours)

    # Pull every flagged assistant message in the window. Demo scale.
    flagged_qs = (
        ChatMessage.objects.filter(role="assistant", created_at__gte=cutoff)
        .order_by("-created_at")
        .iterator()
    )

    by_flag_count: Dict[str, int] = {}
    recent_events: List[Dict[str, Any]] = []
    totals = {
        "total_guard_events": 0,
        "pre_llm_short_circuits": 0,
        "post_llm_rewrites": 0,
        "post_llm_overrides": 0,
        "scrubs_fired": 0,
    }

    for msg in flagged_qs:
        flag = (msg.metadata or {}).get("flag")
        if not flag:
            continue
        category = _FLAG_CATEGORIES.get(flag)
        if category is None:
            # Unknown flag value — count toward total but skip categorized
            # totals. Surfaces new flag types without breaking the panel.
            category = "unknown"
        totals["total_guard_events"] += 1
        if category == "pre_llm_guard":
            totals["pre_llm_short_circuits"] += 1
        elif category == "post_llm_rewrite":
            totals["post_llm_rewrites"] += 1
        elif category == "post_llm_override":
            totals["post_llm_overrides"] += 1
        elif category == "scrub":
            totals["scrubs_fired"] += 1
        by_flag_count[flag] = by_flag_count.get(flag, 0) + 1

        if len(recent_events) < recent_limit:
            user_msg = _preceding_user_message(msg)
            recent_events.append(
                {
                    "session_id": str(msg.session_id) if msg.session_id else None,
                    "message_id": msg.id,
                    "created_at": msg.created_at.isoformat(),
                    "flag": flag,
                    "category": category,
                    "user_message_excerpt": _excerpt(
                        user_msg.content if user_msg else None
                    ),
                    "assistant_excerpt": _excerpt(msg.content),
                    "scrubs": list((msg.metadata or {}).get("scrubs") or []),
                    "override_kind": (msg.metadata or {}).get("override_kind"),
                }
            )

    # Render by_flag in count-desc, then alpha for stable UX.
    by_flag = [
        {
            "flag": flag,
            "count": count,
            "category": _FLAG_CATEGORIES.get(flag, "unknown"),
            "severity": _CATEGORY_SEVERITY.get(
                _FLAG_CATEGORIES.get(flag, "unknown"), "muted"
            ),
        }
        for flag, count in sorted(
            by_flag_count.items(), key=lambda kv: (-kv[1], kv[0])
        )
    ]

    return {
        "since": canonical_since,
        "window_hours": hours,
        "generated_at": timezone.now().isoformat(),
        "totals": totals,
        "by_flag": by_flag,
        "recent_events": recent_events,
    }
