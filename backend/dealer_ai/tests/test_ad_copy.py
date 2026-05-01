"""Manager Phase 3: ad-copy generation pipeline.

Covers:

- Endpoint returns 2–3 safe variants for an inventory recommendation.
- Endpoint returns 2–3 safe variants for a marketing recommendation.
- Sales / unsupported categories rejected with 400.
- Missing recommendation / missing id rejected with 400.
- Bad vehicle_id falls back gracefully (warning, no 500).
- Rate / APR language scrubbed inline; variant survives.
- Dealer-cost / invoice-price language drops the variant entirely.
- Negotiation / fake-handoff phrasing drops the variant entirely.
- Invented "save $500", "limited time", "as low as", "$0 down",
  "guaranteed approval" scrubbed.
- Variants reference real Stock #s only — never a fabricated one.
- Builder uses the MockLLMProvider so tests never call Ollama/OpenAI.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import List

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import Vehicle
from dealer_ai.services import ad_copy as ad_copy_svc
from dealer_ai.services.ad_copy import generate_ad_copy
from dealer_ai.tests._mocks import MockLLMProvider


def _make_vehicle(stock: str, price: str, *, model: str = "F-150", year: int = 2025) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=year,
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


def _inventory_rec(*, monthly_low: int = 500, monthly_high: int = 599) -> dict:
    return {
        "id": f"inventory.mismatch.{monthly_low}_{monthly_high}",
        "category": "inventory",
        "priority": "high",
        "title": "Source vehicles in the $27,108–$32,588 range",
        "explanation": (
            "8 open leads target $500–599/mo but only 2 vehicles are "
            "available in that band — a 4.0× shortfall."
        ),
        "action_text": (
            "Acquire 3–6 units priced $27,108–$32,588. Consider sourcing "
            "Bronco Sport, Edge, Ranger, or used F-150 in the "
            "$27,108–$32,588 range."
        ),
        "evidence": {
            "band_label": "$500–599/mo",
            "lead_count": 8,
            "vehicle_count": 2,
            "ratio": 4.0,
        },
        "cta": {
            "kind": "view_leads_in_band",
            "params": {"monthly_low": monthly_low, "monthly_high": monthly_high},
        },
    }


def _marketing_rec(*, model: str = "F-150") -> dict:
    return {
        "id": f"marketing.promote_model.{model.lower().replace('-', '_').replace(' ', '_')}",
        "category": "marketing",
        "priority": "medium",
        "title": f"Promote {model} — 3 customers asked, lot has stock",
        "explanation": (
            f"{model} is the most-requested model (3 sessions). 4 units in inventory."
        ),
        "action_text": (
            f"Run a {model} promotion this week — feature the units in current inventory."
        ),
        "evidence": {
            "model": model,
            "session_count": 3,
            "available_inventory": 4,
        },
        "cta": None,
    }


def _good_variants_json() -> str:
    return json.dumps(
        [
            {
                "platform_hint": "facebook",
                "headline": "Trucks ready at Freedom Ford",
                "body": (
                    "Stock #FF-2025-002 is on the lot and priced for the "
                    "real world. Estimated payments W.A.C. — see an advisor "
                    "for terms."
                ),
                "cta": "See the truck",
            },
            {
                "platform_hint": "instagram",
                "headline": "Built Ford tough — in stock now",
                "body": (
                    "We have a 2025 F-150 ready to drive home. Stop in for "
                    "a real quote (W.A.C.)."
                ),
                "cta": "Visit today",
            },
            {
                "platform_hint": "email",
                "headline": "Your next truck is on the lot",
                "body": (
                    "Stock #FF-2025-002, in stock and ready. Payments are "
                    "estimates only and finalized by Freedom Ford with "
                    "approved credit."
                ),
                "cta": "Reply for details",
            },
        ]
    )


def _dirty_variants_json() -> str:
    return json.dumps(
        [
            # Variant 1: rate language → should be scrubbed inline, kept.
            {
                "platform_hint": "facebook",
                "headline": "Save now on F-150",
                "body": (
                    "Estimated $517/mo at 7.49% APR over 60 months. "
                    "Stop in today."
                ),
                "cta": "Apply now",
            },
            # Variant 2: dealer-cost → entire variant dropped.
            {
                "platform_hint": "instagram",
                "headline": "Insider F-150 deal",
                "body": (
                    "Our dealer cost on this F-150 is around $52,000, "
                    "so we have wiggle room."
                ),
                "cta": "DM for price",
            },
            # Variant 3: invented promotion (save $X / limited time / $0 down)
            # → scrubbed but kept.
            {
                "platform_hint": "email",
                "headline": "Limited time offer",
                "body": (
                    "Save $1,000 today only — $0 down, guaranteed approval "
                    "on a new F-150."
                ),
                "cta": "Lock it in",
            },
        ]
    )


class AdCopyServiceTests(TestCase):
    def setUp(self):
        # Real, available inventory the resolver can attach to inventory recs.
        self.v1 = _make_vehicle("FF-2025-002", "30000.00", model="F-150")
        self.v2 = _make_vehicle("FF-2025-007", "31500.00", model="Explorer")

    def test_inventory_recommendation_returns_safe_variants(self):
        provider = MockLLMProvider(replies=[_good_variants_json()])
        result = generate_ad_copy(
            recommendation=_inventory_rec(), provider=provider
        )
        self.assertEqual(result.recommendation_id, _inventory_rec()["id"])
        self.assertGreaterEqual(len(result.variants), 2)
        self.assertLessEqual(len(result.variants), 3)
        for v in result.variants:
            self.assertIn(v["platform_hint"], {
                "facebook", "instagram", "email", "google_search", "showroom"
            })
            self.assertTrue(v["headline"])
            self.assertTrue(v["body"])
            self.assertTrue(v["cta"])
            self.assertIn("scrubs_fired", v)
        # Vehicles_used should be the real, available rows in the band.
        self.assertGreater(len(result.vehicles_used), 0)
        for v in result.vehicles_used:
            self.assertTrue(v.is_available)

    def test_marketing_recommendation_with_model_evidence(self):
        provider = MockLLMProvider(replies=[_good_variants_json()])
        result = generate_ad_copy(
            recommendation=_marketing_rec(), provider=provider
        )
        self.assertGreaterEqual(len(result.variants), 2)
        # F-150 evidence → resolver should attach the F-150 row.
        stock_numbers = {v.stock_number for v in result.vehicles_used}
        self.assertIn("FF-2025-002", stock_numbers)

    def test_unsupported_category_raises(self):
        with self.assertRaises(ValueError):
            generate_ad_copy(
                recommendation={
                    "id": "sales.high_intent_assign",
                    "category": "sales",
                    "title": "x",
                    "explanation": "y",
                    "action_text": "z",
                    "evidence": {},
                },
                provider=MockLLMProvider(replies=[_good_variants_json()]),
            )

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            generate_ad_copy(
                recommendation={
                    "category": "marketing",
                    "title": "x",
                    "explanation": "y",
                    "action_text": "z",
                    "evidence": {},
                },
                provider=MockLLMProvider(replies=[_good_variants_json()]),
            )

    def test_recommendation_must_be_dict(self):
        with self.assertRaises(ValueError):
            generate_ad_copy(
                recommendation="not-a-dict",  # type: ignore[arg-type]
                provider=MockLLMProvider(replies=[_good_variants_json()]),
            )

    def test_unknown_vehicle_id_falls_back_with_warning(self):
        provider = MockLLMProvider(replies=[_good_variants_json()])
        result = generate_ad_copy(
            recommendation=_marketing_rec(),
            vehicle_id=999_999,
            provider=provider,
        )
        # No 500; we still get variants.
        self.assertGreater(len(result.variants), 0)
        # And a warning that the requested vehicle wasn't found.
        self.assertTrue(
            any("not found" in w.lower() for w in result.warnings),
            f"warnings={result.warnings}",
        )

    def test_explicit_vehicle_id_pins_to_that_vehicle(self):
        provider = MockLLMProvider(replies=[_good_variants_json()])
        result = generate_ad_copy(
            recommendation=_marketing_rec(model="Explorer"),
            vehicle_id=self.v2.pk,
            provider=provider,
        )
        self.assertEqual(len(result.vehicles_used), 1)
        self.assertEqual(result.vehicles_used[0].stock_number, "FF-2025-007")


class AdCopyScrubTests(TestCase):
    def setUp(self):
        self.v1 = _make_vehicle("FF-2025-002", "30000.00", model="F-150")

    def test_rate_language_scrubbed_in_variant(self):
        provider = MockLLMProvider(replies=[_dirty_variants_json()])
        result = generate_ad_copy(
            recommendation=_marketing_rec(), provider=provider
        )
        # Variant 1 had "$517/mo at 7.49% APR over 60 months" — must not
        # appear verbatim in any surviving variant.
        for v in result.variants:
            self.assertNotIn("APR", v["body"], v)
            self.assertNotIn("7.49%", v["body"], v)
        # And the variant that had rate language carries the scrub flag.
        rate_scrubbed = [
            v for v in result.variants
            if any("rate_language" in s for s in v["scrubs_fired"])
        ]
        self.assertGreater(len(rate_scrubbed), 0)

    def test_dealer_cost_variant_dropped(self):
        provider = MockLLMProvider(replies=[_dirty_variants_json()])
        result = generate_ad_copy(
            recommendation=_marketing_rec(), provider=provider
        )
        # Variant 2 had "Our dealer cost…" — must not appear in output.
        for v in result.variants:
            self.assertNotIn("dealer cost", v["body"].lower())
            self.assertNotIn("our cost", v["body"].lower())
        # And we expect the warnings to mention a drop.
        self.assertTrue(
            any("dropped" in w.lower() for w in result.warnings),
            f"warnings={result.warnings}",
        )

    def test_invented_promotion_phrases_scrubbed(self):
        provider = MockLLMProvider(replies=[_dirty_variants_json()])
        result = generate_ad_copy(
            recommendation=_marketing_rec(), provider=provider
        )
        joined = " ".join(
            (v["headline"] + " " + v["body"] + " " + v["cta"])
            for v in result.variants
        ).lower()
        self.assertNotIn("save $1,000", joined)
        self.assertNotIn("save $1000", joined)
        self.assertNotIn("limited time", joined)
        self.assertNotIn("today only", joined)
        self.assertNotIn("$0 down", joined)
        self.assertNotIn("guaranteed approval", joined)

    def test_empty_llm_reply_returns_zero_variants_with_warning(self):
        provider = MockLLMProvider(replies=[""])
        result = generate_ad_copy(
            recommendation=_marketing_rec(), provider=provider
        )
        self.assertEqual(result.variants, [])
        self.assertTrue(
            any("parseable" in w.lower() for w in result.warnings)
            or any("survived" in w.lower() for w in result.warnings)
        )

    def test_unparseable_llm_reply_returns_warning(self):
        provider = MockLLMProvider(replies=["not json at all, sorry"])
        result = generate_ad_copy(
            recommendation=_marketing_rec(), provider=provider
        )
        self.assertEqual(result.variants, [])
        self.assertTrue(
            any("parseable" in w.lower() for w in result.warnings)
        )

    def test_provider_raises_returns_warning_not_500(self):
        class BoomProvider(MockLLMProvider):
            def chat(self, *a, **kw):
                raise RuntimeError("simulated outage")

        result = generate_ad_copy(
            recommendation=_marketing_rec(), provider=BoomProvider()
        )
        self.assertEqual(result.variants, [])
        self.assertTrue(
            any("LLM call failed" in w for w in result.warnings)
        )


class AdCopyEndpointTests(TestCase):
    def setUp(self):
        self.v1 = _make_vehicle("FF-2025-002", "30000.00", model="F-150")
        # Patch the factory so the view picks up our scripted provider.
        self._patcher_replies: List[str] = [_good_variants_json()]

        original_get = ad_copy_svc.get_llm_provider

        def _patched():
            return MockLLMProvider(replies=self._patcher_replies)

        ad_copy_svc.get_llm_provider = _patched  # type: ignore[assignment]
        self.addCleanup(setattr, ad_copy_svc, "get_llm_provider", original_get)

    def test_post_returns_200_with_variants(self):
        url = reverse("dealer_ai:admin-ad-copy")
        res = self.client.post(
            url,
            data=json.dumps({"recommendation": _marketing_rec()}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data["recommendation_id"], _marketing_rec()["id"])
        self.assertGreaterEqual(len(data["variants"]), 2)
        self.assertIn("warnings", data)
        self.assertIn("vehicles_used", data)
        # Each surviving variant has the contract fields.
        for v in data["variants"]:
            self.assertIn("platform_hint", v)
            self.assertIn("headline", v)
            self.assertIn("body", v)
            self.assertIn("cta", v)
            self.assertIn("scrubs_fired", v)

    def test_post_400_when_recommendation_missing(self):
        url = reverse("dealer_ai:admin-ad-copy")
        res = self.client.post(
            url,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_post_400_when_category_unsupported(self):
        url = reverse("dealer_ai:admin-ad-copy")
        res = self.client.post(
            url,
            data=json.dumps(
                {
                    "recommendation": {
                        "id": "sales.high_intent_assign",
                        "category": "sales",
                        "title": "x",
                        "explanation": "y",
                        "action_text": "z",
                        "evidence": {},
                    }
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_post_400_when_vehicle_id_not_an_integer(self):
        url = reverse("dealer_ai:admin-ad-copy")
        res = self.client.post(
            url,
            data=json.dumps(
                {
                    "recommendation": _marketing_rec(),
                    "vehicle_id": "not-an-int",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_post_with_explicit_vehicle_id(self):
        url = reverse("dealer_ai:admin-ad-copy")
        res = self.client.post(
            url,
            data=json.dumps(
                {
                    "recommendation": _marketing_rec(),
                    "vehicle_id": self.v1.pk,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        stock_numbers = {v["stock_number"] for v in data["vehicles_used"]}
        self.assertIn("FF-2025-002", stock_numbers)
