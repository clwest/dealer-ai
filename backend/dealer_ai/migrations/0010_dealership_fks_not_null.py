"""Milestone 1 · Increment 3 — flip the six tenancy FKs to NOT NULL.

Depends on ``0009_backfill_dealership_fks`` having seeded the default
:class:`Dealership` row and backfilled every pre-existing row of the
six tenant carriers. Depends on the write-path plumbing shipped in
SESSION_038 (``services/tenancy.py`` primitive + ``pre_save`` fallback
signal registered in :class:`dealer_ai.apps.DealerAiConfig`) so every
future insert either carries an explicit ``dealership=`` or gets the
default attached before it hits the DB.

Reverse migration flips the FKs back to nullable. Combined with the
reverse of ``0009`` (which nulls out backfilled rows and deletes the
default Dealership) and the reverse of ``0008`` (which drops the FK
columns), the milestone is fully reversible for local dev / rollback.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0009_backfill_dealership_fks"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatmessage",
            name="dealership",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chat_messages",
                to="dealer_ai.dealership",
            ),
        ),
        migrations.AlterField(
            model_name="chatsession",
            name="dealership",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chat_sessions",
                to="dealer_ai.dealership",
            ),
        ),
        migrations.AlterField(
            model_name="customerlead",
            name="dealership",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="customer_leads",
                to="dealer_ai.dealership",
            ),
        ),
        migrations.AlterField(
            model_name="dealeronboardingprofile",
            name="dealership",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="onboarding_profiles",
                to="dealer_ai.dealership",
            ),
        ),
        migrations.AlterField(
            model_name="salesperson",
            name="dealership",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="salespeople",
                to="dealer_ai.dealership",
            ),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="dealership",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="vehicles",
                to="dealer_ai.dealership",
            ),
        ),
    ]
