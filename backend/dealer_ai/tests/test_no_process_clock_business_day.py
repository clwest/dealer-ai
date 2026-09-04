"""SESSION_241.1 — the guard that stops the process-clock bug coming back.

Scans ``backend/dealer_ai/`` for ``timezone.now().date()`` and
``date.today()`` and fails on any hit that is not either:

- inside ``services/store_time.py`` (the one legitimate consumer), or
- inside a test file (tests may pin clocks), or
- on a line carrying the opt-out marker
  ``# no-store-clock: <reason>`` — reserved for the rare place a
  process-clock ``today`` genuinely is the right answer (e.g. a
  provenance stamp on a row that spans every tenant).

The marker is a conversation, not a wall: if a reviewer sees a new
marker in a diff, the reviewer asks "why is this legitimately not a
business day?" and the reason is right there on the line.

This is the third guard of the week and every one has the same shape:
the fix is cheap, the recurrence is what costs. Two prior sessions
(241 and this one) had to hunt every business-day site by hand; this
test means the next session finds them in CI, not on a walk.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.test import SimpleTestCase


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_MARKER = "no-store-clock:"
FORBIDDEN_PATTERNS = (
    re.compile(r"timezone\.now\(\)\.date\(\)"),
    re.compile(r"\bdate\.today\(\)"),
)


def _skip(path: Path) -> bool:
    parts = path.relative_to(PACKAGE_ROOT).parts
    if parts[0] == "tests":
        return True
    if parts == ("services", "store_time.py"):
        return True
    if "__pycache__" in parts:
        return True
    if parts[0] == "migrations":
        # Historical migrations are frozen — do not police them.
        return True
    return False


def _scan() -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for py in PACKAGE_ROOT.rglob("*.py"):
        if _skip(py):
            continue
        try:
            text = py.read_text()
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ALLOWLIST_MARKER in line:
                continue
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    hits.append((py, lineno, line.rstrip()))
                    break
    return hits


class NoProcessClockBusinessDayGuard(SimpleTestCase):
    def test_no_new_process_clock_today_in_dealer_ai(self):
        hits = _scan()
        if hits:
            lines = "\n".join(
                f"  {p.relative_to(PACKAGE_ROOT)}:{n}: {code}"
                for p, n, code in hits
            )
            self.fail(
                "process-clock 'today' found in backend/dealer_ai/ — a "
                "business-day site must use services.store_time."
                "store_today(dealership) so a Phoenix store at 22:00 "
                "does not book to Chicago's next day. If this really is "
                "not a business day (a provenance stamp that spans all "
                "tenants, an audit row keyed on the process clock, ...), "
                "add `# no-store-clock: <one-line reason>` on the same "
                "line.\n" + lines
            )
