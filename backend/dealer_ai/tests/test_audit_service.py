"""Manager Phase 1: audit/safety panel tests.

Verifies audit_events_snapshot aggregates ChatMessage.metadata.flag
correctly into category totals, by-flag counts, and recent-event
excerpts. Also verifies the GET /admin/audit-events/ endpoint shape.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import ChatMessage, ChatSession
from dealer_ai.services.audit import audit_events_snapshot


def _msg(
    session: ChatSession,
    *,
    role: str,
    content: str,
    metadata: dict | None = None,
    age_hours: float = 0.5,
) -> ChatMessage:
    """Create a ChatMessage with a forced created_at offset."""
    msg = ChatMessage.objects.create(
        session=session,
        role=role,
        content=content,
        metadata=metadata or {},
    )
    if age_hours:
        ChatMessage.objects.filter(pk=msg.pk).update(
            created_at=timezone.now() - timedelta(hours=age_hours)
        )
        msg.refresh_from_db()
    return msg


class AuditEventsSnapshotShapeTests(TestCase):
    """Empty + minimal shape locks."""

    def test_empty_database_returns_zero_counts(self):
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["since"], "24h")
        self.assertEqual(snap["window_hours"], 24)
        self.assertEqual(snap["totals"]["total_guard_events"], 0)
        self.assertEqual(snap["totals"]["pre_llm_short_circuits"], 0)
        self.assertEqual(snap["totals"]["post_llm_rewrites"], 0)
        self.assertEqual(snap["totals"]["post_llm_overrides"], 0)
        self.assertEqual(snap["totals"]["scrubs_fired"], 0)
        self.assertEqual(snap["by_flag"], [])
        self.assertEqual(snap["recent_events"], [])

    def test_unsupported_since_falls_back_to_24h(self):
        snap = audit_events_snapshot(since="garbage")
        self.assertEqual(snap["since"], "24h")
        self.assertEqual(snap["window_hours"], 24)

    def test_supported_windows(self):
        for label, hours in [("24h", 24), ("7d", 168), ("30d", 720)]:
            snap = audit_events_snapshot(since=label)
            self.assertEqual(snap["since"], label)
            self.assertEqual(snap["window_hours"], hours)


class AuditEventsCategoryTotalTests(TestCase):
    """Category totals must match the sum of their flag values."""

    def setUp(self):
        self.session = ChatSession.objects.create()

    def test_pre_llm_guards_aggregate_under_pre_llm_short_circuits(self):
        for flag in ["rate_inquiry", "negotiation_request", "handoff_request"]:
            _msg(
                self.session, role="assistant", content=f"reply {flag}",
                metadata={"provider": "guard", "flag": flag},
            )
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["totals"]["pre_llm_short_circuits"], 3)
        self.assertEqual(snap["totals"]["post_llm_rewrites"], 0)
        self.assertEqual(snap["totals"]["scrubs_fired"], 0)
        self.assertEqual(snap["totals"]["total_guard_events"], 3)

    def test_post_llm_rewrites_categorized_correctly(self):
        for flag in ["post_llm_safety_rewrite", "internal_confusion_fallback"]:
            _msg(
                self.session, role="assistant", content="rewritten",
                metadata={"flag": flag},
            )
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["totals"]["post_llm_rewrites"], 2)
        self.assertEqual(snap["totals"]["pre_llm_short_circuits"], 0)

    def test_post_llm_override_separate_total(self):
        _msg(
            self.session, role="assistant", content="overridden",
            metadata={"flag": "post_llm_override", "override_kind": "negotiation"},
        )
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["totals"]["post_llm_overrides"], 1)
        self.assertEqual(snap["totals"]["post_llm_rewrites"], 0)

    def test_scrubs_categorized_as_scrub(self):
        for flag in [
            "rate_language_scrubbed", "internal_directive_scrubbed",
            "default_assumption_scrubbed", "category_label_scrubbed",
            "multiple_scrubs_fired",
        ]:
            _msg(
                self.session, role="assistant", content=f"scrubbed {flag}",
                metadata={"flag": flag},
            )
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["totals"]["scrubs_fired"], 5)
        self.assertEqual(snap["totals"]["total_guard_events"], 5)

    def test_messages_without_flag_are_ignored(self):
        # Plain chat turn (no guard fired) — must not count.
        _msg(self.session, role="assistant", content="plain reply")
        _msg(self.session, role="assistant", content="plain too", metadata={})
        _msg(
            self.session, role="assistant", content="provider only",
            metadata={"provider": "ollama"},
        )
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["totals"]["total_guard_events"], 0)

    def test_user_role_messages_are_ignored(self):
        _msg(
            self.session, role="user", content="customer text",
            metadata={"flag": "prompt_injection"},  # the user-flag form
        )
        snap = audit_events_snapshot(since="24h")
        # The audit panel only counts ASSISTANT-side guard events.
        self.assertEqual(snap["totals"]["total_guard_events"], 0)


class AuditEventsByFlagListTests(TestCase):
    def test_by_flag_sorted_count_desc_then_alpha(self):
        session = ChatSession.objects.create()
        # 3 rate_inquiry, 1 negotiation_request, 2 handoff_request.
        for _ in range(3):
            _msg(session, role="assistant", content="r",
                 metadata={"flag": "rate_inquiry"})
        _msg(session, role="assistant", content="n",
             metadata={"flag": "negotiation_request"})
        for _ in range(2):
            _msg(session, role="assistant", content="h",
                 metadata={"flag": "handoff_request"})
        snap = audit_events_snapshot(since="24h")
        flags = [(b["flag"], b["count"]) for b in snap["by_flag"]]
        # rate(3) > handoff(2) > negotiation(1), alpha tiebreak unused.
        self.assertEqual(
            flags,
            [
                ("rate_inquiry", 3),
                ("handoff_request", 2),
                ("negotiation_request", 1),
            ],
        )

    def test_by_flag_carries_category_and_severity(self):
        session = ChatSession.objects.create()
        _msg(session, role="assistant", content="r",
             metadata={"flag": "rate_inquiry"})
        _msg(session, role="assistant", content="rw",
             metadata={"flag": "post_llm_safety_rewrite"})
        _msg(session, role="assistant", content="sc",
             metadata={"flag": "rate_language_scrubbed"})
        snap = audit_events_snapshot(since="24h")
        cats = {b["flag"]: (b["category"], b["severity"]) for b in snap["by_flag"]}
        self.assertEqual(cats["rate_inquiry"], ("pre_llm_guard", "info"))
        self.assertEqual(
            cats["post_llm_safety_rewrite"], ("post_llm_rewrite", "warn")
        )
        self.assertEqual(
            cats["rate_language_scrubbed"], ("scrub", "muted")
        )


class AuditEventsRecentExcerptTests(TestCase):
    """recent_events should pair the assistant turn with the immediately
    preceding user message in the same session, ordered by -created_at,
    truncated at 160 chars."""

    def test_recent_event_includes_preceding_user_message(self):
        session = ChatSession.objects.create()
        _msg(
            session, role="user",
            content="Will you match this price?",
            age_hours=1.0,
        )
        _msg(
            session, role="assistant",
            content="I get what you're trying to do.",
            metadata={"flag": "negotiation_request"},
            age_hours=0.99,
        )
        snap = audit_events_snapshot(since="24h", recent_limit=5)
        self.assertEqual(len(snap["recent_events"]), 1)
        ev = snap["recent_events"][0]
        self.assertEqual(ev["flag"], "negotiation_request")
        self.assertEqual(
            ev["user_message_excerpt"], "Will you match this price?"
        )
        self.assertIn("I get what", ev["assistant_excerpt"])
        self.assertEqual(ev["category"], "pre_llm_guard")
        self.assertEqual(ev["scrubs"], [])
        self.assertIsNone(ev["override_kind"])

    def test_recent_event_with_no_preceding_user_msg_has_empty_excerpt(self):
        # Edge case: assistant message exists with no prior user turn
        # in the session (shouldn't happen in normal flow but lock it).
        session = ChatSession.objects.create()
        _msg(
            session, role="assistant",
            content="orphan reply",
            metadata={"flag": "rate_inquiry"},
        )
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["recent_events"][0]["user_message_excerpt"], "")

    def test_recent_events_ordered_newest_first(self):
        session = ChatSession.objects.create()
        _msg(
            session, role="assistant", content="oldest",
            metadata={"flag": "rate_inquiry"}, age_hours=10,
        )
        _msg(
            session, role="assistant", content="middle",
            metadata={"flag": "negotiation_request"}, age_hours=5,
        )
        _msg(
            session, role="assistant", content="newest",
            metadata={"flag": "handoff_request"}, age_hours=1,
        )
        snap = audit_events_snapshot(since="24h", recent_limit=10)
        excerpts = [e["assistant_excerpt"] for e in snap["recent_events"]]
        self.assertEqual(excerpts, ["newest", "middle", "oldest"])

    def test_excerpt_truncated_at_160_chars(self):
        session = ChatSession.objects.create()
        long_user = "x" * 250
        long_assistant = "y" * 250
        _msg(session, role="user", content=long_user, age_hours=1)
        _msg(
            session, role="assistant", content=long_assistant,
            metadata={"flag": "rate_inquiry"}, age_hours=0.99,
        )
        snap = audit_events_snapshot(since="24h")
        ev = snap["recent_events"][0]
        self.assertLessEqual(len(ev["user_message_excerpt"]), 160)
        self.assertLessEqual(len(ev["assistant_excerpt"]), 160)
        self.assertTrue(ev["user_message_excerpt"].endswith("…"))
        self.assertTrue(ev["assistant_excerpt"].endswith("…"))

    def test_recent_events_capped_by_limit(self):
        session = ChatSession.objects.create()
        for i in range(7):
            _msg(
                session, role="assistant", content=f"reply {i}",
                metadata={"flag": "rate_inquiry"},
                age_hours=0.5 + i * 0.1,
            )
        snap = audit_events_snapshot(since="24h", recent_limit=3)
        self.assertEqual(len(snap["recent_events"]), 3)
        # Counts still reflect the full set, not just the capped recent.
        self.assertEqual(snap["totals"]["total_guard_events"], 7)

    def test_scrubs_list_carried_into_recent_event(self):
        session = ChatSession.objects.create()
        _msg(session, role="user", content="q", age_hours=1)
        _msg(
            session, role="assistant", content="r",
            metadata={
                "flag": "multiple_scrubs_fired",
                "scrubs": ["rate_language", "internal_directive"],
            },
            age_hours=0.99,
        )
        snap = audit_events_snapshot(since="24h")
        ev = snap["recent_events"][0]
        self.assertEqual(
            ev["scrubs"], ["rate_language", "internal_directive"]
        )

    def test_override_kind_carried_into_recent_event(self):
        session = ChatSession.objects.create()
        _msg(session, role="user", content="q", age_hours=1)
        _msg(
            session, role="assistant", content="r",
            metadata={"flag": "post_llm_override", "override_kind": "negotiation"},
            age_hours=0.99,
        )
        snap = audit_events_snapshot(since="24h")
        ev = snap["recent_events"][0]
        self.assertEqual(ev["override_kind"], "negotiation")


class AuditEventsTimeWindowTests(TestCase):
    def test_since_24h_excludes_older_events(self):
        session = ChatSession.objects.create()
        _msg(
            session, role="assistant", content="recent",
            metadata={"flag": "rate_inquiry"}, age_hours=2,
        )
        _msg(
            session, role="assistant", content="old",
            metadata={"flag": "rate_inquiry"}, age_hours=48,
        )
        snap = audit_events_snapshot(since="24h")
        self.assertEqual(snap["totals"]["total_guard_events"], 1)
        self.assertEqual(snap["recent_events"][0]["assistant_excerpt"], "recent")

    def test_since_7d_includes_older_within_window(self):
        session = ChatSession.objects.create()
        _msg(
            session, role="assistant", content="3d",
            metadata={"flag": "rate_inquiry"}, age_hours=72,
        )
        _msg(
            session, role="assistant", content="10d",
            metadata={"flag": "rate_inquiry"}, age_hours=240,
        )
        snap = audit_events_snapshot(since="7d")
        self.assertEqual(snap["totals"]["total_guard_events"], 1)


class AuditEventsEndpointTests(TestCase):
    """GET /api/dealer-ai/admin/audit-events/ surface."""

    def test_endpoint_returns_200_when_empty(self):
        url = reverse("dealer_ai:admin-audit-events")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("totals", body)
        self.assertIn("by_flag", body)
        self.assertIn("recent_events", body)

    def test_endpoint_respects_since_param(self):
        url = reverse("dealer_ai:admin-audit-events")
        for label in ["24h", "7d", "30d"]:
            res = self.client.get(url, {"since": label})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["since"], label)

    def test_endpoint_clamps_limit(self):
        url = reverse("dealer_ai:admin-audit-events")
        # Garbage limit → defaults to 50.
        res = self.client.get(url, {"limit": "abc"})
        self.assertEqual(res.status_code, 200)
        # Out-of-range high → clamped (no error).
        res = self.client.get(url, {"limit": "10000"})
        self.assertEqual(res.status_code, 200)

    def test_endpoint_with_real_data(self):
        session = ChatSession.objects.create()
        _msg(session, role="user", content="lowest you'll take?", age_hours=1)
        _msg(
            session, role="assistant", content="advisor handles that",
            metadata={"flag": "negotiation_request"}, age_hours=0.99,
        )
        url = reverse("dealer_ai:admin-audit-events")
        res = self.client.get(url, {"since": "24h"})
        body = res.json()
        self.assertEqual(body["totals"]["total_guard_events"], 1)
        self.assertEqual(body["totals"]["pre_llm_short_circuits"], 1)
        self.assertEqual(len(body["recent_events"]), 1)
        self.assertEqual(
            body["recent_events"][0]["user_message_excerpt"],
            "lowest you'll take?",
        )
