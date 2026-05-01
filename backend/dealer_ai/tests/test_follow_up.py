"""Manager Phase 4: AI follow-up draft generator + endpoint."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import List

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import CustomerLead, Salesperson, Vehicle
from dealer_ai.services import follow_up as follow_up_svc
from dealer_ai.services.follow_up import generate_follow_up_drafts
from dealer_ai.tests._mocks import MockLLMProvider


def _make_advisor(**extra) -> Salesperson:
    defaults = dict(
        slug="maria-cortez",
        name="Maria Cortez",
        title="Senior Truck Specialist",
        specialties=["F-150", "Trucks"],
        is_active=True,
    )
    defaults.update(extra)
    return Salesperson.objects.create(**defaults)


def _make_vehicle(stock: str, price: str = "30000.00", model: str = "F-150") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


def _make_lead(advisor: Salesperson, *, name: str = "Casey Morales") -> CustomerLead:
    lead = CustomerLead.objects.create(
        name=name,
        urgency="this_week",
        target_monthly_payment=Decimal("500"),
        down_payment=Decimal("1000"),
        conversation_summary=(
            "Wants a Ranger in the $500/mo range. Open to used."
        ),
        recommended_next_action=(
            "Confirm Ranger inventory and prep a real quote."
        ),
        assigned_to=advisor,
    )
    v = _make_vehicle("FF-USED-104", "26995.00", model="Ranger")
    lead.interested_vehicles.add(v)
    return lead


def _good_drafts_json(channel: str = "sms") -> str:
    return json.dumps(
        [
            {
                "channel": channel,
                "subject": None if channel == "sms" else "Following up on the Ranger",
                "body": (
                    "Hi Casey — Maria from Freedom Ford. Quick follow-up on the "
                    "Ranger XLT (Stock #FF-USED-104). Want me to line up a time? "
                    "(Estimates W.A.C.) — Maria"
                ),
            },
            {
                "channel": channel,
                "subject": None if channel == "sms" else "Quick note from Freedom Ford",
                "body": (
                    "Hey Casey — checking in on the Ranger. Whenever works for "
                    "you, I'll line up a time. Thanks, Maria"
                ),
            },
        ]
    )


def _dirty_drafts_json() -> str:
    return json.dumps(
        [
            # Variant 1: rate language → scrubbed inline.
            {
                "channel": "sms",
                "subject": None,
                "body": (
                    "Hi Casey — at 7.49% APR over 60 months, your payment "
                    "looks great. Maria"
                ),
            },
            # Variant 2: dealer-cost leak → drop entirely.
            {
                "channel": "sms",
                "subject": None,
                "body": (
                    "Our dealer cost on this Ranger is around $24,000 so we "
                    "have wiggle room. Maria"
                ),
            },
            # Variant 3: invented appointment → scrubbed inline.
            {
                "channel": "sms",
                "subject": None,
                "body": (
                    "Hi Casey — I have you down for Saturday at 1 PM at "
                    "Freedom Ford. See you then! Maria"
                ),
            },
        ]
    )


class FollowUpServiceTests(TestCase):
    def setUp(self):
        self.advisor = _make_advisor()
        self.lead = _make_lead(self.advisor)

    def test_generate_returns_drafts(self):
        provider = MockLLMProvider(replies=[_good_drafts_json("sms")])
        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            channel="sms",
            tone="warm",
            provider=provider,
        )
        self.assertEqual(result.lead_id, self.lead.pk)
        self.assertEqual(result.salesperson_slug, "maria-cortez")
        self.assertGreaterEqual(len(result.drafts), 1)
        for d in result.drafts:
            self.assertEqual(d["channel"], "sms")
            self.assertIsNone(d["subject"])
            self.assertTrue(d["body"])
            self.assertIn("scrubs_fired", d)

    def test_email_drafts_carry_subject(self):
        provider = MockLLMProvider(replies=[_good_drafts_json("email")])
        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            channel="email",
            tone="warm",
            provider=provider,
        )
        self.assertGreaterEqual(len(result.drafts), 1)
        for d in result.drafts:
            self.assertEqual(d["channel"], "email")
            self.assertTrue(d["subject"])

    def test_unsupported_channel_raises(self):
        provider = MockLLMProvider(replies=[_good_drafts_json("sms")])
        with self.assertRaises(ValueError):
            generate_follow_up_drafts(
                lead=self.lead,
                advisor=self.advisor,
                channel="phone-call",
                tone="warm",
                provider=provider,
            )

    def test_unsupported_tone_raises(self):
        provider = MockLLMProvider(replies=[_good_drafts_json("sms")])
        with self.assertRaises(ValueError):
            generate_follow_up_drafts(
                lead=self.lead,
                advisor=self.advisor,
                channel="sms",
                tone="hostile",
                provider=provider,
            )

    def test_unparseable_llm_returns_fallback_draft(self):
        # Phase 4 hardening: unparseable LLM output must not leave the
        # modal blank. The service substitutes a deterministic draft
        # built from real lead + advisor data.
        provider = MockLLMProvider(replies=["not json sorry"])
        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            provider=provider,
        )
        self.assertEqual(len(result.drafts), 1)
        self.assertEqual(result.drafts[0]["source"], "fallback")
        # Real first names of customer + advisor present.
        self.assertIn("Casey", result.drafts[0]["body"])
        self.assertIn("Maria", result.drafts[0]["body"])
        # Real interested-vehicle stock number woven in.
        self.assertIn("FF-USED-104", result.drafts[0]["body"])
        # Warning surfaces the parseability problem.
        self.assertTrue(
            any("parseable" in w.lower() for w in result.warnings)
        )

    def test_provider_exception_returns_fallback_draft(self):
        class BoomProvider(MockLLMProvider):
            def chat(self, *a, **kw):
                raise RuntimeError("simulated outage")

        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            provider=BoomProvider(),
        )
        self.assertEqual(len(result.drafts), 1)
        self.assertEqual(result.drafts[0]["source"], "fallback")
        self.assertTrue(any("LLM call failed" in w for w in result.warnings))


class FollowUpParserResilienceTests(TestCase):
    """Phase 4 hardening: the layered parser must recover usable drafts
    when Ollama returns prose around the JSON, a single object instead
    of an array, or markdown fences. When nothing recovers, the service
    must still return a deterministic fallback draft."""

    def setUp(self):
        self.advisor = _make_advisor()
        self.lead = _make_lead(self.advisor)

    def test_prose_wrapped_json_array_parses(self):
        wrapped = (
            "Sure! Here are the drafts:\n\n"
            + _good_drafts_json("sms")
            + "\n\nHope this helps!"
        )
        provider = MockLLMProvider(replies=[wrapped])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        # Real LLM drafts came through (not a fallback).
        self.assertGreaterEqual(len(result.drafts), 1)
        self.assertTrue(any(d["source"] == "llm" for d in result.drafts))

    def test_markdown_fence_wrapped_json_parses(self):
        fenced = "```json\n" + _good_drafts_json("sms") + "\n```"
        provider = MockLLMProvider(replies=[fenced])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        self.assertGreaterEqual(len(result.drafts), 1)
        self.assertTrue(any(d["source"] == "llm" for d in result.drafts))

    def test_single_object_coerced_to_single_draft(self):
        # LLM returns a bare {...} instead of [{...}].
        single = json.dumps(
            {
                "channel": "sms",
                "subject": None,
                "body": (
                    "Hi Casey — Maria from Freedom Ford. Quick check-in. "
                    "(W.A.C.) — Maria"
                ),
            }
        )
        provider = MockLLMProvider(replies=[single])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        self.assertEqual(len(result.drafts), 1)
        self.assertEqual(result.drafts[0]["source"], "llm")

    def test_balanced_brace_walk_recovers_objects_from_prose(self):
        # No surrounding [ ], just two object-literals interleaved with
        # prose. The walker should still pick them up.
        prose = (
            "Got it — here's the first one:\n"
            "{\"channel\": \"sms\", \"subject\": null, \"body\": "
            "\"Hi Casey — quick note from Maria. (W.A.C.)\"}\n"
            "and the second:\n"
            "{\"channel\": \"sms\", \"subject\": null, \"body\": "
            "\"Hey Casey — Maria again. Whenever works.\"}"
        )
        provider = MockLLMProvider(replies=[prose])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        self.assertGreaterEqual(len(result.drafts), 1)
        self.assertTrue(any(d["source"] == "llm" for d in result.drafts))

    def test_empty_llm_reply_returns_fallback(self):
        provider = MockLLMProvider(replies=[""])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        self.assertEqual(len(result.drafts), 1)
        self.assertEqual(result.drafts[0]["source"], "fallback")

    def test_fallback_uses_real_advisor_first_name(self):
        provider = MockLLMProvider(replies=[""])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        body = result.drafts[0]["body"]
        # Advisor first name only, never the full name.
        self.assertIn("Maria", body)
        self.assertNotIn("Maria Cortez", body)

    def test_email_fallback_has_subject(self):
        provider = MockLLMProvider(replies=[""])
        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            channel="email",
            provider=provider,
        )
        self.assertEqual(len(result.drafts), 1)
        self.assertEqual(result.drafts[0]["source"], "fallback")
        self.assertEqual(result.drafts[0]["channel"], "email")
        self.assertIsNotNone(result.drafts[0]["subject"])
        self.assertIn("Freedom Ford", result.drafts[0]["subject"])

    def test_fallback_when_lead_has_no_interested_vehicles(self):
        # Strip the vehicle relation — fallback should still produce a
        # safe, generic draft that doesn't reference a fabricated unit.
        self.lead.interested_vehicles.clear()
        provider = MockLLMProvider(replies=[""])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        self.assertEqual(len(result.drafts), 1)
        body = result.drafts[0]["body"]
        # Customer + advisor names are still present.
        self.assertIn("Casey", body)
        self.assertIn("Maria", body)
        # No fake stock number woven in.
        self.assertNotIn("Stock #", body)

    def test_fallback_draft_passes_safety_scrubs(self):
        # Hand-curated content but we still run it through the scrub
        # stack. Defensive: confirm scrubs_fired is empty (deterministic
        # content shouldn't trigger anything).
        provider = MockLLMProvider(replies=["not json"])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        self.assertEqual(result.drafts[0]["scrubs_fired"], [])

    def test_all_drafts_dropped_by_scrubs_falls_back_to_fallback(self):
        # Every LLM-produced variant has dealer-cost language → all
        # dropped → fallback should kick in.
        dirty = json.dumps(
            [
                {
                    "channel": "sms",
                    "subject": None,
                    "body": "Our dealer cost is around $24,000 — Maria",
                },
                {
                    "channel": "sms",
                    "subject": None,
                    "body": "Our internal cost on this Ranger is low — Maria",
                },
            ]
        )
        provider = MockLLMProvider(replies=[dirty])
        result = generate_follow_up_drafts(
            lead=self.lead, advisor=self.advisor, provider=provider
        )
        self.assertEqual(len(result.drafts), 1)
        self.assertEqual(result.drafts[0]["source"], "fallback")
        # And the warnings note both the drops and the fallback.
        joined = " ".join(result.warnings).lower()
        self.assertIn("dropped", joined)
        self.assertIn("fallback", joined)


class FollowUpScrubTests(TestCase):
    def setUp(self):
        self.advisor = _make_advisor()
        self.lead = _make_lead(self.advisor)

    def test_rate_language_scrubbed(self):
        provider = MockLLMProvider(replies=[_dirty_drafts_json()])
        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            provider=provider,
        )
        for d in result.drafts:
            self.assertNotIn("APR", d["body"])
            self.assertNotIn("7.49%", d["body"])

    def test_dealer_cost_draft_dropped(self):
        provider = MockLLMProvider(replies=[_dirty_drafts_json()])
        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            provider=provider,
        )
        for d in result.drafts:
            self.assertNotIn("dealer cost", d["body"].lower())
        self.assertTrue(
            any("dropped" in w.lower() for w in result.warnings)
        )

    def test_invented_appointment_scrubbed(self):
        provider = MockLLMProvider(replies=[_dirty_drafts_json()])
        result = generate_follow_up_drafts(
            lead=self.lead,
            advisor=self.advisor,
            provider=provider,
        )
        all_bodies = " ".join(d["body"].lower() for d in result.drafts)
        self.assertNotIn("have you down", all_bodies)
        self.assertNotIn("see you saturday at 1 pm", all_bodies)


class FollowUpEndpointTests(TestCase):
    def setUp(self):
        self.advisor = _make_advisor()
        self.other = _make_advisor(slug="other", name="Other Advisor")
        self.lead = _make_lead(self.advisor)

        original = follow_up_svc.get_llm_provider
        self._scripted: List[str] = [_good_drafts_json("sms")]

        def _patched():
            return MockLLMProvider(replies=self._scripted)

        follow_up_svc.get_llm_provider = _patched  # type: ignore[assignment]
        self.addCleanup(setattr, follow_up_svc, "get_llm_provider", original)

    def test_post_returns_drafts(self):
        url = reverse(
            "dealer_ai:advisor-follow-up",
            args=[self.advisor.slug, self.lead.pk],
        )
        res = self.client.post(
            url,
            data=json.dumps({"channel": "sms", "tone": "warm"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data["lead_id"], self.lead.pk)
        self.assertEqual(data["salesperson_slug"], self.advisor.slug)
        self.assertGreaterEqual(len(data["drafts"]), 1)

    def test_400_for_unknown_channel(self):
        url = reverse(
            "dealer_ai:advisor-follow-up",
            args=[self.advisor.slug, self.lead.pk],
        )
        res = self.client.post(
            url,
            data=json.dumps({"channel": "phone-call"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_404_for_unknown_advisor(self):
        url = reverse(
            "dealer_ai:advisor-follow-up", args=["nope", self.lead.pk]
        )
        res = self.client.post(
            url,
            data=json.dumps({"channel": "sms"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_404_for_unknown_lead(self):
        url = reverse(
            "dealer_ai:advisor-follow-up",
            args=[self.advisor.slug, 999_999],
        )
        res = self.client.post(
            url,
            data=json.dumps({"channel": "sms"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_403_when_lead_belongs_to_other_advisor(self):
        url = reverse(
            "dealer_ai:advisor-follow-up",
            args=[self.other.slug, self.lead.pk],
        )
        res = self.client.post(
            url,
            data=json.dumps({"channel": "sms"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)
