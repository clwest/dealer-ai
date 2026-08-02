"""Milestone 17 · Increment 1 (SESSION_145) — trial-balance materialization tests.

Mirror ``test_m133_trial_balance_service.py`` + ``test_m141_journal_entry_
list_endpoint.py`` shape. Covers:

- :func:`freeze_trial_balance` happy path (header + child rows).
- Zero-portfolio freeze (empty rows, balanced totals).
- ``DuplicateTrialBalanceSnapshotError`` on second freeze at same ``as_of``.
- Cross-tenant guard (isolation on read).
- Atomic partial-write rollback on child creation failure.
- Frozen row immutability against later COA rename + backdated entries.
- :func:`list_trial_balance_snapshots` pagination + tenancy isolation.
- :func:`get_trial_balance_snapshot` detail + cross-tenant 404.
- POST endpoint: 201 happy path, 400 missing/invalid as_of, 409 on
  duplicate, 403 on non-permitted role.
- GET list endpoint: pagination + zero-portfolio.
- GET detail endpoint: full frozen rows + 404 on cross-tenant.
- Tenancy carrier count 47 → 49 (>=).
- Permission class count == 8 (zero-drift streak extends to nine).
- Endpoint count 104 → 107 (>=).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest import mock

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_REVENUE,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    Dealership,
    GLAccount,
    TrialBalanceSnapshot,
    TrialBalanceSnapshotRow,
)
from dealer_ai.services.accounting import (
    DuplicateTrialBalanceSnapshotError,
    JournalLineInput,
    TrialBalanceSnapshotListPage,
    freeze_trial_balance,
    get_trial_balance_snapshot,
    list_trial_balance_snapshots,
    post_journal_entry,
)
from dealer_ai.services.tenancy import (
    _TENANT_CARRIER_MODEL_NAMES,
    get_default_dealership,
)

from ._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)


FREEZE = "dealer_ai:admin-trial-balance-snapshot-create"
LIST = "dealer_ai:admin-trial-balance-snapshot-list"
RETRIEVE = "dealer_ai:admin-trial-balance-snapshot-retrieve"


def _sm_client(
    dealership: Dealership | None = None,
    username: str = "m171-sm",
) -> APIClient:
    """Sales-manager APIClient scoped to a specific dealership."""
    user = make_user(username=username)
    make_membership(
        user,
        dealership or get_default_dealership(),
        ROLE_SALES_MANAGER,
    )
    return authenticated_client(user)


def _post_two_line(dealership, cash: GLAccount, revenue: GLAccount, amount: Decimal):
    """Post one balanced two-line entry — DR cash / CR revenue."""
    return post_journal_entry(
        dealership=dealership,
        description="M17.1 test posting",
        lines=[
            JournalLineInput(account=cash, debit=amount),
            JournalLineInput(account=revenue, credit=amount),
        ],
    )


def _test_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    cash = GLAccount.objects.create(
        dealership=dealership,
        code="M171-100000",
        name="Cash (M17.1 test)",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    revenue = GLAccount.objects.create(
        dealership=dealership,
        code="M171-400000",
        name="Revenue (M17.1 test)",
        account_type=GL_ACCOUNT_TYPE_REVENUE,
    )
    return cash, revenue


# ---------------------------------------------------------------------------
# freeze_trial_balance — happy path
# ---------------------------------------------------------------------------


class FreezeTrialBalanceHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m171-freeze-happy")
        self.cash, self.revenue = _test_accounts(self.dealership)

    def test_freeze_creates_header_and_child_rows(self) -> None:
        _post_two_line(
            self.dealership, self.cash, self.revenue, Decimal("500.00")
        )
        snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        self.assertIsInstance(snapshot, TrialBalanceSnapshot)
        self.assertEqual(snapshot.dealership_id, self.dealership.pk)
        rows = list(snapshot.rows.order_by("account_code"))
        self.assertEqual(len(rows), 2)
        codes = {r.account_code for r in rows}
        self.assertEqual(codes, {"M171-100000", "M171-400000"})

    def test_freeze_totals_match_computation(self) -> None:
        _post_two_line(
            self.dealership, self.cash, self.revenue, Decimal("750.00")
        )
        snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        self.assertEqual(snapshot.total_debits, Decimal("750.00"))
        self.assertEqual(snapshot.total_credits, Decimal("750.00"))
        self.assertTrue(snapshot.is_balanced)

    def test_freeze_captures_actor(self) -> None:
        user = make_user(username="m171-actor")
        snapshot = freeze_trial_balance(
            dealership=self.dealership,
            as_of=timezone.now(),
            actor=user,
        )
        self.assertEqual(snapshot.created_by_id, user.pk)

    def test_freeze_actor_is_optional(self) -> None:
        snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        self.assertIsNone(snapshot.created_by_id)

    def test_freeze_frozen_rows_carry_natural_balance(self) -> None:
        _post_two_line(
            self.dealership,
            self.cash,
            self.revenue,
            Decimal("1000.00"),
        )
        snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        rows_by_code = {r.account_code: r for r in snapshot.rows.all()}
        self.assertEqual(
            rows_by_code["M171-100000"].natural_balance,
            Decimal("1000.00"),
        )
        self.assertEqual(
            rows_by_code["M171-400000"].natural_balance,
            Decimal("1000.00"),
        )

    def test_freeze_uses_supplied_as_of(self) -> None:
        moment = timezone.now() - dt.timedelta(days=1)
        snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=moment
        )
        self.assertEqual(snapshot.as_of, moment)


class FreezeTrialBalanceZeroPortfolioTests(TestCase):
    def test_zero_portfolio_freeze_produces_empty_balanced_snapshot(
        self,
    ) -> None:
        dealership = make_dealership(slug="m171-zero")
        snapshot = freeze_trial_balance(
            dealership=dealership, as_of=timezone.now()
        )
        self.assertEqual(snapshot.total_debits, Decimal("0.00"))
        self.assertEqual(snapshot.total_credits, Decimal("0.00"))
        self.assertTrue(snapshot.is_balanced)
        self.assertEqual(snapshot.rows.count(), 0)


# ---------------------------------------------------------------------------
# freeze_trial_balance — guards
# ---------------------------------------------------------------------------


class FreezeTrialBalanceUniquenessTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m171-uniq")

    def test_duplicate_as_of_raises_domain_error(self) -> None:
        moment = timezone.now()
        freeze_trial_balance(
            dealership=self.dealership, as_of=moment
        )
        with self.assertRaises(DuplicateTrialBalanceSnapshotError):
            freeze_trial_balance(
                dealership=self.dealership, as_of=moment
            )

    def test_duplicate_error_message_names_dealer_and_moment(self) -> None:
        moment = timezone.now()
        freeze_trial_balance(
            dealership=self.dealership, as_of=moment
        )
        with self.assertRaises(DuplicateTrialBalanceSnapshotError) as ctx:
            freeze_trial_balance(
                dealership=self.dealership, as_of=moment
            )
        self.assertIn("m171-uniq", str(ctx.exception))
        self.assertIn(moment.isoformat(), str(ctx.exception))

    def test_different_dealerships_can_share_as_of(self) -> None:
        other = make_dealership(slug="m171-uniq-other")
        moment = timezone.now()
        freeze_trial_balance(dealership=self.dealership, as_of=moment)
        # Not a duplicate — different tenant.
        snap_other = freeze_trial_balance(
            dealership=other, as_of=moment
        )
        self.assertEqual(snap_other.dealership_id, other.pk)


class FreezeTrialBalanceAtomicityTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m171-atomic")
        self.cash, self.revenue = _test_accounts(self.dealership)

    def test_child_row_failure_rolls_back_header(self) -> None:
        _post_two_line(
            self.dealership,
            self.cash,
            self.revenue,
            Decimal("300.00"),
        )
        with mock.patch(
            "dealer_ai.services.accounting.trial_balance_close."
            "TrialBalanceSnapshotRow.objects.bulk_create",
            side_effect=RuntimeError("simulated child failure"),
        ):
            with self.assertRaises(RuntimeError):
                freeze_trial_balance(
                    dealership=self.dealership,
                    as_of=timezone.now(),
                )
        # Header should have rolled back — no snapshot rows exist.
        self.assertEqual(
            TrialBalanceSnapshot.objects.filter(
                dealership=self.dealership
            ).count(),
            0,
        )


# ---------------------------------------------------------------------------
# freeze_trial_balance — immutability (frozen rows survive change)
# ---------------------------------------------------------------------------


class FreezeTrialBalanceImmutabilityTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m171-immut")
        self.cash, self.revenue = _test_accounts(self.dealership)

    def test_frozen_rows_preserve_account_name_after_coa_rename(
        self,
    ) -> None:
        _post_two_line(
            self.dealership,
            self.cash,
            self.revenue,
            Decimal("200.00"),
        )
        snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        # Later: COA renamed.
        self.cash.name = "Cash (renamed post-freeze)"
        self.cash.save(update_fields=["name"])
        # Frozen row still carries the original name.
        row = snapshot.rows.get(account_code="M171-100000")
        self.assertEqual(row.account_name, "Cash (M17.1 test)")

    def test_backdated_entry_does_not_change_frozen_rows(self) -> None:
        _post_two_line(
            self.dealership,
            self.cash,
            self.revenue,
            Decimal("100.00"),
        )
        freeze_moment = timezone.now()
        snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=freeze_moment
        )
        original_debit = snapshot.rows.get(
            account_code="M171-100000"
        ).debit_total
        # Post an additional backdated entry (posted_at BEFORE
        # freeze_moment). This shifts the LIVE aggregate but must not
        # touch the FROZEN rows.
        backdated_moment = freeze_moment - dt.timedelta(hours=1)
        post_journal_entry(
            dealership=self.dealership,
            description="Backdated correction",
            posted_at=backdated_moment,
            lines=[
                JournalLineInput(
                    account=self.cash, debit=Decimal("50.00")
                ),
                JournalLineInput(
                    account=self.revenue, credit=Decimal("50.00")
                ),
            ],
        )
        # Reload snapshot row from DB — value must be unchanged.
        row = TrialBalanceSnapshotRow.objects.get(
            snapshot=snapshot, account_code="M171-100000"
        )
        self.assertEqual(row.debit_total, original_debit)


# ---------------------------------------------------------------------------
# list_trial_balance_snapshots
# ---------------------------------------------------------------------------


class ListTrialBalanceSnapshotsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m171-list")

    def test_zero_portfolio_returns_empty_page(self) -> None:
        page = list_trial_balance_snapshots(dealership=self.dealership)
        self.assertIsInstance(page, TrialBalanceSnapshotListPage)
        self.assertEqual(page.snapshots, ())
        self.assertEqual(page.total_count, 0)

    def test_returns_recent_snapshots_first(self) -> None:
        now = timezone.now()
        older = freeze_trial_balance(
            dealership=self.dealership,
            as_of=now - dt.timedelta(days=2),
        )
        newer = freeze_trial_balance(
            dealership=self.dealership,
            as_of=now - dt.timedelta(days=1),
        )
        page = list_trial_balance_snapshots(dealership=self.dealership)
        self.assertEqual(
            [s.pk for s in page.snapshots],
            [newer.pk, older.pk],
        )

    def test_pagination_bounds(self) -> None:
        now = timezone.now()
        for i in range(5):
            freeze_trial_balance(
                dealership=self.dealership,
                as_of=now - dt.timedelta(days=i + 1),
            )
        page = list_trial_balance_snapshots(
            dealership=self.dealership, page=1, page_size=2
        )
        self.assertEqual(len(page.snapshots), 2)
        self.assertEqual(page.total_count, 5)
        self.assertEqual(page.page_size, 2)

    def test_cross_tenant_isolation(self) -> None:
        other = make_dealership(slug="m171-list-other")
        freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        page = list_trial_balance_snapshots(dealership=other)
        self.assertEqual(page.total_count, 0)


# ---------------------------------------------------------------------------
# get_trial_balance_snapshot
# ---------------------------------------------------------------------------


class GetTrialBalanceSnapshotTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m171-detail")
        self.cash, self.revenue = _test_accounts(self.dealership)
        _post_two_line(
            self.dealership,
            self.cash,
            self.revenue,
            Decimal("400.00"),
        )
        self.snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )

    def test_returns_snapshot_in_tenant(self) -> None:
        result = get_trial_balance_snapshot(
            dealership=self.dealership,
            snapshot_id=self.snapshot.pk,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.pk, self.snapshot.pk)

    def test_returns_none_for_missing_pk(self) -> None:
        result = get_trial_balance_snapshot(
            dealership=self.dealership,
            snapshot_id=999_999_999,
        )
        self.assertIsNone(result)

    def test_returns_none_for_cross_tenant(self) -> None:
        other = make_dealership(slug="m171-detail-other")
        result = get_trial_balance_snapshot(
            dealership=other, snapshot_id=self.snapshot.pk
        )
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# POST /admin/accounting/trial-balance/snapshots/
# ---------------------------------------------------------------------------


class FreezeEndpointHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash, self.revenue = _test_accounts(self.dealership)
        self.client_ = _sm_client()

    def test_post_freezes_201_and_returns_projection(self) -> None:
        _post_two_line(
            self.dealership,
            self.cash,
            self.revenue,
            Decimal("222.00"),
        )
        moment = timezone.now()
        response = self.client_.post(
            reverse(FREEZE),
            {"as_of": moment.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["trial_balance_snapshot"]
        self.assertEqual(body["total_debits"], "222.00")
        self.assertEqual(body["total_credits"], "222.00")
        self.assertTrue(body["is_balanced"])
        self.assertEqual(len(body["rows"]), 2)

    def test_post_captures_authenticated_user(self) -> None:
        response = self.client_.post(
            reverse(FREEZE),
            {"as_of": timezone.now().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["trial_balance_snapshot"]
        self.assertIsNotNone(body["created_by_username"])


class FreezeEndpointGuardTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.client_ = _sm_client()

    def test_missing_as_of_returns_400(self) -> None:
        response = self.client_.post(
            reverse(FREEZE), {}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_as_of_returns_400(self) -> None:
        response = self.client_.post(
            reverse(FREEZE),
            {"as_of": "not-a-date"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_as_of_returns_409(self) -> None:
        moment = timezone.now()
        first = self.client_.post(
            reverse(FREEZE),
            {"as_of": moment.isoformat()},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.content)
        second = self.client_.post(
            reverse(FREEZE),
            {"as_of": moment.isoformat()},
            format="json",
        )
        self.assertEqual(second.status_code, 409, second.content)

    def test_non_permitted_role_returns_403(self) -> None:
        advisor = make_user(username="m171-advisor")
        make_membership(advisor, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(advisor)
        response = client.post(
            reverse(FREEZE),
            {"as_of": timezone.now().isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# GET /admin/accounting/trial-balance/snapshots/list/
# ---------------------------------------------------------------------------


class SnapshotListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.client_ = _sm_client()

    def test_zero_portfolio_returns_empty_list(self) -> None:
        response = self.client_.get(reverse(LIST))
        self.assertEqual(response.status_code, 200)
        body = response.json()["trial_balance_snapshots"]
        self.assertEqual(body["snapshots"], [])
        self.assertEqual(body["total_count"], 0)

    def test_returns_list_after_freezes(self) -> None:
        freeze_trial_balance(
            dealership=self.dealership,
            as_of=timezone.now() - dt.timedelta(days=1),
        )
        freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        response = self.client_.get(reverse(LIST))
        body = response.json()["trial_balance_snapshots"]
        self.assertEqual(body["total_count"], 2)
        self.assertEqual(len(body["snapshots"]), 2)

    def test_pagination_query_params_honoured(self) -> None:
        now = timezone.now()
        for i in range(4):
            freeze_trial_balance(
                dealership=self.dealership,
                as_of=now - dt.timedelta(days=i + 1),
            )
        response = self.client_.get(
            reverse(LIST), {"page": 2, "page_size": 2}
        )
        body = response.json()["trial_balance_snapshots"]
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["page_size"], 2)
        self.assertEqual(len(body["snapshots"]), 2)
        self.assertEqual(body["total_count"], 4)


# ---------------------------------------------------------------------------
# GET /admin/accounting/trial-balance/snapshots/<pk>/
# ---------------------------------------------------------------------------


class SnapshotRetrieveEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash, self.revenue = _test_accounts(self.dealership)
        _post_two_line(
            self.dealership,
            self.cash,
            self.revenue,
            Decimal("125.00"),
        )
        self.snapshot = freeze_trial_balance(
            dealership=self.dealership, as_of=timezone.now()
        )
        self.client_ = _sm_client()

    def test_get_returns_full_frozen_rows(self) -> None:
        response = self.client_.get(
            reverse(RETRIEVE, kwargs={"pk": self.snapshot.pk})
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["trial_balance_snapshot"]
        self.assertEqual(body["id"], self.snapshot.pk)
        self.assertEqual(len(body["rows"]), 2)
        # Money on the wire is Decimal-as-string.
        self.assertIsInstance(body["rows"][0]["debit_total"], str)

    def test_missing_pk_returns_404(self) -> None:
        response = self.client_.get(
            reverse(RETRIEVE, kwargs={"pk": 999_999_999})
        )
        self.assertEqual(response.status_code, 404)

    def test_cross_tenant_returns_404(self) -> None:
        other = make_dealership(slug="m171-retrieve-other")
        other_client = _sm_client(
            dealership=other, username="m171-retrieve-other-sm"
        )
        response = other_client.get(
            reverse(RETRIEVE, kwargs={"pk": self.snapshot.pk})
        )
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Tenancy carrier + permission-class + endpoint counts
# ---------------------------------------------------------------------------


class M171TenancyCarrierTests(TestCase):
    def test_snapshot_registered_as_tenancy_carrier(self) -> None:
        self.assertIn(
            "TrialBalanceSnapshot", _TENANT_CARRIER_MODEL_NAMES
        )

    def test_snapshot_row_registered_as_tenancy_carrier(self) -> None:
        self.assertIn(
            "TrialBalanceSnapshotRow", _TENANT_CARRIER_MODEL_NAMES
        )

    def test_carrier_count_at_least_forty_nine(self) -> None:
        # Growth-only list per M9-M16 lesson. `>=49` after M17.1 —
        # +2 for the two new snapshot models.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 49)


class M171PermissionClassZeroDriftTests(TestCase):
    def test_no_new_permission_class_at_m171(self) -> None:
        # Zero-drift streak extends to nine consecutive milestones
        # (M10 + M11 + M12 + M13 + M14 + M15 + M16 + M17). Exact
        # set equality per fixed-vocab lesson — a new permission
        # class at M17 would trip this.
        from dealer_ai import permissions

        permission_classes = {
            name
            for name in dir(permissions)
            if not name.startswith("_")
            and name != "IsAuthenticated"
            and isinstance(getattr(permissions, name), type)
            and issubclass(
                getattr(permissions, name),
                __import__(
                    "rest_framework.permissions",
                    fromlist=["BasePermission"],
                ).BasePermission,
            )
            and getattr(permissions, name).__module__
            == "dealer_ai.permissions"
        }
        self.assertEqual(
            permission_classes,
            {
                "IsAdvisorForSlug",
                "IsDealerOwnerForAdvisorSlug",
                "IsSalesManagerOrOwnerAtActiveDealership",
                "IsReconManagerSalesManagerOrOwnerAtActiveDealership",
                "IsDealerOwnerAtActiveDealership",
                "IsFinanceManagerOrOwnerAtActiveDealership",
                "ReadOnly",
            },
        )



class M171EndpointCountTests(TestCase):
    def test_endpoint_count_at_least_one_hundred_seven(self) -> None:
        # Growth-only list per lesson. `>=107` after M17.1 — +3 for
        # the freeze / list / detail endpoints.
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern")
            and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 107)
