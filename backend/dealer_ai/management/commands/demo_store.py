"""Milestone 18 · Increment 1 (SESSION_147) — demo-store management command.

Per MILESTONE_18_PLANNING.md §5.c Option A (user-confirmed at
SESSION_146 open, recorded in §0.a). One command with four
subcommands provides the operator entry point for demo-store
lifecycle:

- ``python manage.py demo_store create --slug <name> --archetype
  <name> [--display-name <name>]`` — creates a fresh demo dealership
  + runs the archetype builder.
- ``python manage.py demo_store reset --slug <name>`` — resets to
  canonical starting state (belt-and-suspenders guarded).
- ``python manage.py demo_store list`` — lists demo dealerships.
- ``python manage.py demo_store export_feedback --dealership <slug>
  [--since <YYYY-MM-DD>] [--out <path>]`` — CSV export of
  TesterFeedback rows.

The command is a thin CLI over :mod:`dealer_ai.services.demo_store` —
all logic lives in the service package.
"""

from __future__ import annotations

import csv
import datetime as dt
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError

from dealer_ai.models import (
    DEMO_ARCHETYPE_CHOICES,
    Dealership,
    TesterFeedback,
)
from dealer_ai.services.demo_store import (
    NonDemoResetError,
    create_demo_store,
    list_demo_stores,
    reset_demo_store,
)


_ARCHETYPE_CHOICES = [key for key, _ in DEMO_ARCHETYPE_CHOICES]


class Command(BaseCommand):
    help = "Create / reset / list demo dealerships and export tester feedback."

    def add_arguments(self, parser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        create = sub.add_parser("create", help="Create a fresh demo dealership.")
        create.add_argument("--slug", required=True)
        create.add_argument(
            "--archetype", required=True, choices=_ARCHETYPE_CHOICES
        )
        create.add_argument("--display-name", default=None)

        reset = sub.add_parser("reset", help="Reset a demo dealership.")
        reset.add_argument("--slug", required=True)

        sub.add_parser("list", help="List all demo dealerships.")

        export = sub.add_parser(
            "export_feedback",
            help="Export TesterFeedback rows for a demo dealership as CSV.",
        )
        export.add_argument("--dealership", required=True)
        export.add_argument(
            "--since",
            default=None,
            help="ISO date (YYYY-MM-DD) — only feedback at or after this date.",
        )
        export.add_argument(
            "--out",
            default=None,
            help="Output file path. Default: stdout.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        subcommand = options["subcommand"]
        if subcommand == "create":
            self._handle_create(options)
        elif subcommand == "reset":
            self._handle_reset(options)
        elif subcommand == "list":
            self._handle_list()
        elif subcommand == "export_feedback":
            self._handle_export_feedback(options)
        else:
            raise CommandError(f"Unknown subcommand {subcommand!r}.")

    # --- subcommand handlers --------------------------------------------

    def _handle_create(self, options: dict) -> None:
        slug = options["slug"]
        archetype = options["archetype"]
        display_name = options.get("display_name")
        try:
            dealership, summary = create_demo_store(
                slug=slug,
                archetype=archetype,
                name=display_name,
            )
        except IntegrityError as exc:
            raise CommandError(
                f"Cannot create demo store {slug!r} — slug already exists."
            ) from exc
        except NotImplementedError as exc:
            # Archetype stub at M18.1 — the ``create_demo_store``
            # atomic wraps the Dealership.create + builder.build in
            # one transaction. NotImplementedError inside build()
            # rolls back the whole thing, so the Dealership row is
            # NOT persisted at M18.1 when the stub fires. Surface a
            # clear message.
            raise CommandError(
                f"Archetype {archetype!r} builder is not yet "
                f"implemented at M18.1 — Dealership create rolled "
                f"back (see MILESTONE_18_PLANNING.md §7 for the "
                f"per-archetype increment schedule):\n  {exc}"
            ) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Created demo store {dealership.slug!r} (pk={dealership.pk}) "
            f"with archetype {archetype!r}."
        ))
        self.stdout.write(
            f"  Stock numbers seeded: {len(summary.seeded_stock_numbers)}"
        )
        self.stdout.write(
            f"  User accounts seeded: {len(summary.seeded_user_usernames)}"
        )
        self.stdout.write(
            f"  Scenario briefs available: {len(summary.seeded_scenario_slugs)}"
        )
        if summary.notes:
            self.stdout.write(f"  Notes: {summary.notes}")

    def _handle_reset(self, options: dict) -> None:
        slug = options["slug"]
        try:
            dealership = Dealership.objects.get(slug=slug)
        except Dealership.DoesNotExist as exc:
            raise CommandError(f"No dealership with slug {slug!r}.") from exc
        try:
            summary = reset_demo_store(dealership=dealership)
        except NonDemoResetError as exc:
            raise CommandError(str(exc)) from exc
        except NotImplementedError as exc:
            self.stdout.write(self.style.WARNING(
                f"Reset cleared child rows on {dealership.slug!r} but the "
                f"archetype {dealership.demo_archetype!r} builder is not yet "
                f"implemented at M18.1:\n  {exc}"
            ))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Reset demo store {dealership.slug!r} to canonical state."
        ))
        self.stdout.write(
            f"  Stock numbers seeded: {len(summary.seeded_stock_numbers)}"
        )
        self.stdout.write(
            f"  Scenario briefs available: {len(summary.seeded_scenario_slugs)}"
        )

    def _handle_list(self) -> None:
        stores = list_demo_stores()
        if not stores:
            self.stdout.write("No demo dealerships exist yet.")
            return
        self.stdout.write(f"Found {len(stores)} demo dealership(s):")
        for store in stores:
            self.stdout.write(
                f"  {store.slug!r} (pk={store.pk}, archetype="
                f"{store.demo_archetype!r}, created "
                f"{store.created_at.isoformat()})"
            )

    def _handle_export_feedback(self, options: dict) -> None:
        slug = options["dealership"]
        since_raw = options.get("since")
        out_path = options.get("out")
        try:
            dealership = Dealership.objects.get(slug=slug)
        except Dealership.DoesNotExist as exc:
            raise CommandError(f"No dealership with slug {slug!r}.") from exc

        qs = TesterFeedback.objects.filter(dealership=dealership)
        if since_raw:
            try:
                since_date = dt.date.fromisoformat(since_raw)
            except ValueError as exc:
                raise CommandError(
                    f"--since must be YYYY-MM-DD; got {since_raw!r}."
                ) from exc
            qs = qs.filter(created_at__date__gte=since_date)
        rows = list(qs.order_by("-created_at", "-id"))

        columns = [
            "id",
            "dealership_slug",
            "tester_name",
            "scenario_slug",
            "category",
            "note",
            "referenced_route",
            "created_at",
        ]

        if out_path:
            target = open(out_path, "w", newline="")
        else:
            # Route to ``self.stdout`` so ``call_command(..., stdout=...)``
            # in tests + operator scripts captures the CSV correctly.
            target = self.stdout
        try:
            writer = csv.DictWriter(target, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "id": row.pk,
                    "dealership_slug": dealership.slug,
                    "tester_name": row.tester_name,
                    "scenario_slug": row.scenario_slug,
                    "category": row.category,
                    "note": row.note,
                    "referenced_route": row.referenced_route,
                    "created_at": row.created_at.isoformat(),
                })
        finally:
            if out_path:
                target.close()

        if out_path:
            self.stdout.write(self.style.SUCCESS(
                f"Exported {len(rows)} feedback row(s) to {out_path}."
            ))
