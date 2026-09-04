#!/usr/bin/env python3
"""Verify what code the dev pair is actually serving.

Reads the backend's ``/api/dealer-ai/health/version/`` and the frontend's
``/__version``, compares each server's captured boot-time SHA to the
working tree's ``git rev-parse HEAD``, and prints a verdict. Exit 0 iff
both match HEAD; exit 1 otherwise so a brief can gate on it.

Run this on the Mac. A curl from inside a Linux VM's loopback (the Cowork
mount) does NOT reach the Mac's 127.0.0.1 — a connection refused there is
evidence about the VM, not about the servers.

Four outcomes, all distinguishable:

  MATCH        server reports HEAD's sha
  STALE        server reports an older sha — say how many commits behind
  UNREACHABLE  server does not answer — not the same as being stale
  UNREADABLE   server answered but sha is null — its own state, never
               conflated with MATCH

The point of the whole task is that last row: an unreadable answer is not
a passing answer. This is the same rule the reconciler had to be taught
four times: "I could not read it" and "it agrees" are different facts.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DEFAULT_BACKEND = "http://127.0.0.1:8001"
DEFAULT_FRONTEND = "http://127.0.0.1:5173"
BACKEND_PATH = "/api/dealer-ai/health/version/"
FRONTEND_PATH = "/__version"
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ServerReport:
    label: str
    url: str
    ok: bool
    identity: Optional[dict]
    error: Optional[str]

    @property
    def sha(self) -> Optional[str]:
        if not self.identity:
            return None
        raw = self.identity.get("sha")
        return raw if isinstance(raw, str) and raw else None


def _fetch(url: str, timeout: float = 3.0) -> ServerReport:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return ServerReport(
            label=url, url=url, ok=False, identity=None,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return ServerReport(
            label=url, url=url, ok=False, identity=None,
            error=f"{exc.__class__.__name__}: {exc}",
        )
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return ServerReport(
            label=url, url=url, ok=False, identity=None,
            error=f"invalid JSON: {exc}",
        )
    if not isinstance(data, dict):
        return ServerReport(
            label=url, url=url, ok=False, identity=None,
            error=f"body is not an object: {type(data).__name__}",
        )
    return ServerReport(
        label=url, url=url, ok=True, identity=data, error=None,
    )


def _run(*args: str, cwd: Path = REPO_ROOT, timeout: float = 3.0) -> Optional[str]:
    try:
        out = subprocess.run(
            list(args),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _head_sha() -> Optional[str]:
    return _run("git", "--no-optional-locks", "rev-parse", "HEAD")


def _tree_dirty() -> Optional[bool]:
    out = _run("git", "--no-optional-locks", "status", "--porcelain")
    if out is None:
        return None
    return bool(out.strip())


def _commits_behind(server_sha: str, head_sha: str) -> Optional[int]:
    """Return the number of commits between server_sha and HEAD along
    first-parent history. ``None`` if git cannot answer (e.g. commit not
    in local history yet)."""
    if server_sha == head_sha:
        return 0
    out = _run("git", "--no-optional-locks", "rev-list", "--count", f"{server_sha}..{head_sha}")
    if out is None:
        return None
    try:
        return int(out)
    except ValueError:
        return None


def _verdict_for(report: ServerReport, head_sha: Optional[str]) -> tuple[str, str]:
    """Return (STATE, human_line) for one server.

    States: MATCH, STALE, UNREACHABLE, UNREADABLE, UNKNOWN.
    UNKNOWN is only returned when the working-tree HEAD itself could not
    be read; the checker cannot compare to nothing.
    """
    if not report.ok:
        return "UNREACHABLE", f"{report.label} did not answer: {report.error}"
    sha = report.sha
    if sha is None:
        return (
            "UNREADABLE",
            f"{report.label} answered but sha is null "
            f"(identity={report.identity!r}) — this is its own state, "
            "NOT a match",
        )
    if head_sha is None:
        return (
            "UNKNOWN",
            f"{report.label} reports sha {sha[:7]}, but the working tree's "
            "HEAD could not be read — cannot compare",
        )
    if sha == head_sha:
        dirty = report.identity.get("dirty") if report.identity else None
        dirty_note = " (booted against a dirty tree)" if dirty else ""
        return "MATCH", f"{report.label} on HEAD {sha[:7]}{dirty_note}"
    behind = _commits_behind(sha, head_sha)
    if behind is None:
        return (
            "STALE",
            f"{report.label} reports sha {sha[:7]}, HEAD is {head_sha[:7]} "
            "— server sha is not in local history so commits-behind is "
            "unknown; the server was not restarted at HEAD",
        )
    return (
        "STALE",
        f"{report.label} reports sha {sha[:7]} — {behind} commit"
        f"{'s' if behind != 1 else ''} behind HEAD ({head_sha[:7]}); "
        "the server was not restarted",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        default=os.environ.get("VERIFY_PAIR_BACKEND", DEFAULT_BACKEND),
        help=f"backend base URL (default: {DEFAULT_BACKEND})",
    )
    parser.add_argument(
        "--frontend",
        default=os.environ.get("VERIFY_PAIR_FRONTEND", DEFAULT_FRONTEND),
        help=f"frontend base URL (default: {DEFAULT_FRONTEND})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of the human report",
    )
    args = parser.parse_args(argv)

    backend_url = args.backend.rstrip("/") + BACKEND_PATH
    frontend_url = args.frontend.rstrip("/") + FRONTEND_PATH

    head_sha = _head_sha()
    dirty = _tree_dirty()

    backend = _fetch(backend_url)
    backend.label = "backend"
    frontend = _fetch(frontend_url)
    frontend.label = "frontend"

    backend_state, backend_line = _verdict_for(backend, head_sha)
    frontend_state, frontend_line = _verdict_for(frontend, head_sha)

    exit_code = 0 if (backend_state == "MATCH" and frontend_state == "MATCH") else 1

    if args.json:
        payload: dict[str, Any] = {
            "head_sha": head_sha,
            "tree_dirty": dirty,
            "backend": {
                "state": backend_state,
                "line": backend_line,
                "identity": backend.identity,
                "error": backend.error,
                "url": backend.url,
            },
            "frontend": {
                "state": frontend_state,
                "line": frontend_line,
                "identity": frontend.identity,
                "error": frontend.error,
                "url": frontend.url,
            },
            "exit_code": exit_code,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code

    if head_sha is None:
        print("HEAD: <unreadable — git rev-parse failed>")
    else:
        dirty_word = "dirty" if dirty else ("clean" if dirty is False else "dirty state unknown")
        print(f"HEAD: {head_sha[:7]} — tree is {dirty_word}")
    print(f"  {backend_state:11s} {backend_line}")
    print(f"  {frontend_state:11s} {frontend_line}")

    if exit_code == 0:
        print("both servers are on HEAD.")
    else:
        print("verdict: the pair is not fully serving HEAD — see above.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
