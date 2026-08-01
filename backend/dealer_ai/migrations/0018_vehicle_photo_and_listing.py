"""Milestone 6 · Increment 1 (SESSION_082) — VehiclePhoto + VehicleListing persistence.

Creates two new models — :class:`dealer_ai.models.VehiclePhoto` and
:class:`dealer_ai.models.VehicleListing` — per
``MILESTONE_6_PLANNING.md`` §1.1 + §1.2 + §5.a Option A
(user-confirmed at SESSION_082 open).

**Pure additive migration.** Unlike ``0017`` (which bootstrapped a
``VehicleStage`` + ``VehicleStageEvent`` row for every existing
Vehicle), M6.1 has no existing rows to seed: photos and listings do
not exist until the M6.2 / M6.3 services author them. The forward
migration only issues ``CreateModel`` operations; the reverse drops
the tables.

**No data migration.** Bootstrapping empty photo galleries or empty
listing drafts for every existing Vehicle would be dishonest —
neither service exists yet, and the M6.4 rules that read these tables
correctly return "no photos yet" / "no listing yet" for missing rows.

**No M1–M5 substrate touched.** Every prior model, index, constraint,
service, permission, safety-stack scrub, endpoint, and frontend
behavior unchanged.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0017_vehicle_lifecycle_persistence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VehicleListing",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("approved", "Approved"),
                            ("published", "Published"),
                            ("unpublished", "Unpublished"),
                        ],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("title", models.CharField(blank=True, default="", max_length=255)),
                ("body", models.TextField(blank=True, default="")),
                ("source_provenance", models.JSONField(blank=True, default=dict)),
                ("drafted_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("unpublished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "unpublished_reason",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vehicle_listings",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "drafted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "published_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "unpublished_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "vehicle",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="listing",
                        to="dealer_ai.vehicle",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vehicle listing",
                "verbose_name_plural": "Vehicle listings",
                "ordering": ("-updated_at",),
            },
        ),
        migrations.CreateModel(
            name="VehiclePhoto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("storage_key", models.CharField(max_length=512, unique=True)),
                (
                    "content_type",
                    models.CharField(
                        choices=[
                            ("image/jpeg", "JPEG"),
                            ("image/png", "PNG"),
                            ("image/webp", "WebP"),
                        ],
                        max_length=32,
                    ),
                ),
                ("width_px", models.PositiveIntegerField()),
                ("height_px", models.PositiveIntegerField()),
                ("sort_order", models.IntegerField(default=0)),
                ("is_primary", models.BooleanField(default=False)),
                ("caption", models.CharField(blank=True, default="", max_length=255)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("marked_deleted_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dealership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vehicle_photos",
                        to="dealer_ai.dealership",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="dealer_ai.vehicle",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vehicle photo",
                "verbose_name_plural": "Vehicle photos",
                "ordering": ("sort_order", "uploaded_at"),
            },
        ),
    ]
