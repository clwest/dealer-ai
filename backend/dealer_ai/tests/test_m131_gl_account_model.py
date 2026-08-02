"""Milestone 13 · Increment 1 (SESSION_129) — GLAccount model tests."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EXPENSE,
    GL_ACCOUNT_TYPE_REVENUE,
    Dealership,
    GLAccount,
)
from dealer_ai.services.tenancy import get_default_dealership


class GLAccountModelTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()

    def test_create_gl_account(self) -> None:
        account = GLAccount.objects.create(
            dealership=self.dealership,
            code="150000",
            name="Test Suspense",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        self.assertEqual(account.code, "150000")
        self.assertTrue(account.is_active)
        self.assertIsNotNone(account.created_at)
        self.assertIsNotNone(account.updated_at)

    def test_code_is_unique_per_dealership(self) -> None:
        GLAccount.objects.create(
            dealership=self.dealership,
            code="199999",
            name="First",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GLAccount.objects.create(
                    dealership=self.dealership,
                    code="199999",
                    name="Duplicate",
                    account_type=GL_ACCOUNT_TYPE_ASSET,
                )

    def test_code_can_repeat_across_dealerships(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-m131a", name="Other"
        )
        GLAccount.objects.create(
            dealership=self.dealership,
            code="177777",
            name="Ours",
            account_type=GL_ACCOUNT_TYPE_REVENUE,
        )
        # Namespace is per-dealership — same code in a different tenant
        # must not conflict.
        other_account = GLAccount.objects.create(
            dealership=other,
            code="177777",
            name="Theirs",
            account_type=GL_ACCOUNT_TYPE_REVENUE,
        )
        self.assertEqual(other_account.name, "Theirs")

    def test_str_shows_code_name_and_type(self) -> None:
        account = GLAccount.objects.create(
            dealership=self.dealership,
            code="811100",
            name="Rent",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        )
        rendered = str(account)
        self.assertIn("811100", rendered)
        self.assertIn("Rent", rendered)
        self.assertIn("expense", rendered)

    def test_invalid_account_type_rejected_by_full_clean(self) -> None:
        account = GLAccount(
            dealership=self.dealership,
            code="123400",
            name="Bogus",
            account_type="not_a_real_type",
        )
        with self.assertRaises(ValidationError):
            account.full_clean()
