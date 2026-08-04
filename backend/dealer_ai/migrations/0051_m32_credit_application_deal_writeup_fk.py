"""Milestone 32 · Increment 1 (SESSION_207) — CA → DealWriteup backpointer.

Per ``MILESTONE_32_PLANNING.md`` §5.b D9-revised² (user-confirmed at
SESSION_206 open, recorded in §5.b): add a nullable
:class:`OneToOneField` from :class:`CreditApplication` to
:class:`DealWriteup` so the F&I intake queue can pair CAs to their
originating writeups deterministically.

**Why a schema change now.** M11.3 shipped a "peer-not-child"
architectural preference between CA and DealWriteup with no
structural link — pairing was implicit via shared ``lead`` FK and
the ``Deal write-up #<pk> handoff:`` text prefix that
:func:`services.deal_writeups._format_handoff_notes` writes into
``CreditApplication.notes``. That worked when there was no F&I intake
UI and no per-lead multiplicity concern. At M32.1 the F&I intake page
needs unambiguous writeup-to-CA pairing: one lead can legitimately
have N writeups → N hand-offs → N CAs, all sharing the same lead FK.
Text-based pairing is fragile (operator-writable field; brittle to
parse); time-window pairing is non-deterministic. A schema-level
link is the smallest structural change that makes pairing
deterministic.

**Why OneToOneField, not ForeignKey + unique_constraint.** The
hand-off service contract permits only one successful hand-off per
writeup (:class:`services.deal_writeups.WriteupAlreadyHandedOffError`
raised on second attempt). A plain nullable ForeignKey would allow
multiple CAs to point to the same writeup at the schema layer,
contradicting that lifecycle contract. OneToOneField is Django-native
and auto-generates the unique index on the FK column, enforcing the
"at most one CA per writeup" invariant idempotently under any caller
path — including alternate ORM writes and future migrations.

**Nullability preserved.** ``SET_NULL`` on delete + nullable +
blank=True. Direct-created CAs via :func:`services.f_and_i.record_credit_application`
without a ``deal_writeup=`` kwarg (the M10.1 path) stay NULL. All
historical rows pre-M32.1 stay NULL — backfill-free.

**Three-layer defense against duplicate pairings** (documented in
detail in ``docs/roadmap/MILESTONE_32_PLANNING.md`` §5.b D9-revised²):

1. Database layer — OneToOne unique index. ``IntegrityError`` on any
   second insert. Catches all callers.
2. Service layer (``record_credit_application``) — new
   :class:`services.f_and_i.DealWriteupAlreadyLinkedError` raised
   before the DB write when the incoming writeup is already paired.
   Endpoint layer maps to 409 CONFLICT.
3. Service layer (``hand_off_to_fandi``) — existing
   :class:`services.deal_writeups.WriteupAlreadyHandedOffError`
   (M11.3 shipped) catches the writeup-side path.

**Semantic.** Peer-with-optional-backpointer, not compositional
child. Retention-clock ownership stays on the CA per M10.1 §5.e —
the CA outlives its writeup (SET_NULL preserves the CA if the
writeup is deleted). The FK is a discovery aid for the F&I intake
queue, not a parent-child link. The M11.3 architectural preference
("no FK on either side") was accurate at that time; M32.1 records
the evolution truthfully here and in the current model docstrings
without rewriting historical migration 0034.

**Reverse-migration behavior.** Fully reversible — Django's
auto-generated ``migrations.AddField.database_backwards`` drops the
column. Existing CA and DealWriteup rows are preserved on revert;
only the linkage data (``deal_writeup_id`` values written by
hand-offs between deploy and revert) is dropped. Operationally
recoverable because the M11.3 ``_format_handoff_notes`` text prefix
in ``CreditApplication.notes`` remains as the pre-M32.1 pairing
hint.

See ``docs/roadmap/MILESTONE_32_PLANNING.md`` §5.b D9-revised² +
§5.g Rollback for the full contract.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0050_m281_je_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="creditapplication",
            name="deal_writeup",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="credit_application",
                to="dealer_ai.dealwriteup",
            ),
        ),
    ]
