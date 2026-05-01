"""python manage.py seed_phase4_demo [--reset]

Manager Phase 4 demo seed — adds 5 fictional dealership salespeople and
assigns roughly half of the existing demo leads to them so the new pipeline
avatar badges, the LeadDetailModal assignment dropdown, and the per-advisor
workspace pages all have visible content on first load.

Idempotent and additive — re-running without ``--reset`` skips advisors that
already exist (matched by slug). The ``--reset`` flag wipes the seeded
salespeople first and clears their assignments (preserving every other
field on the leads). Existing leads are *not* deleted by either path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import StringIO
from typing import List

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dealer_ai.models import CustomerLead, Salesperson


@dataclass
class AdvisorSpec:
    slug: str
    name: str
    title: str
    email: str
    phone: str
    photo_url: str
    bio: str
    specialties: List[str] = field(default_factory=list)


_ADVISORS: List[AdvisorSpec] = [
    AdvisorSpec(
        slug="maria-cortez",
        name="Maria Cortez",
        title="Senior Truck Specialist",
        email="maria.cortez@freedomford.example",
        phone="(405) 555-1010",
        photo_url=(
            "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=400"
        ),
        bio=(
            "Eight years on the F-150 line. Helps customers match payload, "
            "tow rating, and budget without the runaround."
        ),
        specialties=["F-150", "Super Duty", "Towing", "Fleet"],
    ),
    AdvisorSpec(
        slug="dave-okafor",
        name="Dave Okafor",
        title="New-Vehicle Advisor",
        email="dave.okafor@freedomford.example",
        phone="(405) 555-1020",
        photo_url=(
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400"
        ),
        bio=(
            "Bronco and Mustang enthusiast. Walks customers through new "
            "models, trims, and EV options without the high-pressure pitch."
        ),
        specialties=["Bronco", "Mustang", "Mustang Mach-E", "EVs"],
    ),
    AdvisorSpec(
        slug="linda-park",
        name="Linda Park",
        title="Family + Used Specialist",
        email="linda.park@freedomford.example",
        phone="(405) 555-1030",
        photo_url=(
            "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=400"
        ),
        bio=(
            "Knows the used inventory inside-out. Specializes in family "
            "SUVs and helping first-time-buyer parents find safe, "
            "reliable rides."
        ),
        specialties=["Explorer", "Edge", "Used SUVs", "Family vehicles"],
    ),
    AdvisorSpec(
        slug="jordan-rivera",
        name="Jordan Rivera",
        title="Finance + First-Time Buyer",
        email="jordan.rivera@freedomford.example",
        phone="(405) 555-1040",
        photo_url=(
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400"
        ),
        bio=(
            "Built a career around helping people with fair credit get "
            "into the right vehicle. No drama, no surprises."
        ),
        specialties=[
            "Maverick",
            "Financing options",
            "Fair-credit programs",
            "First-time buyers",
        ],
    ),
    AdvisorSpec(
        slug="sam-bell",
        name="Sam Bell",
        title="Customer Care Lead",
        email="sam.bell@freedomford.example",
        phone="(405) 555-1050",
        photo_url=(
            "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=400"
        ),
        bio=(
            "Handles the overflow queue and keeps customers from falling "
            "through the cracks. Concierge by training, advisor by craft."
        ),
        specialties=[
            "Concierge",
            "Trade-in coordination",
            "Cross-brand experience",
        ],
    ),
]


class Command(BaseCommand):
    help = (
        "Seed 5 demo salespeople and assign about half of the existing "
        "demo leads to them. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Wipe seeded salespeople and clear their lead assignments "
                "before re-seeding. Does NOT delete leads."
            ),
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        # Make sure leads exist — if not, run the Phase 3 seeder first so
        # the dashboard has something to show.
        if not CustomerLead.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No customer leads found — running seed_phase3_demo first."
                )
            )
            call_command("seed_phase3_demo", stdout=StringIO())

        created, skipped = self._seed_advisors()
        assigned = self._auto_assign_leads()

        self.stdout.write(
            self.style.SUCCESS(
                f"Phase 4 seed: created {created} salesperson "
                f"profile(s), skipped {skipped} existing, assigned "
                f"{assigned} previously-unassigned lead(s)."
            )
        )
        self.stdout.write(
            "Open /dealer-ai-admin to see the assignment chips, then "
            "/dealer-ai-advisor/maria-cortez (or any other slug) for "
            "the workspace view."
        )

    def _reset(self) -> None:
        seeded_slugs = [a.slug for a in _ADVISORS]
        # Clear assignments first so we don't rely on SET_NULL ordering.
        cleared = CustomerLead.objects.filter(
            assigned_to__slug__in=seeded_slugs
        ).update(assigned_to=None, assigned_at=None)
        deleted = Salesperson.objects.filter(slug__in=seeded_slugs).count()
        Salesperson.objects.filter(slug__in=seeded_slugs).delete()
        self.stdout.write(
            self.style.WARNING(
                f"Phase 4 reset: removed {deleted} salesperson row(s), "
                f"cleared {cleared} lead assignment(s)."
            )
        )

    @transaction.atomic
    def _seed_advisors(self) -> tuple[int, int]:
        created = 0
        skipped = 0
        for spec in _ADVISORS:
            obj, was_created = Salesperson.objects.get_or_create(
                slug=spec.slug,
                defaults={
                    "name": spec.name,
                    "title": spec.title,
                    "email": spec.email,
                    "phone": spec.phone,
                    "photo_url": spec.photo_url,
                    "bio": spec.bio,
                    "specialties": spec.specialties,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1
        return created, skipped

    @transaction.atomic
    def _auto_assign_leads(self) -> int:
        """Round-robin assign about half of the unassigned leads to the
        seeded advisors so the demo workspaces aren't empty."""
        active = list(
            Salesperson.objects.filter(
                slug__in=[a.slug for a in _ADVISORS], is_active=True
            ).order_by("slug")
        )
        if not active:
            return 0

        unassigned = list(
            CustomerLead.objects.filter(assigned_to__isnull=True).order_by(
                "-created_at"
            )
        )
        if not unassigned:
            return 0

        # Assign every other unassigned lead so half are still available
        # for the manager to assign during the demo.
        target_leads = unassigned[::2]
        now = timezone.now()
        assigned_count = 0
        for idx, lead in enumerate(target_leads):
            advisor = active[idx % len(active)]
            CustomerLead.objects.filter(pk=lead.pk).update(
                assigned_to=advisor, assigned_at=now
            )
            assigned_count += 1
        return assigned_count
