"""python manage.py import_inventory --file path/to/file.csv [--dry-run]

Upserts vehicles by stock_number (or VIN as a fallback). Vehicles previously
imported from the same `source` that are absent from this run are marked
unavailable but never deleted. Demo seed data lives under a different source
(`demo_seed`) and is not affected by CSV imports.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from dealer_ai.services.inventory_import import import_csv


class Command(BaseCommand):
    help = "Import dealership inventory from a CSV export."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the CSV file (UTF-8). See docs for required columns.",
        )
        parser.add_argument(
            "--source",
            default=None,
            help="Logical source name (defaults to csv:<filename>). "
            "Vehicles are scoped per source for missing-availability marking.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without persisting any changes.",
        )
        parser.add_argument(
            "--no-mark-missing",
            action="store_true",
            help="Skip marking previously-imported vehicles as unavailable when "
            "they're absent from this run.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit the run summary as a single JSON object on stdout.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        try:
            summary = import_csv(
                path,
                source=options.get("source"),
                dry_run=options["dry_run"],
                mark_missing_unavailable=not options["no_mark_missing"],
            )
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Import failed: {exc}") from exc

        if options["json"]:
            self.stdout.write(json.dumps(summary.as_dict(), indent=2))
            return

        prefix = "[DRY-RUN] " if summary.dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Source: {summary.source}\n"
                f"  Created:            {summary.created}\n"
                f"  Updated:            {summary.updated}\n"
                f"  Unchanged:          {summary.unchanged}\n"
                f"  Marked unavailable: {summary.marked_unavailable}\n"
                f"  Invalid rows:       {len(summary.invalid_rows)}"
            )
        )
        for err in summary.invalid_rows:
            self.stdout.write(
                self.style.WARNING(
                    f"  · line {err.line} ({err.stock_number or '—'}): {err.reason}"
                )
            )
