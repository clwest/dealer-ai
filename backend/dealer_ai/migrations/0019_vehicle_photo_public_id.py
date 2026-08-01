"""Milestone 6 · Increment 2 (SESSION_083) — VehiclePhoto.public_id.

Adds a durable ``public_id`` UUIDField to :class:`dealer_ai.models.VehiclePhoto`
per ``MILESTONE_6_PLANNING.md`` §2 Option A (user-confirmed at
SESSION_083 open). Mirrors the M3.1
``ConditionFindingPhoto.public_id`` pattern so external references
(admin API URLs, log lines, cross-service attachments) bind to a
tenant-safe UUID rather than an enumerable integer PK.

**Three-step migration** for future-safety even though the M6.1
``0018`` migration shipped an empty ``dealer_ai_vehiclephoto`` table.
If future M6.2 upload testing / dev exploration lands photos before
this migration runs, the three-step pattern still applies unique
UUIDs to existing rows without violating the ``unique=True``
constraint:

1. ``AddField`` — nullable, non-unique. Every existing row (if any)
   gets ``public_id=NULL``.
2. ``RunPython`` — walk existing rows and assign a fresh
   :func:`uuid.uuid4` to each.
3. ``AlterField`` — enforce ``NOT NULL`` + ``unique=True``. New rows
   inserted after this migration get their default from
   :func:`uuid.uuid4`.

Empty-table path (all environments at SESSION_083 open): steps 1 and
3 are the only ones that touch the schema; step 2 is a no-op iterator.

Reverse:

- Step 3 reverse: ``AlterField`` reversal drops ``NOT NULL`` + ``unique``.
- Step 2 reverse: no-op — the ``AlterField`` reverse already
  loosened the constraint; leaving backfilled UUIDs in place is
  harmless.
- Step 1 reverse: ``AddField`` reversal drops the column entirely.

**No M1–M5 substrate touched.** Only ``VehiclePhoto`` gains one
column.
"""

import uuid

from django.db import migrations, models


def _backfill_public_ids(apps, schema_editor):
    """Assign a fresh :func:`uuid.uuid4` to every ``VehiclePhoto`` row
    that still has ``public_id=NULL`` after step 1.

    On an empty table the iterator is a no-op; on a table with legacy
    rows (dev exploration, test fixtures) each row gets its own unique
    UUID so step 3's ``unique=True`` constraint installs without
    violation.
    """
    VehiclePhoto = apps.get_model("dealer_ai", "VehiclePhoto")
    for photo in VehiclePhoto.objects.filter(public_id__isnull=True):
        photo.public_id = uuid.uuid4()
        photo.save(update_fields=["public_id"])


def _unbackfill_public_ids(apps, schema_editor):  # noqa: ARG001
    """Reverse of :func:`_backfill_public_ids` — intentionally a no-op.

    The AlterField reverse (step 3 → step 1 direction) loosens the
    NOT NULL + unique constraint; leaving backfilled UUIDs in place
    is harmless and preserves history if the migration is
    forward-reverted-forward.
    """
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0018_vehicle_photo_and_listing"),
    ]

    operations = [
        # Step 1: nullable, non-unique — every existing row gets NULL.
        migrations.AddField(
            model_name="vehiclephoto",
            name="public_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        # Step 2: backfill unique UUIDs for any existing rows.
        migrations.RunPython(_backfill_public_ids, _unbackfill_public_ids),
        # Step 3: enforce NOT NULL + unique. Sets the future default
        # for new rows via ``default=uuid.uuid4`` (called per-insert).
        migrations.AlterField(
            model_name="vehiclephoto",
            name="public_id",
            field=models.UUIDField(
                default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
