#!/usr/bin/env python3
"""Verify what code the dev pair is actually serving.

Reads the backend's ``/api/dealer-ai/health/version/`` and the frontend's
``/__version``, compares each server's captured boot-time SHA to the
working tree's ``git rev-parse HEAD``, and prints a verdict. Exit 0 iff
both match HEAD; exit 1 for everything else — including
NO_VERSION_ENDPOINT, which is not a pass.

Run this on the Mac. A curl from inside a Linux VM's loopback (the Cowork
mount) does NOT reach the Mac's 127.0.0.1 — a connection refused there is
evidence about the VM, not about the servers.

Five outcomes, all distinguishable:

  MATCH                server reports HEAD's sha
  STALE                server reports an older sha — say how many
                       commits behind
  NO_VERSION_ENDPOINT  server 404s the version URL but is alive on a
                       liveness route — booted from code that predates
                       this check; restart to make it checkable
  UNREACHABLE          server does not answer (connection refused, DNS,
                       timeout — OR 404 with the liveness probe also
                       failing) — not the same as being stale
  UNREADABLE           server answered but sha is null OR body will not
                       parse OR status is not 200/404 — its own state,
                       never conflated with MATCH

The point of the whole design: "the server is down" and "the server is
up and older than the check" are different facts, and the second one is
the NORMAL case during a rollout. Collapsing them sends someone hunting
for a crashed process. NO_VERSION_ENDPOINT must be **earned** — by a
positive liveness probe on a route we know answers. Without that
positive signal the answer is UNREACHABLE.

Liveness probe URLs (paired with the version URL on each server):

  backend  GET /api/dealer-ai/auth/me/   — any HTTP response = alive
  frontend GET /                          — vite SPA fallback = alive
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

DEFAULT_BACKEND = "http://127.0.0.1:8001"
DEFAULT_FRONTEND = "http://127.0.0.1:5173"
BACKEND_VERSION_PATH = "/api/dealer-ai/health/version/"
BACKEND_LIVENESS_PATH = "/api/dealer-ai/auth/me/"
FRONTEND_VERSION_PATH = "/__version"
FRONTEND_LIVENESS_PATH = "/"
REPO_ROOT = Path(__file__).resolve().parent.parent

RESTART_HINT = (
    "restart the pair (docs/_internal/TASK_restart-servers.md) so the "
    "version endpoint is loaded and this becomes checkable"
)


@dataclass
class FetchResult:
    """Outcome of hitting one URL.

    Three mutually exclusive shapes:

    - ``status`` set, ``identity`` is a dict → parsed 200 OK JSON
    - ``status`` set, ``identity`` is None → HTTP error status or body
      that could not be parsed (``parse_error`` explains)
    - ``status`` is None → connection-level failure (``conn_error``)

    Keeping ``status is None`` distinct from ``status == 404`` is the
    whole point of adding this layer — a dead port and a
    predates-the-endpoint server are different facts.
    """

    status: Optional[int] = None
    identity: Optional[dict] = None
    parse_error: Optional[str] = None
    conn_error: Optional[str] = None


@dataclass
class ServerReport:
    label: str
    version_url: str
    liveness_url: str
    version: FetchResult = field(default_factory=FetchResult)
    # ``None`` when we did not need to run the liveness probe (the
    # version fetch already told us what we needed). ``True`` / ``False``
    # once we probed. A liveness probe counts as True if we got ANY HTTP
    # response — even 401 or 404. The signal is "the process handled
    # the request", not "the URL was found."
    liveness_alive: Optional[bool] = None
    liveness_note: Optional[str] = None  # status code or error string

    @property
    def sha(self) -> Optional[str]:
        if not self.version.identity:
            return None
        raw = self.version.identity.get("sha")
        return raw if isinstance(raw, str) and raw else None


def _fetch(url: str, timeout: float = 3.0) -> FetchResult:
    """Fetch a URL. Never raise — every failure mode collapses into a
    FetchResult with either ``conn_error`` or ``parse_error`` set."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # The remote process answered — we just got a non-2xx. That is
        # NOT a connection error. Record the status so the verdict can
        # tell 404 apart from 500 apart from 502.
        return FetchResult(status=exc.code, parse_error=f"HTTP {exc.code} {exc.reason}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return FetchResult(conn_error=f"{exc.__class__.__name__}: {exc}")
    if status != 200:
        return FetchResult(
            status=status,
            parse_error=f"HTTP {status} (expected 200)",
        )
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return FetchResult(
            status=status, parse_error=f"invalid JSON: {exc}"
        )
    if not isinstance(data, dict):
        return FetchResult(
            status=status,
            parse_error=f"body is not a JSON object: {type(data).__name__}",
        )
    return FetchResult(status=status, identity=data)


def _liveness_probe(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    """Return (alive, human_note). Alive iff we got any HTTP response.

    A 200 is alive. A 401, 403, 404, 500 are all alive — the process
    handled the request. Only a connection-level failure (refused,
    timeout, DNS) means not alive.
    """
    req = urllib.request.Request(url, headers={"Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return True, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


def _probe_server(report: ServerReport) -> None:
    """Fill in report.version and (when needed) report.liveness_*.

    The liveness probe is only run when the version fetch returned 404.
    For any other outcome the version fetch already tells us what we
    need. This keeps the checker fast in the healthy case (one HTTP
    round-trip per server) and only pays for the second probe in the
    ambiguous one.
    """
    report.version = _fetch(report.version_url)
    if report.version.status == 404:
        alive, note = _liveness_probe(report.liveness_url)
        report.liveness_alive = alive
        report.liveness_note = note


def _run(*args: str, cwd: Path = REPO_ROOT, timeout: float = 3.0) -> Optional[str]:
    """Run a subprocess and return stdout (stripped, EMPTY string kept
    distinct from ``None``). ``None`` means the command failed; empty
    string means it ran and produced no output. Collapsing those two —
    L-029 / L-036 — is one of the failures this checker is about."""
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
    return out.stdout.strip()


def _head_sha() -> Optional[str]:
    out = _run("git", "--no-optional-locks", "rev-parse", "HEAD")
    return out if out else None


def _tree_dirty() -> Optional[bool]:
    """Return True/False for the working-tree dirty state, ``None`` when
    git could not answer. An empty output is a real answer (clean tree),
    not a failure — see the docstring on ``_run``."""
    out = _run("git", "--no-optional-locks", "status", "--porcelain")
    if out is None:
        return None
    return bool(out)


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

    States: MATCH, STALE, NO_VERSION_ENDPOINT, UNREACHABLE, UNREADABLE,
    UNKNOWN.

    UNKNOWN is only returned when the working-tree HEAD itself could not
    be read; the checker cannot compare to nothing.
    """
    v = report.version

    # 1. Connection-level failure — nothing to probe further. UNREACHABLE.
    if v.conn_error is not None:
        return (
            "UNREACHABLE",
            f"{report.label} did not answer: {v.conn_error}",
        )

    # 2. HTTP 404 — needs the liveness probe to decide.
    if v.status == 404:
        if report.liveness_alive:
            return (
                "NO_VERSION_ENDPOINT",
                f"{report.label} is running (liveness {report.liveness_url} "
                f"→ {report.liveness_note}) but 404s the version URL — "
                f"booted from code that predates the check. "
                f"{RESTART_HINT}",
            )
        return (
            "UNREACHABLE",
            f"{report.label} 404s the version URL AND the liveness probe "
            f"({report.liveness_url}) failed "
            f"({report.liveness_note or 'unknown'}) — treat as unreachable",
        )

    # 3. Any other non-200 status — UNREADABLE, and say which status.
    if v.status is None or v.status != 200:
        return (
            "UNREADABLE",
            f"{report.label} returned HTTP {v.status} — "
            f"cannot read a version out of this response",
        )

    # 4. HTTP 200 but body will not parse — UNREADABLE, and say why.
    if v.identity is None:
        return (
            "UNREADABLE",
            f"{report.label} returned HTTP 200 but the body will not parse: "
            f"{v.parse_error}",
        )

    # 5. HTTP 200, parsed — read the sha.
    sha = report.sha
    if sha is None:
        return (
            "UNREADABLE",
            f"{report.label} answered but sha is null "
            f"(identity={v.identity!r}) — this is its own state, "
            "NOT a match",
        )
    if head_sha is None:
        return (
            "UNKNOWN",
            f"{report.label} reports sha {sha[:7]}, but the working tree's "
            "HEAD could not be read — cannot compare",
        )
    if sha == head_sha:
        dirty = v.identity.get("dirty")
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

    head_sha = _head_sha()
    dirty = _tree_dirty()

    backend = ServerReport(
        label="backend",
        version_url=args.backend.rstrip("/") + BACKEND_VERSION_PATH,
        liveness_url=args.backend.rstrip("/") + BACKEND_LIVENESS_PATH,
    )
    frontend = ServerReport(
        label="frontend",
        version_url=args.frontend.rstrip("/") + FRONTEND_VERSION_PATH,
        liveness_url=args.frontend.rstrip("/") + FRONTEND_LIVENESS_PATH,
    )
    _probe_server(backend)
    _probe_server(frontend)

    backend_state, backend_line = _verdict_for(backend, head_sha)
    frontend_state, frontend_line = _verdict_for(frontend, head_sha)

    exit_code = 0 if (backend_state == "MATCH" and frontend_state == "MATCH") else 1

    def _server_payload(r: ServerReport, state: str, line: str) -> dict:
        return {
            "state": state,
            "line": line,
            "identity": r.version.identity,
            "status": r.version.status,
            "parse_error": r.version.parse_error,
            "conn_error": r.version.conn_error,
            "liveness_alive": r.liveness_alive,
            "liveness_note": r.liveness_note,
            "version_url": r.version_url,
            "liveness_url": r.liveness_url,
        }

    if args.json:
        payload: dict[str, Any] = {
            "head_sha": head_sha,
            "tree_dirty": dirty,
            "backend": _server_payload(backend, backend_state, backend_line),
            "frontend": _server_payload(frontend, frontend_state, frontend_line),
            "exit_code": exit_code,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code

    if head_sha is None:
        print("HEAD: <unreadable — git rev-parse failed>")
    else:
        dirty_word = "dirty" if dirty else ("clean" if dirty is False else "dirty state unknown")
        print(f"HEAD: {head_sha[:7]} — tree is {dirty_word}")
    print(f"  {backend_state:19s} {backend_line}")
    print(f"  {frontend_state:19s} {frontend_line}")

    if exit_code == 0:
        print("both servers are on HEAD.")
    else:
        print("verdict: the pair is not fully serving HEAD — see above.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
