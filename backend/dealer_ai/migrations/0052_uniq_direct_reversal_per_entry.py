"""Duplicate-direct-reversal defect fix — DB-level guard.

An adversarial audit demonstrated that ``reverse_journal_entry`` would
accept a second direct reversal of the same original JournalEntry.
Both reversals would persist, both pointing at the original via the
``reverses`` FK, and the per-account ledger would double-apply the
correction (debits still balanced credits system-wide, so the balance
invariant did not catch it).

The invariant: **a JournalEntry may be directly reversed at most
once.** Reversing a reversal is intentionally still allowed — that
produces a chain (``original ← A ← B``) where each ``reverses`` value
is distinct.

This migration adds a partial unique index on
``JournalEntry.reverses`` (``WHERE reverses IS NOT NULL``). Original
postings (``reverses IS NULL``) remain unconstrained; two reversals
pointing at the same target are now rejected at the storage layer.

Portability: Django's ``UniqueConstraint(condition=...)`` compiles to
a partial unique index on both PostgreSQL (production) and SQLite
(dev / test / acceptance) — SQLite has supported partial indexes since
3.8.0, well below any version this repo runs against.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0051_m32_credit_application_deal_writeup_fk"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.UniqueConstraint(
                fields=("reverses",),
                condition=models.Q(reverses__isnull=False),
                name="uniq_direct_reversal_per_entry",
            ),
        ),
    ]
