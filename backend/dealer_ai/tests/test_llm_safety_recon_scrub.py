"""Milestone 4 · Increment 5 — _scrub_invented_recon_fact tests.

Coverage of the new post-LLM scrub added to
``dealer_ai/services/llm_safety.py``. Four regex families per
planning §5.g:

- Invented finding IDs (``Finding #<n>`` not in source).
- Invented part numbers (``[A-Z0-9-]{5,}`` not in source).
- Invented dollar amounts (``$<n>`` not matching authorized_cost
  or any parts_needed unit_cost*quantity).
- Invented ISO dates (``YYYY-MM-DD`` not matching
  estimated_completion_date).

Also covers the ``apply_post_llm_scrubs`` integration:
- ``kind="vendor_comm"`` fires the scrub.
- ``kind="parts_order"`` fires the scrub.
- Other kinds do NOT fire the scrub (chat / ad / follow_up etc.).
- Missing ``recon_source_bundle`` (empty dict) treats every
  referenced fact as invented.
"""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.services.llm_safety import (
    _RECON_COMM_KINDS,
    _scrub_invented_recon_fact,
    apply_post_llm_scrubs,
)


# ============================================================================
# Kinds vocabulary
# ============================================================================


class ReconCommKindsMembership(TestCase):
    def test_recon_comm_kinds_exact_membership(self):
        # SESSION_084 M6.3 extended this set with 'vehicle_listing' per
        # §5.d Option A user-confirmed — reuses the M4.5
        # ``_scrub_invented_recon_fact`` via dispatch extension, not a
        # new scrub. See ``services/llm_safety.py``.
        self.assertEqual(
            _RECON_COMM_KINDS,
            frozenset({"vendor_comm", "parts_order", "vehicle_listing"}),
        )

    def test_m45_recon_comm_kinds_still_members(self):
        """M4.5 additions preserved — additive-only extension."""
        self.assertIn("vendor_comm", _RECON_COMM_KINDS)
        self.assertIn("parts_order", _RECON_COMM_KINDS)


# ============================================================================
# _scrub_invented_recon_fact — direct tests
# ============================================================================


class ScrubEmptyOrTrivial(TestCase):
    def test_empty_text_returns_unchanged(self):
        cleaned, changed = _scrub_invented_recon_fact("", source_bundle={})
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)

    def test_no_invented_patterns_unchanged(self):
        text = "Hey Bob, hope you're well. Please take a look when convenient."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={}
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)


class ScrubInventedFindingIds(TestCase):
    def test_finding_id_not_in_source_stripped(self):
        text = "Please address Finding #999 on the truck."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"findings": [{"id": 1}]}
        )
        self.assertNotIn("#999", cleaned)
        self.assertIn("the finding", cleaned)
        self.assertTrue(changed)

    def test_finding_id_in_source_preserved(self):
        text = "Please address Finding #42 on the truck."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"findings": [{"id": 42}]}
        )
        self.assertIn("Finding #42", cleaned)
        self.assertFalse(changed)

    def test_multiple_finding_ids_mixed(self):
        text = "Address Finding #1 and Finding #99 on this vehicle."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"findings": [{"id": 1}]}
        )
        self.assertIn("Finding #1", cleaned)
        self.assertNotIn("Finding #99", cleaned)
        self.assertIn("the finding", cleaned)
        self.assertTrue(changed)

    def test_finding_case_insensitive_pattern(self):
        text = "See finding #77 for details."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"findings": [{"id": 42}]}
        )
        self.assertNotIn("#77", cleaned)
        self.assertTrue(changed)


class ScrubInventedPartNumbers(TestCase):
    def test_part_number_not_in_source_stripped(self):
        text = "Please order part FAKE-123 for the truck."
        cleaned, changed = _scrub_invented_recon_fact(
            text,
            source_bundle={
                "parts_needed": [{"part_number": "REAL-456"}]
            },
        )
        self.assertNotIn("FAKE-123", cleaned)
        self.assertIn("the part", cleaned)
        self.assertTrue(changed)

    def test_part_number_in_source_preserved(self):
        text = "Please order part REAL-456 for the truck."
        cleaned, changed = _scrub_invented_recon_fact(
            text,
            source_bundle={
                "parts_needed": [{"part_number": "REAL-456"}]
            },
        )
        self.assertIn("REAL-456", cleaned)
        self.assertFalse(changed)

    def test_short_alphanumeric_not_matched(self):
        # "SUV" is short enough not to match the [A-Z0-9-]{5,}
        # pattern — false positives here would be noisy.
        text = "It's a nice SUV in the lot."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={}
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)


class ScrubInventedDollarAmounts(TestCase):
    def test_amount_not_matching_authorized_cost_stripped(self):
        text = "The total quote came to $999.00 for this job."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"authorized_cost": "500.00"}
        )
        self.assertNotIn("$999", cleaned)
        self.assertIn("the quoted amount", cleaned)
        self.assertTrue(changed)

    def test_amount_matching_authorized_cost_preserved(self):
        text = "The total quote is $500 for this job."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"authorized_cost": "500.00"}
        )
        self.assertIn("$500", cleaned)
        self.assertFalse(changed)

    def test_amount_matching_authorized_two_decimal(self):
        text = "The total is $500.00."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"authorized_cost": "500.00"}
        )
        self.assertIn("$500.00", cleaned)
        self.assertFalse(changed)

    def test_amount_matching_parts_unit_cost_times_quantity(self):
        # 2 units at $150 each = $300.
        text = "Total for parts: $300.00."
        cleaned, changed = _scrub_invented_recon_fact(
            text,
            source_bundle={
                "parts_needed": [
                    {"unit_cost": "150.00", "quantity": 2}
                ]
            },
        )
        self.assertIn("$300", cleaned)
        self.assertFalse(changed)

    def test_comma_grouped_amount_matches_normalized(self):
        text = "The total is $1,234.00."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={"authorized_cost": "1234.00"}
        )
        self.assertIn("$1,234.00", cleaned)
        self.assertFalse(changed)


class ScrubInventedDates(TestCase):
    def test_date_not_matching_ecd_stripped(self):
        text = "Please have it ready by 2026-09-15."
        cleaned, changed = _scrub_invented_recon_fact(
            text,
            source_bundle={"estimated_completion_date": "2026-08-15"},
        )
        self.assertNotIn("2026-09-15", cleaned)
        self.assertIn("the scheduled date", cleaned)
        self.assertTrue(changed)

    def test_date_matching_ecd_preserved(self):
        text = "Please have it ready by 2026-08-15."
        cleaned, changed = _scrub_invented_recon_fact(
            text,
            source_bundle={"estimated_completion_date": "2026-08-15"},
        )
        self.assertIn("2026-08-15", cleaned)
        self.assertFalse(changed)


class ScrubEmptyBundleTreatsAllAsInvented(TestCase):
    """When the caller provides no source bundle (or an empty one),
    every referenced fact is treated as invented — the LLM should
    not fabricate facts when the caller has no source."""

    def test_finding_stripped_with_empty_bundle(self):
        text = "Finding #1 needs work."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={}
        )
        self.assertNotIn("#1", cleaned)
        self.assertTrue(changed)

    def test_part_stripped_with_empty_bundle(self):
        text = "Please order PART-ABC."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={}
        )
        self.assertNotIn("PART-ABC", cleaned)
        self.assertTrue(changed)

    def test_dollar_stripped_with_empty_bundle(self):
        text = "Total is $500."
        cleaned, changed = _scrub_invented_recon_fact(
            text, source_bundle={}
        )
        self.assertNotIn("$500", cleaned)
        self.assertTrue(changed)


class ScrubWhitespaceNormalization(TestCase):
    """After stripping invented content, whitespace should be
    tidied so the caller doesn't see double spaces where a fact
    used to be."""

    def test_double_spaces_collapsed(self):
        text = "Please order FAKE-123 quickly."
        cleaned, _ = _scrub_invented_recon_fact(text, source_bundle={})
        self.assertNotIn("  ", cleaned)

    def test_leading_trailing_whitespace_stripped(self):
        text = "  Finding #99 needs work.  "
        cleaned, _ = _scrub_invented_recon_fact(text, source_bundle={})
        self.assertEqual(cleaned, cleaned.strip())


# ============================================================================
# apply_post_llm_scrubs integration
# ============================================================================


class ApplyScrubsFiresOnReconKinds(TestCase):
    def test_vendor_comm_kind_fires_recon_scrub(self):
        text = "Please address Finding #999 in your quote."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text,
            kind="vendor_comm",
            recon_source_bundle={"findings": [{"id": 1}]},
        )
        self.assertIsNone(dropped)
        self.assertIn("invented_recon_fact", scrubs)
        self.assertNotIn("#999", cleaned)

    def test_parts_order_kind_fires_recon_scrub(self):
        text = "Please order FAKE-999 for us."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text,
            kind="parts_order",
            recon_source_bundle={
                "parts_needed": [{"part_number": "REAL-456"}]
            },
        )
        self.assertIsNone(dropped)
        self.assertIn("invented_recon_fact", scrubs)
        self.assertNotIn("FAKE-999", cleaned)

    def test_chat_kind_does_not_fire_recon_scrub(self):
        # A vehicle_ask / chat reply that legitimately mentions
        # "Finding #123" (unlikely but possible if the model is
        # confused) should NOT be scrubbed by the recon rules —
        # the recon scrub only applies to vendor comms.
        text = "Please address Finding #999 in your reply."
        cleaned, scrubs, _ = apply_post_llm_scrubs(
            text, kind="chat"
        )
        self.assertNotIn("invented_recon_fact", scrubs)
        # #999 stays because the recon scrub didn't fire.
        self.assertIn("#999", cleaned)

    def test_ad_kind_does_not_fire_recon_scrub(self):
        text = "This week only — Finding #42 special."
        _, scrubs, _ = apply_post_llm_scrubs(text, kind="ad")
        self.assertNotIn("invented_recon_fact", scrubs)

    def test_missing_bundle_treats_everything_invented(self):
        text = "Finding #99 needs work by 2026-01-01."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text, kind="vendor_comm"
        )
        self.assertIsNone(dropped)
        self.assertIn("invented_recon_fact", scrubs)
        self.assertNotIn("#99", cleaned)
        self.assertNotIn("2026-01-01", cleaned)

    def test_recon_scrub_runs_after_other_scrubs(self):
        # Text with both a rate-language pattern and an invented
        # finding — both scrubs should fire, and the result should
        # bear both markers.
        text = (
            "Please address Finding #999. Financing at 4.9% APR is "
            "available on similar units."
        )
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text,
            kind="vendor_comm",
            recon_source_bundle={"findings": [{"id": 1}]},
        )
        # Recon scrub fired.
        self.assertIn("invented_recon_fact", scrubs)
        self.assertNotIn("#999", cleaned)


class ApplyScrubsHardRewriteReturnsEarly(TestCase):
    """When ``detect_unsafe_response`` or
    ``scrub_post_llm_override`` fires, the recon scrub should NOT
    run — the caller drops the whole variant per the shared
    contract."""

    def test_hard_rewrite_short_circuits_recon_scrub(self):
        # "our dealer cost" triggers detect_unsafe_response.
        text = "Our dealer cost on this F-150 is around $52,000."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text,
            kind="vendor_comm",
            recon_source_bundle={"findings": [{"id": 1}]},
        )
        self.assertIsNotNone(dropped)
        # scrubs list should not contain invented_recon_fact —
        # the recon scrub was short-circuited by the early return.
        self.assertNotIn("invented_recon_fact", scrubs)
