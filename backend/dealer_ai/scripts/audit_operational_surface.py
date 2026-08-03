"""
M21.1 operational-surface audit — §5.b Option C combined methodology.

Purpose
-------
Identify backend capabilities (DRF endpoints + service verbs) that are
NOT reachable through the shipped frontend UI. Emits a markdown table
that feeds ``docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md``.

Design
------
The dealer_ai app centralizes its HTTP surface in a single flat
``backend/dealer_ai/urls.py`` (function-based views) and the frontend
centralizes API consumption in a single ``frontend/src/lib/api.ts``
(all calls go through ``authGetJSON`` / ``authPostJSON`` /
``authPatchJSON`` / ``authPutJSON`` / ``authDelete`` /
``authPostForm`` or plain ``fetch`` for public endpoints).

That regularity means the audit does not need an AST — regex-based
extraction is sufficient and the output is auditable.

Two parallel walks:

1. **DRF endpoint enumeration.** Parse ``urls.py``; extract each
   ``path()`` entry as ``(url_pattern, view_callable, url_name)``.
2. **Service-verb enumeration.** Walk ``services/**/*.py``; extract
   public top-level callables (``def name(...)`` without leading
   underscore). Cross-reference to ``from .services.X import Y``
   imports in view modules to mark verbs as endpoint-exposed vs.
   internal.

Then the frontend consumption walk:

3. **Frontend consumer enumeration.** Parse
   ``frontend/src/lib/api.ts``; extract every ``auth*JSON`` /
   ``authDelete`` / ``authPostForm`` call and its URL literal /
   template. Also captures plain ``fetch("/api/dealer-ai/...")``
   calls for public endpoints.

Cross-reference (URL normalization: ``<int:pk>`` /
``<slug:slug>`` in Django patterns match ``${pk}`` / ``${slug}`` in
frontend template literals — both collapse to ``{PARAM}``).

Usage
-----
::

    python3 backend/dealer_ai/scripts/audit_operational_surface.py \
        --repo-root /Users/.../freedom-ford \
        --out docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md

Or from the repo root::

    cd backend
    python3 -m dealer_ai.scripts.audit_operational_surface

Rerun-safe: idempotent on unchanged code. Rerun after new endpoints
ship to refresh the artifact for future OSC-shaped milestones.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# --------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------


@dataclass(frozen=True)
class BackendEndpoint:
    url_pattern: str
    normalized_pattern: str
    view_callable: str
    url_name: str
    source_line: int


@dataclass(frozen=True)
class ServiceVerb:
    name: str
    module: str
    source_line: int


@dataclass(frozen=True)
class FrontendConsumer:
    helper: str  # "authGetJSON" | "authPostJSON" | ...
    url_expr: str  # raw source expression
    normalized_pattern: str
    source_line: int
    # Name of the exported wrapper function in *Api.ts that owns this
    # call, if any. Populated during main() so we can second-pass check
    # whether components consume the wrapper.
    wrapper_name: str = ""
    # True if the wrapper is imported / referenced by a .tsx component
    # outside of test files. False for wrappers that exist only in the
    # API module (backend surface reachable in principle but no
    # operator-facing UI).
    component_consumed: bool = True


@dataclass
class AuditRow:
    url_pattern: str
    normalized_pattern: str
    view_callable: str
    url_name: str
    frontend_consumers: list[FrontendConsumer] = field(default_factory=list)
    service_verbs_imported: list[str] = field(default_factory=list)

    @property
    def is_backend_only(self) -> bool:
        # No consumers at all → backend-only.
        if not self.frontend_consumers:
            return True
        # Every consumer's wrapper is unused by any component → the
        # endpoint has a typed wrapper but no operator-facing UI. Still
        # counts as backend-only from an operator perspective (the whole
        # M21 governing contract cares about UI reachability, not
        # wrapper reachability).
        return all(not c.component_consumed for c in self.frontend_consumers)

    @property
    def is_wrapper_only(self) -> bool:
        """True when the endpoint has a typed wrapper but no component
        consumes it. Distinct from truly-uncovered endpoints where no
        wrapper exists at all."""
        return (
            bool(self.frontend_consumers)
            and all(not c.component_consumed for c in self.frontend_consumers)
        )


# --------------------------------------------------------------------
# URL normalization
# --------------------------------------------------------------------


_DJANGO_PARAM_RE = re.compile(r"<[a-z]+:[a-z_]+>|<[a-z_]+>")
_TS_TEMPLATE_RE = re.compile(r"\$\{[^}]+\}")
_STRIP_TRAILING_SLASH_RE = re.compile(r"/+$")


def normalize_django(pattern: str) -> str:
    """Collapse ``<int:pk>``, ``<slug:slug>``, ``<uuid:public_id>``, etc.
    into a single sentinel so backend + frontend patterns compare."""
    out = _DJANGO_PARAM_RE.sub("{PARAM}", pattern)
    out = _STRIP_TRAILING_SLASH_RE.sub("/", out)
    if not out.startswith("/"):
        out = "/" + out
    return out.rstrip("/") + "/"


def normalize_frontend(url_expr: str) -> str:
    """Strip template ``${...}`` substitutions to ``{PARAM}`` and strip
    leading ``API_BASE`` / plain quotes so patterns compare to Django."""
    raw = url_expr.strip()
    # Trim wrapping quotes / backticks
    if raw and raw[0] in "\"'`":
        raw = raw[1:]
    if raw and raw[-1] in "\"'`":
        raw = raw[:-1]
    # Strip an optional leading ${API_BASE} — most helper calls prefix it
    raw = re.sub(r"^\$\{API_BASE\}", "", raw)
    # Also strip a bare API_BASE prefix that the file sometimes concatenates
    raw = re.sub(r"^API_BASE\s*\+\s*", "", raw)
    # Now collapse remaining template substitutions to {PARAM}
    raw = _TS_TEMPLATE_RE.sub("{PARAM}", raw)
    # Trim query strings
    raw = raw.split("?", 1)[0]
    if not raw.startswith("/"):
        raw = "/" + raw
    raw = _STRIP_TRAILING_SLASH_RE.sub("/", raw)
    return raw.rstrip("/") + "/"


# --------------------------------------------------------------------
# Backend enumeration
# --------------------------------------------------------------------


_PATH_CALL_RE = re.compile(
    # path(
    #    "pattern" [ "continuation" ...],
    #    <view_module>.view_callable,
    #    name="url-name",
    # )
    r"path\(\s*"
    r"((?:(?:\"[^\"]*\"|'[^']*')\s*)+),\s*"
    r"([a-zA-Z_][\w\.]+)\s*,\s*"
    r"name\s*=\s*[\"']([^\"']+)[\"']\s*,?\s*\)",
    re.MULTILINE | re.DOTALL,
)


def extract_backend_endpoints(urls_source: str) -> list[BackendEndpoint]:
    endpoints: list[BackendEndpoint] = []
    for m in _PATH_CALL_RE.finditer(urls_source):
        pieces = re.findall(r"[\"']([^\"']+)[\"']", m.group(1))
        pattern = "".join(pieces)
        view_callable = m.group(2)
        url_name = m.group(3)
        source_line = urls_source[: m.start()].count("\n") + 1
        endpoints.append(
            BackendEndpoint(
                url_pattern=pattern,
                normalized_pattern=normalize_django(pattern),
                view_callable=view_callable,
                url_name=url_name,
                source_line=source_line,
            )
        )
    return endpoints


# --------------------------------------------------------------------
# Service-verb enumeration
# --------------------------------------------------------------------


_PUBLIC_DEF_RE = re.compile(
    r"^def\s+([a-z][a-zA-Z0-9_]*)\s*\(", re.MULTILINE
)


def extract_service_verbs(services_root: Path) -> list[ServiceVerb]:
    verbs: list[ServiceVerb] = []
    for path in sorted(services_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        module_rel = path.relative_to(services_root.parent).as_posix()
        # Skip clearly-internal support modules (tasks / test / migrations)
        if "/tests/" in module_rel or module_rel.endswith("/tests.py"):
            continue
        source = path.read_text()
        for m in _PUBLIC_DEF_RE.finditer(source):
            name = m.group(1)
            source_line = source[: m.start()].count("\n") + 1
            verbs.append(ServiceVerb(name=name, module=module_rel, source_line=source_line))
    return verbs


_SERVICE_IMPORT_RE = re.compile(
    r"from\s+\.services(?:\.[a-z_]+)*\s+import\s+([^\n]+)", re.MULTILINE
)


def view_imported_verbs(view_source: str) -> set[str]:
    imported: set[str] = set()
    for m in _SERVICE_IMPORT_RE.finditer(view_source):
        raw = m.group(1)
        # Handle ``import a, b, c`` and ``import (\n a,\n b,\n)``
        raw = raw.replace("(", "").replace(")", "")
        for tok in raw.split(","):
            name = tok.strip().split(" as ")[0].strip()
            if name and name.isidentifier():
                imported.add(name)
    return imported


# --------------------------------------------------------------------
# Frontend consumer enumeration
# --------------------------------------------------------------------


_HELPER_CALL_RE = re.compile(
    r"(authGetJSON|authPostJSON|authPatchJSON|authPutJSON|authDelete|authPostForm)"
    # TS generic type parameter may contain nested angle brackets
    # (e.g. ``authGetJSON<ListResponse<AdminLead>>``); match anything
    # up to the opening ``(`` on a best-effort basis.
    r"(?:<[^(]*?>)?"
    r"\(\s*(`[^`]*`|\"[^\"]*\"|'[^']*')",
    re.MULTILINE | re.DOTALL,
)

# Base-path helper definitions in ``api.ts`` — small utility functions
# that return a URL prefix. We regex them out and substitute their
# returned values into template literals so cross-reference works.
_BASE_PATH_HELPER_RE = re.compile(
    r"function\s+(_[A-Za-z][\w]*)\s*\([^)]*\)\s*:\s*string\s*\{"
    r"[^}]*?return\s+(`[^`]*`|\"[^\"]*\"|'[^']*')\s*;?\s*\}",
    re.MULTILINE | re.DOTALL,
)

_PUBLIC_FETCH_RE = re.compile(
    r"fetch\(\s*(`[^`]*`|\"[^\"]*\"|'[^']*')",
    re.MULTILINE | re.DOTALL,
)


def _build_base_path_map(api_source: str) -> dict[str, str]:
    """Extract ``function _xxx(...): string { return "..."; }`` helpers
    and map ``_xxx`` to the string body (with any inner ``${...}``
    collapsed to ``{PARAM}``)."""
    out: dict[str, str] = {}
    for m in _BASE_PATH_HELPER_RE.finditer(api_source):
        name = m.group(1)
        raw = m.group(2)
        # Trim wrapping quotes / backticks
        if raw and raw[0] in "\"'`":
            raw = raw[1:]
        if raw and raw[-1] in "\"'`":
            raw = raw[:-1]
        # Collapse any inner ${...} to {PARAM}
        raw = _TS_TEMPLATE_RE.sub("{PARAM}", raw)
        out[name] = raw
    return out


def _expand_helper_calls(url_expr: str, base_paths: dict[str, str]) -> str:
    """Replace ``${_helper(arg)}`` occurrences in a template literal
    with the helper's returned string, so URL normalization has
    something to match against."""
    if "${" not in url_expr:
        return url_expr

    def _sub(match: re.Match[str]) -> str:
        inside = match.group(0)[2:-1]  # strip ``${`` and ``}``
        helper_match = re.match(r"([A-Za-z_][\w]*)\s*\(", inside)
        if helper_match and helper_match.group(1) in base_paths:
            return base_paths[helper_match.group(1)]
        return "{PARAM}"

    return _TS_TEMPLATE_RE.sub(_sub, url_expr)


_EXPORT_FUNCTION_RE = re.compile(
    r"^export\s+(?:async\s+)?function\s+([a-zA-Z_][\w]*)\s*[<(]",
    re.MULTILINE,
)


def _wrapper_owning_line(api_source: str, line_no: int) -> str:
    """Return the exported wrapper function that owns the given line.
    The wrapper's ``export function name(...)`` header must appear
    before ``line_no``; the next such header ends the wrapper."""
    positions: list[tuple[int, str]] = []
    lines = api_source.split("\n")
    for m in _EXPORT_FUNCTION_RE.finditer(api_source):
        # Convert byte offset to line number.
        pre = api_source[: m.start()].count("\n") + 1
        positions.append((pre, m.group(1)))
    owner = ""
    for pos, name in positions:
        if pos <= line_no:
            owner = name
        else:
            break
    # Suppress underscored helpers — they're not the operator-visible
    # entry point.
    if owner.startswith("_"):
        return ""
    _ = lines  # ``lines`` currently unused — kept for future context
    return owner


def extract_frontend_consumers(api_source: str) -> list[FrontendConsumer]:
    base_paths = _build_base_path_map(api_source)
    consumers: list[FrontendConsumer] = []
    for m in _HELPER_CALL_RE.finditer(api_source):
        helper = m.group(1)
        raw_url_expr = m.group(2)
        expanded = _expand_helper_calls(raw_url_expr, base_paths)
        source_line = api_source[: m.start()].count("\n") + 1
        wrapper = _wrapper_owning_line(api_source, source_line)
        consumers.append(
            FrontendConsumer(
                helper=helper,
                url_expr=raw_url_expr,
                normalized_pattern=normalize_frontend(expanded),
                source_line=source_line,
                wrapper_name=wrapper,
                # Optimistic default — overridden in main() by the
                # component-consumption check.
                component_consumed=True,
            )
        )
    # Public endpoints via plain fetch — only capture those hitting the
    # dealer-ai API surface (not arbitrary external URLs).
    for m in _PUBLIC_FETCH_RE.finditer(api_source):
        url_expr = m.group(1)
        normalized = normalize_frontend(url_expr)
        if not normalized.startswith("/api/dealer-ai/") and not normalized.startswith("/"):
            continue
        # Filter obvious non-API paths
        if "/api/dealer-ai/" not in url_expr and "${API_BASE}" not in url_expr and "API_BASE" not in url_expr:
            continue
        source_line = api_source[: m.start()].count("\n") + 1
        consumers.append(
            FrontendConsumer(
                helper="fetch",
                url_expr=url_expr,
                normalized_pattern=normalized,
                source_line=source_line,
            )
        )
    return consumers


# --------------------------------------------------------------------
# Cross-reference
# --------------------------------------------------------------------


def cross_reference(
    endpoints: list[BackendEndpoint],
    consumers: list[FrontendConsumer],
    verbs_imported_by_view_module: dict[str, set[str]],
) -> list[AuditRow]:
    # Bucket consumers by normalized pattern so a single lookup is O(1).
    by_pattern: dict[str, list[FrontendConsumer]] = {}
    for c in consumers:
        by_pattern.setdefault(c.normalized_pattern, []).append(c)

    rows: list[AuditRow] = []
    for ep in endpoints:
        # Frontend match on the pattern with the "/api/dealer-ai" prefix
        # OR without it (helpers vary by whether API_BASE is prefixed).
        # Also match a trailing ``{PARAM}/`` variant — some helpers
        # append a query-string suffix through ``${qs ? ...}`` which
        # our normalizer collapses to ``{PARAM}``.
        candidate_patterns: set[str] = {
            ep.normalized_pattern,
            "/api/dealer-ai" + ep.normalized_pattern,
            ep.normalized_pattern + "{PARAM}/",
            "/api/dealer-ai" + ep.normalized_pattern + "{PARAM}/",
        }
        candidates: list[FrontendConsumer] = []
        for candidate_pattern in candidate_patterns:
            candidates.extend(by_pattern.get(candidate_pattern, []))
        # De-duplicate by (helper, source_line)
        seen: set[tuple[str, int]] = set()
        unique: list[FrontendConsumer] = []
        for c in candidates:
            key = (c.helper, c.source_line)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        # Which service verbs does the owning view module import?
        view_module = ep.view_callable.rsplit(".", 1)[0]
        imported_verbs = verbs_imported_by_view_module.get(view_module, set())
        rows.append(
            AuditRow(
                url_pattern=ep.url_pattern,
                normalized_pattern=ep.normalized_pattern,
                view_callable=ep.view_callable,
                url_name=ep.url_name,
                frontend_consumers=unique,
                service_verbs_imported=sorted(imported_verbs),
            )
        )
    return rows


# --------------------------------------------------------------------
# Markdown emission
# --------------------------------------------------------------------


DISPOSITION_LEGEND = """
**Disposition legend.**

- `M21-anchor` — pre-committed M21 scope (BHPH writes, be-back writes);
  confirmed by audit.
- `M21-conditional` — audit-surfaced item recommended for M21.4
  conditional scope.
- `defer-candidate-O2` — future OSC-shaped milestone (M22+); explicit
  re-entry path preserved.
- `defer-domain-milestone` — belongs in a distinct domain milestone
  (e.g. accounting reversal → Candidate A for M22); explicit re-entry
  path preserved.
- `intentional-omission` — capability is internal / not meant to be
  user-facing (auth flows, health checks, demo reset, etc.); documented
  why.
- `covered` — endpoint IS consumed by the frontend; included for
  audit completeness / regression detection.
"""


def recommend_disposition(row: AuditRow) -> str:
    """Heuristic disposition assignment. Human-reviewed at scope-lock."""
    if not row.is_backend_only:
        return "covered"

    name = row.url_name.lower()

    # Intentional omissions — auth, healthcheck-style, demo utilities,
    # webhook receivers, upload-request handshakes.
    intentional_hints = (
        "auth-login", "auth-logout", "auth-me",
        "demo-reset", "demo-load-scenarios",
        "photo-request-upload", "photo-local-upload",
    )
    if any(h in name for h in intentional_hints):
        return "intentional-omission"

    # M21 anchor 1 — BHPH write path.
    bhph_write_hints = (
        "bhph-promise",  # create, mark-kept, mark-broken
        "collection-contact",  # create + list
        "repossession",  # create, mark-recovered, mark-re-intaked
    )
    if any(h in name for h in bhph_write_hints) and (
        "create" in name or "mark-" in name
    ):
        return "M21-anchor"

    # M21 anchor 2 — be-back write path. Only the record-be-back
    # (POST /admin/be-backs/) verb is missing at the component level
    # (mark-returned + mark-no-show ship via DealerAiSalesBeBacks.tsx).
    if name == "admin-be-back-create":
        return "M21-anchor"
    be_back_write_hints = (
        "be-back-mark",  # transitions if audit still surfaces them
    )
    if any(h in name for h in be_back_write_hints):
        return "M21-anchor"

    # M21 conditional — follow-up cadence config mutations. Cadence
    # create + pause helpers exist in salesApi.ts but no component
    # consumes them; queue-side helpers (list/complete/skip) ARE
    # consumed by DealerAiSalesFollowUps.tsx and land as ``covered``.
    if "follow-up-cadence" in name:
        return "M21-conditional"

    # Domain milestones — accounting reversal / reopen etc.
    if "journal-entry-reverse" in name or "trial-balance-snapshot" in name:
        return "defer-domain-milestone"

    # Defer generic OSC candidates for future OSC-shaped milestones.
    return "defer-candidate-O2"


def emit_markdown(
    rows: list[AuditRow],
    verbs: list[ServiceVerb],
    verbs_imported_by_view_module: dict[str, set[str]],
) -> str:
    total = len(rows)
    covered = sum(1 for r in rows if not r.is_backend_only)
    backend_only = total - covered
    wrapper_only = sum(1 for r in rows if r.is_wrapper_only)

    lines: list[str] = []
    lines.append("---")
    lines.append("title: \"M21 Operational Surface Audit\"")
    lines.append("status: active")
    lines.append("type: audit-artifact")
    lines.append("generated: 2026-08-03")
    lines.append("generated_at_session: SESSION_167")
    lines.append("milestone: 21")
    lines.append("increment: 1")
    lines.append("sources:")
    lines.append("  - backend/dealer_ai/urls.py")
    lines.append("  - backend/dealer_ai/services/**/*.py")
    lines.append("  - frontend/src/lib/api.ts")
    lines.append("---")
    lines.append("")
    lines.append("# M21 Operational Surface Audit")
    lines.append("")
    lines.append(
        "> Generated by "
        "`backend/dealer_ai/scripts/audit_operational_surface.py` per "
        "MILESTONE_21_PLANNING.md §5.b Option C (combined service-verb + "
        "DRF-endpoint enumeration cross-referenced against frontend "
        "consumption). Schema per §5.c Option A. Dispositions per §5.c "
        "legend below."
    )
    lines.append("")
    lines.append("## Coverage summary")
    lines.append("")
    lines.append(f"- **Backend endpoints enumerated:** {total}")
    lines.append(
        f"- **Consumed by frontend components (`covered`):** {covered}"
    )
    lines.append(f"- **Backend-only (audit findings):** {backend_only}")
    lines.append(
        f"  - Of which **`wrapper-only`** (typed helper exists in an "
        f"`*Api.ts` module but no component imports it — the endpoint is "
        f"reachable in principle but not through the operator UI): "
        f"**{wrapper_only}**"
    )
    lines.append(f"- **Service verbs enumerated:** {len(verbs)}")
    lines.append(
        "- **Distinct view modules importing service verbs:** "
        f"{sum(1 for v in verbs_imported_by_view_module.values() if v)}"
    )
    lines.append("")
    lines.append(DISPOSITION_LEGEND.strip())
    lines.append("")
    lines.append("## Full endpoint table")
    lines.append("")
    lines.append(
        "One row per DRF endpoint. `Frontend consumers` counts calls in "
        "`frontend/src/lib/api.ts`. `Service verbs (view imports)` lists "
        "the service verbs the owning view module imports — signal for "
        "which underlying capability is affected."
    )
    lines.append("")
    lines.append(
        "| # | URL pattern | View callable | url_name | Frontend consumers | Recommended disposition |"
    )
    lines.append(
        "| --: | --- | --- | --- | :--: | --- |"
    )
    for i, row in enumerate(rows, start=1):
        consumer_parts: list[str] = []
        for c in row.frontend_consumers:
            location = c.url_expr.split(" ", 1)[0]
            wrapper_tag = f" `{c.wrapper_name}`" if c.wrapper_name else ""
            unused_tag = "" if c.component_consumed else " ⚠ wrapper-only"
            consumer_parts.append(f"{location}{wrapper_tag}{unused_tag}")
        consumers_col = ", ".join(consumer_parts) or "—"
        disposition = recommend_disposition(row)
        lines.append(
            f"| {i} | `{row.url_pattern}` | `{row.view_callable}` | "
            f"`{row.url_name}` | {consumers_col} | `{disposition}` |"
        )
    lines.append("")

    # Backend-only findings section — the actionable output.
    findings = [r for r in rows if r.is_backend_only]
    lines.append("## Backend-only findings")
    lines.append("")
    lines.append(
        f"**{len(findings)} endpoints ship without frontend consumption.** "
        "Each row is a capability that dealership staff cannot reach "
        "through the product today. Group by recommended disposition:"
    )
    lines.append("")
    by_disposition: dict[str, list[AuditRow]] = {}
    for r in findings:
        by_disposition.setdefault(recommend_disposition(r), []).append(r)
    for disposition in (
        "M21-anchor",
        "M21-conditional",
        "defer-candidate-O2",
        "defer-domain-milestone",
        "intentional-omission",
    ):
        bucket = by_disposition.get(disposition, [])
        lines.append(f"### {disposition} ({len(bucket)})")
        lines.append("")
        if not bucket:
            lines.append("_None._")
            lines.append("")
            continue
        for r in bucket:
            verbs_col = ", ".join(f"`{v}`" for v in r.service_verbs_imported) or "—"
            lines.append(
                f"- `{r.url_pattern}` → `{r.view_callable}` "
                f"(`{r.url_name}`). Imported service verbs: {verbs_col}"
            )
        lines.append("")

    # Per-domain narrative sections — automatically derived from the
    # ``view_module`` grouping.
    lines.append("## Per-domain narrative sections")
    lines.append("")
    by_module: dict[str, list[AuditRow]] = {}
    for r in rows:
        module = r.view_callable.rsplit(".", 1)[0]
        by_module.setdefault(module, []).append(r)
    for module in sorted(by_module):
        module_rows = by_module[module]
        module_backend_only = [r for r in module_rows if r.is_backend_only]
        lines.append(f"### {module}")
        lines.append("")
        lines.append(
            f"- **Endpoints:** {len(module_rows)}"
        )
        lines.append(
            f"- **Backend-only:** {len(module_backend_only)}"
        )
        if module_backend_only:
            dispositions_seen = sorted({recommend_disposition(r) for r in module_backend_only})
            lines.append(
                "- **Backend-only dispositions in this module:** "
                + ", ".join(f"`{d}`" for d in dispositions_seen)
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "**Regeneration.** Rerun `python3 -m dealer_ai.scripts.audit_operational_surface` "
        "from the `backend/` directory to refresh this artifact after new endpoints or "
        "frontend consumers ship. Human review of disposition assignments is required "
        "each rerun — the recommender is a heuristic, not a source of truth."
    )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------
# CLI entrypoint
# --------------------------------------------------------------------


def _default_repo_root() -> Path:
    here = Path(__file__).resolve()
    # backend/dealer_ai/scripts/audit_operational_surface.py
    return here.parent.parent.parent.parent


def _view_module_verb_imports(
    dealer_ai_root: Path,
) -> dict[str, set[str]]:
    """Walk ``views*.py`` and record which service verbs each imports.
    Key format: ``views_bhph_notes`` etc."""
    out: dict[str, set[str]] = {}
    for path in sorted(dealer_ai_root.glob("views*.py")):
        module = path.stem
        source = path.read_text()
        out[module] = view_imported_verbs(source)
    # Also handle ``views`` package if it exists (currently a plain
    # ``views.py`` file, but future refactor may split).
    return out


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_default_repo_root(),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md"),
        help="Output markdown path (relative to --repo-root).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root: Path = args.repo_root.resolve()
    urls_path = repo_root / "backend" / "dealer_ai" / "urls.py"
    services_root = repo_root / "backend" / "dealer_ai" / "services"
    frontend_lib_root = repo_root / "frontend" / "src" / "lib"
    dealer_ai_root = repo_root / "backend" / "dealer_ai"

    urls_source = urls_path.read_text()

    endpoints = extract_backend_endpoints(urls_source)
    verbs = extract_service_verbs(services_root)
    # Walk every ``*Api.ts`` / ``api.ts`` file under ``frontend/src/lib/``
    # — the frontend split its API-consumer surface across several
    # modules (api.ts, bhphApi.ts, fAndIApi.ts, accountingApi.ts,
    # analyticsApi.ts, salesApi.ts, saleApi.ts).
    api_files = sorted(
        list(frontend_lib_root.glob("api.ts")) + list(frontend_lib_root.glob("*Api.ts"))
    )
    # Build the set of exported wrapper names actually referenced by
    # non-test components anywhere under frontend/src/. A wrapper that
    # nobody imports is a dead wrapper — the endpoint is unreachable
    # from the operator's perspective even though its typed helper
    # exists.
    frontend_src = repo_root / "frontend" / "src"
    all_component_text_parts: list[str] = []
    for tsx in frontend_src.rglob("*.tsx"):
        if tsx.name.endswith(".test.tsx"):
            continue
        try:
            all_component_text_parts.append(tsx.read_text())
        except UnicodeDecodeError:
            continue
    for ts in frontend_src.rglob("*.ts"):
        # Skip the API wrappers themselves and test files.
        if ts.parent == frontend_lib_root and (
            ts.name == "api.ts" or ts.name.endswith("Api.ts")
        ):
            continue
        if ts.name.endswith(".test.ts"):
            continue
        try:
            all_component_text_parts.append(ts.read_text())
        except UnicodeDecodeError:
            continue
    combined_component_text = "\n".join(all_component_text_parts)

    consumers: list[FrontendConsumer] = []
    for api_file in api_files:
        source = api_file.read_text()
        for c in extract_frontend_consumers(source):
            # Check whether the wrapper is consumed by any component /
            # non-API module. Use a word-boundary regex so
            # ``createBeBack`` doesn't match ``createBeBackReturned``.
            component_consumed = True
            if c.wrapper_name:
                pattern = re.compile(r"\b" + re.escape(c.wrapper_name) + r"\b")
                component_consumed = bool(pattern.search(combined_component_text))
            consumers.append(
                FrontendConsumer(
                    helper=c.helper,
                    url_expr=f"{api_file.name}:{c.source_line} {c.url_expr}",
                    normalized_pattern=c.normalized_pattern,
                    source_line=c.source_line,
                    wrapper_name=c.wrapper_name,
                    component_consumed=component_consumed,
                )
            )
    verbs_imported_by_view_module = _view_module_verb_imports(dealer_ai_root)

    rows = cross_reference(endpoints, consumers, verbs_imported_by_view_module)
    markdown = emit_markdown(rows, verbs, verbs_imported_by_view_module)

    out_path = repo_root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown)

    # Summary to stdout for interactive runs.
    total = len(rows)
    covered = sum(1 for r in rows if not r.is_backend_only)
    backend_only = total - covered
    print(f"Backend endpoints: {total}")
    print(f"Covered: {covered}")
    print(f"Backend-only: {backend_only}")
    print(f"Service verbs enumerated: {len(verbs)}")
    print(f"Artifact written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
