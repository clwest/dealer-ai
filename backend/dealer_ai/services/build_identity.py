"""Capture the git identity this Django process booted with, once.

The captured values (``BUILD_IDENTITY``) are what the ``/health/version/``
endpoint reads. The rule is one-per-process: read at module import time,
never recompute on a request. A server booted at commit A and left running
while the tree moves to B must still answer "A" — that is the whole point of
the checker. If we shelled out to ``git rev-parse HEAD`` inside the request
handler, the endpoint would report the current working tree instead and the
check would pass forever while the process served yesterday's code.

Order the reader falls through:

1. Read ``.git`` directly (no subprocess). Normal dev path.
2. ``git rev-parse HEAD`` fallback, with a short timeout.
3. ``DEALER_AI_BUILD_SHA`` environment variable — for deployed environments
   where ``.git`` is absent (onrender).

If all three fail, ``sha`` is ``None``. ``None`` must NEVER be rendered as
"unknown but probably fine" downstream — see ``scripts/verify_pair.py`` for
the four-outcome table.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from django.conf import settings


def _read_sha_from_dotgit(repo_root: Path) -> Optional[str]:
    """Read HEAD's SHA by walking ``.git`` directly, no subprocess."""
    git_dir = repo_root / ".git"
    head = git_dir / "HEAD"
    if not head.is_file():
        return None
    raw = head.read_text().strip()
    if raw.startswith("ref:"):
        ref = raw.split(":", 1)[1].strip()
        ref_path = git_dir / ref
        if ref_path.is_file():
            return ref_path.read_text().strip() or None
        packed = git_dir / "packed-refs"
        if packed.is_file():
            for line in packed.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("^"):
                    continue
                sha, _, ref_name = line.partition(" ")
                if ref_name == ref:
                    return sha or None
        return None
    if len(raw) == 40 and all(c in "0123456789abcdef" for c in raw):
        return raw
    return None


def _read_branch_from_dotgit(repo_root: Path) -> Optional[str]:
    head = repo_root / ".git" / "HEAD"
    if not head.is_file():
        return None
    raw = head.read_text().strip()
    if raw.startswith("ref:"):
        ref = raw.split(":", 1)[1].strip()
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            return ref[len(prefix):]
        return ref
    return None


def _read_sha_via_git(repo_root: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "--no-optional-locks", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    sha = out.stdout.strip()
    return sha or None


def _read_branch_via_git(repo_root: Path) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "--no-optional-locks", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    name = out.stdout.strip()
    if not name or name == "HEAD":
        return None
    return name


def _read_dirty(repo_root: Path) -> Optional[bool]:
    """True when the working tree had uncommitted changes at boot.

    Uses ``git --no-optional-locks status --porcelain`` per the task's
    non-goal (no plain ``git status`` anywhere in this work). ``None`` when
    git is unavailable — an unknown dirty state is not the same as clean.
    """
    try:
        out = subprocess.run(
            ["git", "--no-optional-locks", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return bool(out.stdout.strip())


def _capture() -> dict:
    repo_root: Path = Path(settings.BASE_DIR).parent

    sha = _read_sha_from_dotgit(repo_root)
    branch = _read_branch_from_dotgit(repo_root)
    if sha is None:
        sha = _read_sha_via_git(repo_root)
        if branch is None:
            branch = _read_branch_via_git(repo_root)
    if sha is None:
        env_sha = os.environ.get("DEALER_AI_BUILD_SHA", "").strip()
        sha = env_sha or None

    dirty = _read_dirty(repo_root)

    return {
        "sha": sha,
        "sha_short": sha[:7] if sha else None,
        "branch": branch,
        "dirty": dirty,
        "booted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pid": os.getpid(),
    }


BUILD_IDENTITY: dict = _capture()
