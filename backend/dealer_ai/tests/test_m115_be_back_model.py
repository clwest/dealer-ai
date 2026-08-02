"""Milestone 11 · Increment 5 (SESSION_118) — BeBack model tests.

Locks the schema surface of :class:`dealer_ai.models.BeBack` per
``MILESTONE_11_PLANNING.md`` §1.5 + §5.g Options A / A.
"""

from __future__ import annotations

import datetime as dt

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BE_BACK_REASON_BRING_CO_SIGNER,
    BE_BACK_REASON_BRING_TRADE_IN,
    BE_BACK_REASON_CHOICES,
    BE_BACK_REASON_OTHER,
    BE_BACK_REASON_TEST_DRIVE,
    BE_BACK_STATE_CHOICES,
    BE_BACK_STATE_NO_SHOW,
    BE_BACK_STATE_PROMISED,
    BE_BACK_STATE_RETURNED,
    BeBack,
    CustomerLead,
    Dealership,
)


class BeBackDefaultsAndOrderingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bb-def", name="BB Defaults"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Bev Backman"
        )

    def test_defaults(self) -> None:
        bb = BeBack.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now() + dt.timedelta(days=1),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
        )
        self.assertEqual(bb.state, BE_BACK_STATE_PROMISED)
        self.assertIsNone(bb.actual_return_at)
        self.assertEqual(bb.notes, "")

    def test_ordering_is_reverse_promised_at(self) -> None:
        earlier = BeBack.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now(),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
        )
        later = BeBack.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now() + dt.timedelta(days=1),
            promised_reason=BE_BACK_REASON_BRING_CO_SIGNER,
        )
        self.assertEqual(list(BeBack.objects.all()), [later, earlier])


class BeBackCrossTenantAndCascadeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bb-clean", name="BB Clean"
        )
        self.other = Dealership.objects.create(
            slug="bb-clean-other", name="BB Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local"
        )
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )

    def test_clean_rejects_cross_tenant_lead(self) -> None:
        bb = BeBack(
            dealership=self.dealership,
            lead=self.cross_lead,
            promised_at=timezone.now(),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
        )
        with self.assertRaises(ValidationError) as ctx:
            bb.clean()
        self.assertIn("lead", ctx.exception.message_dict)

    def test_lead_delete_cascades(self) -> None:
        bb = BeBack.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now(),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
        )
        self.lead.delete()
        self.assertFalse(BeBack.objects.filter(pk=bb.pk).exists())


class BeBackVocabTests(TestCase):
    def test_reason_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in BE_BACK_REASON_CHOICES}
        self.assertEqual(
            vocab,
            {
                BE_BACK_REASON_TEST_DRIVE,
                BE_BACK_REASON_BRING_CO_SIGNER,
                BE_BACK_REASON_BRING_TRADE_IN,
                BE_BACK_REASON_OTHER,
            },
        )

    def test_state_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in BE_BACK_STATE_CHOICES}
        self.assertEqual(
            vocab,
            {
                BE_BACK_STATE_PROMISED,
                BE_BACK_STATE_RETURNED,
                BE_BACK_STATE_NO_SHOW,
            },
        )
