"""Coverage guard: every flag the services layer can emit must be
mapped in :data:`services.audit._FLAG_CATEGORIES`.

TASK_label-pass §1 — the overview's Recent activity card fell back to
``(Unknown)`` for four flags the chat engine actually emits
(``list_shape_scrubbed``, ``meta_narration_scrubbed``,
``banned_phrase_scrubbed`` and ``provider_unavailable``). Categorising
those four is the fix; this test is the guard so the next scrub added
without a category surfaces at ``pytest`` time instead of the next
browser walk.

Instrument: scan ``services/`` sources for two assignment shapes —

    assistant_metadata["flag"] = "..."
    {"flag": "..."}

— union the string literals, and assert every one exists as a key in
``_FLAG_CATEGORIES``. A dynamically assigned flag (e.g. a variable
holding a name) is out of scope of the regex — those paths route
through the same set of literal names elsewhere in the file, which the
scan does pick up. If a future scrub is introduced via a fresh
variable name, this test will not catch it; the reasonable fix at
that point is to hoist the whole flag set into a module-level
frozenset the engine assigns from.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Set

from django.test import TestCase

from dealer_ai.services.audit import _FLAG_CATEGORIES


SERVICES_DIR = Path(__file__).resolve().parent.parent / "services"

# Two shapes the chat engine and vehicle-ask path use to stamp
# ``flag`` on assistant metadata. The scan matches literal strings
# only — dynamic assignments (``metadata["flag"] = some_var``) are
# out of scope by design; see module docstring.
_FLAG_ASSIGN_PATTERNS = (
    re.compile(r'''\["flag"\]\s*=\s*[\(\s]*["']([a-z_][a-z0-9_]*)["']'''),
    re.compile(r'''["']flag["']\s*:\s*["']([a-z_][a-z0-9_]*)["']'''),
)


def _collect_emitted_flags() -> Set[str]:
    seen: Set[str] = set()
    for path in SERVICES_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in _FLAG_ASSIGN_PATTERNS:
            seen.update(pattern.findall(text))
    return seen


class AuditFlagCoverageTests(TestCase):
    """Fails when a new flag ships without an entry in ``_FLAG_CATEGORIES``."""

    def test_every_emitted_flag_is_categorized(self):
        emitted = _collect_emitted_flags()
        # Guardrail: the scanner is only useful if it's actually
        # finding assignments. If a refactor moves the flag-writing
        # code out of ``services/`` we want the test to raise here,
        # not silently pass with zero hits.
        self.assertGreater(
            len(emitted),
            10,
            "flag-assignment scan found suspiciously few hits — "
            "the assignment shape probably changed; update the "
            "patterns in this test.",
        )
        missing = sorted(emitted - _FLAG_CATEGORIES.keys())
        self.assertFalse(
            missing,
            "New flag(s) emitted by services/ have no category in "
            "``services.audit._FLAG_CATEGORIES``: "
            f"{missing}. Add each to _FLAG_CATEGORIES (and to "
            "FLAG_DISPLAY_NAMES in frontend/src/components/AuditPanel.tsx) "
            "so the overview + audit panel render a label instead of "
            "falling back to '(Unknown)'.",
        )
