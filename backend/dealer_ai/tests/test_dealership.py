"""Milestone 1 · Increment 1 — Dealership tenancy-root model.

The model is introduced in isolation ahead of the FK-carrier work in
subsequent increments (per docs/roadmap/MILESTONE_1_PLANNING.md §1.5).
These tests lock the model's shape so the FK additions in Increment 2
have a stable target and the resolver work in later increments has a
stable identifier field to query on.
"""

from __future__ import annotations

from django.db import IntegrityError
from django.test import TestCase

from dealer_ai.models import Dealership


class DealershipModel(TestCase):
    def test_round_trip(self):
        d = Dealership.objects.create(name="Copper Canyon Auto", slug="copper-canyon")
        fetched = Dealership.objects.get(slug="copper-canyon")
        self.assertEqual(fetched.pk, d.pk)
        self.assertEqual(fetched.name, "Copper Canyon Auto")

    def test_str_returns_name(self):
        d = Dealership.objects.create(name="Rivertown Motors", slug="rivertown")
        self.assertEqual(str(d), "Rivertown Motors")

    def test_slug_is_unique(self):
        Dealership.objects.create(name="First", slug="dup")
        with self.assertRaises(IntegrityError):
            Dealership.objects.create(name="Second", slug="dup")

    def test_default_ordering_is_by_name(self):
        Dealership.objects.create(name="Zeta", slug="zeta")
        Dealership.objects.create(name="Alpha", slug="alpha")
        Dealership.objects.create(name="Mu", slug="mu")
        names = list(Dealership.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Alpha", "Mu", "Zeta"])
