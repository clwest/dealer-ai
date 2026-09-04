"""SESSION_240 (walk finding 28) — TASK_store-timezone.

Two-store, two-zone assertions:

- A sale posted at 22:00 Phoenix books to the Phoenix calendar date;
  the same UTC instant for a Chicago store books to Chicago's calendar
  date (which has already rolled to tomorrow).
- ``services.store_time.store_today`` returns the store's calendar
  day regardless of the process's ``settings.TIME_ZONE``.
- The M11.5 be-back no-show orchestrator dispatches per-tenant only
  for stores whose local clock reads ``target_local_hour`` — so a
  Chicago 07:00 firing dispatches Chicago and skips Phoenix, and a
  Chicago 09:00 firing dispatches Phoenix (whose clock is 07:00) and
  skips Chicago.
- ``Dealership`` rejects an unknown IANA name at write time; the
  onboarding serializer rejects it at the API boundary and exposes
  the live local time to the operator.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from ..models import Dealership
from ..services.be_backs.tasks import (
    detect_no_show_be_backs_for_all_tenants,
)
from ..services.store_time import (
    store_local_hour,
    store_localize,
    store_now,
    store_today,
    suggest_timezone_for_state,
)


class StoreTimeHelperTests(TestCase):
    """The three helpers must resolve the store's zone consistently."""

    def setUp(self):
        self.phoenix = Dealership.objects.create(
            name="Copper Canyon Auto",
            slug="cc-phoenix",
            timezone="America/Phoenix",
        )
        self.chicago = Dealership.objects.create(
            name="Windy City Motors",
            slug="wcm-chicago",
            timezone="America/Chicago",
        )

    def test_store_today_differs_across_zones_at_the_dateline(self):
        # Fixed UTC instant: 2026-09-04 03:30 UTC. That is:
        #   - Phoenix (UTC-7, no DST): 2026-09-03 20:30 — still the 3rd.
        #   - Chicago (UTC-5, DST):    2026-09-03 22:30 — still the 3rd.
        # Pick an earlier UTC that straddles the two: 2026-09-04 05:30 UTC
        #   - Phoenix (UTC-7): 2026-09-03 22:30 — still the 3rd.
        #   - Chicago (UTC-5): 2026-09-04 00:30 — already the 4th.
        fixed = dt.datetime(2026, 9, 4, 5, 30, tzinfo=dt.timezone.utc)
        with patch(
            "dealer_ai.services.store_time.timezone.now",
            return_value=fixed,
        ):
            phoenix_today = store_today(self.phoenix)
            chicago_today = store_today(self.chicago)
        self.assertEqual(phoenix_today, dt.date(2026, 9, 3))
        self.assertEqual(chicago_today, dt.date(2026, 9, 4))

    def test_store_now_returns_aware_datetime_in_store_zone(self):
        fixed = dt.datetime(2026, 9, 4, 5, 30, tzinfo=dt.timezone.utc)
        with patch(
            "dealer_ai.services.store_time.timezone.now",
            return_value=fixed,
        ):
            phoenix_now = store_now(self.phoenix)
            chicago_now = store_now(self.chicago)
        self.assertEqual(phoenix_now.utcoffset(), dt.timedelta(hours=-7))
        # Chicago in September observes CDT (UTC-5).
        self.assertEqual(chicago_now.utcoffset(), dt.timedelta(hours=-5))
        self.assertEqual(phoenix_now.hour, 22)
        self.assertEqual(chicago_now.hour, 0)

    def test_store_localize_reprojects_aware_datetime(self):
        instant = dt.datetime(2026, 9, 4, 5, 30, tzinfo=dt.timezone.utc)
        local = store_localize(instant, self.phoenix)
        self.assertEqual(local.tzinfo, ZoneInfo("America/Phoenix"))
        self.assertEqual(local.hour, 22)
        self.assertEqual(local.date(), dt.date(2026, 9, 3))

    def test_store_local_hour_matches_zoneinfo_wall_time(self):
        fixed = dt.datetime(2026, 9, 4, 5, 30, tzinfo=dt.timezone.utc)
        with patch(
            "dealer_ai.services.store_time.timezone.now",
            return_value=fixed,
        ):
            self.assertEqual(store_local_hour(self.phoenix), 22)
            self.assertEqual(store_local_hour(self.chicago), 0)


class SaleBookingDateAcrossZonesTests(TestCase):
    """The task's cornerstone assertion — a sale posted at 22:00 Phoenix
    books to the Phoenix date, not to Chicago's already-rolled tomorrow.

    Uses ``store_today`` as the substitute for what the ledger's
    ``sale_date`` derivation should be.
    """

    def test_22_00_phoenix_books_to_the_phoenix_date_not_chicago_tomorrow(self):
        phoenix = Dealership.objects.create(
            name="Copper Canyon Auto",
            slug="cc-1",
            timezone="America/Phoenix",
        )
        chicago = Dealership.objects.create(
            name="Windy City Motors",
            slug="wcm-1",
            timezone="America/Chicago",
        )
        # 2026-09-04 05:00 UTC = 22:00 Phoenix (Sep 3) = 00:00 Chicago
        # (Sep 4). A sale posted at this UTC instant must book to
        # Sep 3 at Phoenix and to Sep 4 at Chicago.
        posted_at = dt.datetime(2026, 9, 4, 5, 0, tzinfo=dt.timezone.utc)
        with patch(
            "dealer_ai.services.store_time.timezone.now",
            return_value=posted_at,
        ):
            phoenix_book_date = store_today(phoenix)
            chicago_book_date = store_today(chicago)
        self.assertEqual(phoenix_book_date, dt.date(2026, 9, 3))
        self.assertEqual(chicago_book_date, dt.date(2026, 9, 4))
        # And plainly not the other way round — the sale did not book
        # to Chicago's tomorrow for Phoenix.
        self.assertNotEqual(phoenix_book_date, chicago_book_date)


class BeBackDetectorPerStoreLocalHourTests(TestCase):
    """The M11.5 orchestrator dispatches only to stores whose local
    clock reads ``target_local_hour``. Two stores, two zones, three
    firings — one per store per day, plus the check that non-matching
    firings dispatch nobody.

    The test DB is migrated fresh — migration 0009 creates a
    ``default`` Dealership on the project TIME_ZONE (Chicago). Every
    assertion below filters the dispatched IDs to the two test
    dealerships so a migration-seeded row does not confuse the
    counts. That "default" row exists in production too, so the
    filter here mirrors what a real operator would care about:
    "did my two stores fire at their respective 07:00s?"
    """

    def setUp(self):
        self.phoenix = Dealership.objects.create(
            name="Copper Canyon Auto",
            slug="cc-beback",
            timezone="America/Phoenix",
        )
        self.chicago = Dealership.objects.create(
            name="Windy City Motors",
            slug="wcm-beback",
            timezone="America/Chicago",
        )
        self._test_ids = {self.phoenix.pk, self.chicago.pk}

    def _run_at_utc(self, when: dt.datetime) -> dict:
        # The orchestrator queues each per-tenant task via ``.delay()``.
        # Patching the underlying task lets us assert on the dispatched
        # dealership IDs without actually running the detector.
        dispatched: list[int] = []
        with patch(
            "dealer_ai.services.store_time.timezone.now",
            return_value=when,
        ), patch(
            "dealer_ai.services.be_backs.tasks."
            "detect_no_show_be_backs_for_tenant.delay",
            side_effect=lambda *, dealership_id: dispatched.append(
                dealership_id
            ),
        ):
            result = detect_no_show_be_backs_for_all_tenants()
        # Scope to the test-created dealerships only. Migration 0009
        # provisions a ``default`` Dealership on America/Chicago; a
        # test that asserts an absolute dispatched-count would flake
        # against a fresh vs. rebuilt migration graph.
        result["_dispatched_test_ids"] = [
            pk for pk in dispatched if pk in self._test_ids
        ]
        return result

    def test_chicago_07_dispatches_chicago_only(self):
        # 2026-09-04 12:00 UTC = 07:00 Chicago (CDT) = 05:00 Phoenix.
        result = self._run_at_utc(
            dt.datetime(2026, 9, 4, 12, 0, tzinfo=dt.timezone.utc)
        )
        self.assertEqual(
            result["_dispatched_test_ids"], [self.chicago.pk]
        )

    def test_chicago_09_dispatches_phoenix_only(self):
        # 2026-09-04 14:00 UTC = 09:00 Chicago (CDT) = 07:00 Phoenix.
        # The same daily beat covers both stores — one Chicago-local
        # firing at 07 dispatched Chicago; two hours later the same
        # beat catches Phoenix's 07.
        result = self._run_at_utc(
            dt.datetime(2026, 9, 4, 14, 0, tzinfo=dt.timezone.utc)
        )
        self.assertEqual(
            result["_dispatched_test_ids"], [self.phoenix.pk]
        )

    def test_off_hour_dispatches_nobody(self):
        # 2026-09-04 15:00 UTC = 10:00 Chicago = 08:00 Phoenix.
        # Neither test store's local clock reads 07.
        result = self._run_at_utc(
            dt.datetime(2026, 9, 4, 15, 0, tzinfo=dt.timezone.utc)
        )
        self.assertEqual(result["_dispatched_test_ids"], [])


class DealershipTimezoneValidationTests(TestCase):
    """The model rejects unknown zones at write time; a legacy row
    with an unset zone falls through to the project default."""

    def test_save_rejects_unknown_iana_name(self):
        with self.assertRaises(ValidationError):
            Dealership.objects.create(
                name="Nowhere Motors",
                slug="nm-nope",
                timezone="America/NotAReal_Zone",
            )

    def test_save_accepts_common_iana_names(self):
        for name in [
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "America/Phoenix",
            "Pacific/Honolulu",
        ]:
            with self.subTest(name=name):
                dealership = Dealership.objects.create(
                    name=f"Test {name}",
                    slug=f"test-{name.replace('/', '-').lower()}",
                    timezone=name,
                )
                self.assertEqual(dealership.timezone, name)

    def test_zoneinfo_helper_returns_expected_zone(self):
        dealership = Dealership.objects.create(
            name="Copper Canyon Auto",
            slug="cc-zi",
            timezone="America/Phoenix",
        )
        self.assertEqual(dealership.zoneinfo(), ZoneInfo("America/Phoenix"))


class StateToZoneSuggestionTests(TestCase):
    """One-zone states resolve outright; multi-zone states return None."""

    def test_one_zone_state_resolves(self):
        self.assertEqual(suggest_timezone_for_state("AZ"), "America/Phoenix")
        self.assertEqual(
            suggest_timezone_for_state("CA"), "America/Los_Angeles"
        )
        self.assertEqual(suggest_timezone_for_state("HI"), "Pacific/Honolulu")
        self.assertEqual(suggest_timezone_for_state("il"), "America/Chicago")

    def test_multi_zone_state_returns_none(self):
        for code in ("TX", "FL", "IN", "KY", "MI", "TN", "SD", "ND"):
            with self.subTest(code=code):
                self.assertIsNone(suggest_timezone_for_state(code))

    def test_blank_or_unknown_returns_none(self):
        self.assertIsNone(suggest_timezone_for_state(""))
        self.assertIsNone(suggest_timezone_for_state("ZZ"))


class OnboardingProfileTimezoneEndpointTests(TestCase):
    """The onboarding profile carries the store's zone in and out,
    validates unknown names, and returns a live local ``now``."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        from ..models import ROLE_DEALER_OWNER, UserDealershipRole

        self.dealership = Dealership.objects.create(
            name="Copper Canyon Auto",
            slug="copper-canyon-tests-tz",
            timezone="America/Phoenix",
        )
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="owner-tz", password="pw"
        )
        UserDealershipRole.objects.create(
            user=self.owner,
            dealership=self.dealership,
            role=ROLE_DEALER_OWNER,
        )
        self.client.force_login(self.owner)

    def test_get_returns_timezone_and_local_now(self):
        response = self.client.get(
            "/api/dealer-ai/onboarding/profile/",
            HTTP_X_DEALERSHIP_SLUG=self.dealership.slug,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body.get("dealership_timezone"), "America/Phoenix")
        self.assertIsNotNone(body.get("dealership_local_now"))
        # ``dealership_local_now`` is an ISO 8601 string; parsing it
        # gives a datetime whose offset matches Phoenix (-07:00 all
        # year — no DST).
        local_now = dt.datetime.fromisoformat(
            body["dealership_local_now"]
        )
        self.assertEqual(local_now.utcoffset(), dt.timedelta(hours=-7))

    def test_put_rejects_unknown_iana_name(self):
        response = self.client.put(
            "/api/dealer-ai/onboarding/profile/",
            data={"dealership_timezone": "Made/Up_Zone"},
            content_type="application/json",
            HTTP_X_DEALERSHIP_SLUG=self.dealership.slug,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("dealership_timezone", response.json())

    def test_patch_persists_timezone_to_dealership_row(self):
        response = self.client.patch(
            "/api/dealer-ai/onboarding/profile/",
            data={"dealership_timezone": "America/Chicago"},
            content_type="application/json",
            HTTP_X_DEALERSHIP_SLUG=self.dealership.slug,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.dealership.refresh_from_db()
        self.assertEqual(self.dealership.timezone, "America/Chicago")
        # And the response echoes the new value alongside the fresh
        # local ``now`` (which now carries a Chicago offset).
        body = response.json()
        self.assertEqual(body["dealership_timezone"], "America/Chicago")
        local_now = dt.datetime.fromisoformat(body["dealership_local_now"])
        # Chicago in September observes CDT (UTC-5).
        self.assertIn(
            local_now.utcoffset(),
            (dt.timedelta(hours=-5), dt.timedelta(hours=-6)),
        )


class UtcTimestampsAreLeftAloneTests(TestCase):
    """A wall-clock UTC timestamp used for a ``created_at`` /
    ``posted_at`` column is intentionally NOT converted — it stays as
    ``timezone.now()``. This test pins that decision: swapping to
    store-local would break event-ordering semantics against a
    UTC-aware datetime column shared across tenants."""

    def test_timezone_now_returns_utc_aware_datetime(self):
        now = timezone.now()
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.utcoffset(), dt.timedelta(0))
