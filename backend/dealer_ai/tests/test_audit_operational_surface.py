"""M26.1 regression suite for the operational-surface audit script's
frontend-consumer tokenizer.

Guards the nested-template-literal + optional-querystring parser fix
(§5.b) against regression, and documents the row-5
public-`getJSON`-helper gap deferred to M27+ (§3).

Test structure per MILESTONE_26_PLANNING.md §5.c (refined at
SESSION_190 §2):

- **5 positive cases** — one per confirmed nested-template-literal
  false positive from SESSION_189 §3 tracing (rows 7, 16, 29, 111,
  121). Each asserts the tokenizer captures the full expression and
  ``normalize_frontend`` produces the correct ``/path/{PARAM}/``
  shape.

- **7 negative cases** — guard against over-classification and
  preserve the M22.1 §5.e identifier-lookback + M23.1 §5.d verb-filter
  substrates plus the M26.1-scope-boundary
  (``fetchVehicleDetail`` remains invisible until a separate
  public-`getJSON` fix ships).

No Django test-DB usage — pure unit tests over the script's public
functions.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from dealer_ai.scripts.audit_operational_surface import (
    _extract_balanced_template_literal,
    _HELPER_TO_VERB,
    extract_frontend_consumers,
)


def _wrap(url_expr: str, wrapper_name: str = "wrapExample") -> str:
    """Minimal api.ts-shape source containing a single wrapper function
    that calls ``authGetJSON`` with the given url expression. Mirrors
    the shape ``_wrapper_owning_line`` expects (an ``export function``
    header preceding the helper call)."""
    return (
        f"export function {wrapper_name}() {{\n"
        f"  return authGetJSON<Any>(\n"
        f"    {url_expr},\n"
        f"  );\n"
        f"}}\n"
    )


class NestedTemplateLiteralPositiveCases(SimpleTestCase):
    """5 positive cases — one per confirmed nested-template-literal
    false positive from SESSION_189 §3 tracing (rows 7, 16, 29, 111,
    121). Each asserts the tokenizer captures the full expression and
    normalize_frontend produces the correct pattern.
    """

    def _assert_captured(
        self,
        url_expr: str,
        wrapper_name: str,
        expected_normalized: str,
    ) -> None:
        source = _wrap(url_expr, wrapper_name)
        consumers = extract_frontend_consumers(source)
        matches = [c for c in consumers if c.wrapper_name == wrapper_name]
        self.assertEqual(
            len(matches),
            1,
            f"expected exactly one consumer for {wrapper_name}, got {matches}",
        )
        c = matches[0]
        self.assertEqual(c.helper, "authGetJSON")
        self.assertEqual(c.normalized_pattern, expected_normalized)
        # The captured url_expr must end with the closing backtick —
        # not with the inner-template terminator that the fast-path
        # regex would produce pre-fix.
        self.assertTrue(
            c.url_expr.endswith("`"),
            f"url_expr should end with backtick, got {c.url_expr!r}",
        )

    def test_row_7_admin_leads(self):
        """Row 7 — `fetchAdminLeads` in api.ts:284 (M11)."""
        self._assert_captured(
            "`/admin/leads/${qs ? `?${qs}` : \"\"}`",
            "fetchAdminLeads",
            "/admin/leads/{PARAM}/",
        )

    def test_row_16_admin_audit_events(self):
        """Row 16 — `fetchAuditEvents` in api.ts:341 (M11-era)."""
        self._assert_captured(
            "`/admin/audit-events/${qs ? `?${qs}` : \"\"}`",
            "fetchAuditEvents",
            "/admin/audit-events/{PARAM}/",
        )

    def test_row_29_admin_vehicles(self):
        """Row 29 — `listAdminVehicles` in salesApi.ts:257 (M25.2)."""
        self._assert_captured(
            "`/admin/vehicles/${qs ? `?${qs}` : \"\"}`",
            "listAdminVehicles",
            "/admin/vehicles/{PARAM}/",
        )

    def test_row_111_admin_test_drives_list(self):
        """Row 111 — `listTestDrives` in salesApi.ts:204 (M11.6)."""
        self._assert_captured(
            "`/admin/test-drives/list/${qs ? `?${qs}` : \"\"}`",
            "listTestDrives",
            "/admin/test-drives/list/{PARAM}/",
        )

    def test_row_121_admin_be_backs_list(self):
        """Row 121 — `listBeBacks` in salesApi.ts:425 (M11)."""
        self._assert_captured(
            "`/admin/be-backs/list/${qs ? `?${qs}` : \"\"}`",
            "listBeBacks",
            "/admin/be-backs/list/{PARAM}/",
        )


class TokenizerNegativeCases(SimpleTestCase):
    """7 negative cases — guard against over-classification and
    preserve M22.1 §5.e + M23.1 §5.d substrates plus M26.1 scope
    boundary.
    """

    def test_negative_1_fixed_query_string(self):
        """A wrapper URL with a legitimate `?` in a query-string
        position but no template nesting — normalize_frontend must
        strip the query string, not include it in the pattern.
        """
        source = _wrap(
            "`/some/path/?fixed=1`",
            "queryStringWrapper",
        )
        consumers = extract_frontend_consumers(source)
        matches = [c for c in consumers if c.wrapper_name == "queryStringWrapper"]
        self.assertEqual(len(matches), 1)
        # normalize_frontend strips query strings — pattern is
        # /some/path/ (no trailing ?fixed=1).
        self.assertEqual(matches[0].normalized_pattern, "/some/path/")

    def test_negative_2_nonexistent_endpoint(self):
        """A wrapper for a path that no backend endpoint matches —
        parser still captures the wrapper (its job); cross-reference
        would produce no match downstream. Guards against the fix
        manufacturing false coverage.
        """
        source = _wrap(
            "`/totally/fake/endpoint/${qs ? `?${qs}` : \"\"}`",
            "fakeEndpointWrapper",
        )
        consumers = extract_frontend_consumers(source)
        matches = [c for c in consumers if c.wrapper_name == "fakeEndpointWrapper"]
        self.assertEqual(len(matches), 1)
        # Pattern normalizes correctly — cross_reference in the audit
        # driver would find no endpoint to match against, so the
        # wrapper does not manufacture false coverage.
        self.assertEqual(
            matches[0].normalized_pattern,
            "/totally/fake/endpoint/{PARAM}/",
        )

    def test_negative_3_fast_path_unchanged(self):
        """Fast-path wrapper (plain single `${var}`, no nested
        template) — post-match refinement must NOT fire because
        ``${`` count equals ``}`` count. Guards against silent
        rewrite of already-correct fast-path output.
        """
        source = _wrap(
            "`/admin/things/${stockNumber}/`",
            "fastPathWrapper",
        )
        consumers = extract_frontend_consumers(source)
        matches = [c for c in consumers if c.wrapper_name == "fastPathWrapper"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].normalized_pattern, "/admin/things/{PARAM}/")
        # url_expr must be the full literal (starts and ends with
        # backtick) — same shape whether the refinement fires or not.
        self.assertTrue(matches[0].url_expr.startswith("`"))
        self.assertTrue(matches[0].url_expr.endswith("`"))

    def test_negative_4_identifier_lookback_preserved(self):
        """M22.1 §5.e substrate — identifier-passed URL. The wrapper
        assigns its URL to `const path = ...` and passes `path` (a
        bare identifier) to authGetJSON. The parser fix must not
        break the identifier-lookback path in
        ``_resolve_variable_url``.
        """
        source = (
            "export function identifierWrapper() {\n"
            "  const path = `/admin/things/${id}/details/`;\n"
            "  return authGetJSON<Any>(path);\n"
            "}\n"
        )
        consumers = extract_frontend_consumers(source)
        matches = [c for c in consumers if c.wrapper_name == "identifierWrapper"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            matches[0].normalized_pattern,
            "/admin/things/{PARAM}/details/",
        )

    def test_negative_5_verb_filter_substrate_preserved(self):
        """M23.1 §5.d substrate — helper-to-verb mapping preserved.
        The GET helpers (`authGetJSON`) resolve to GET; the POST
        helper (`authPostJSON`) resolves to POST. cross_reference
        downstream uses this to filter false-positive coverage
        claims where a GET wrapper URL prefix-matches a POST
        endpoint.
        """
        self.assertEqual(_HELPER_TO_VERB["authGetJSON"], "GET")
        self.assertEqual(_HELPER_TO_VERB["authPostJSON"], "POST")
        self.assertEqual(_HELPER_TO_VERB["authPatchJSON"], "PATCH")
        self.assertEqual(_HELPER_TO_VERB["authPutJSON"], "PUT")
        self.assertEqual(_HELPER_TO_VERB["authDelete"], "DELETE")
        self.assertEqual(_HELPER_TO_VERB["authPostForm"], "POST")

    def test_negative_6_malformed_template_no_hang(self):
        """A malformed / unterminated template literal (opens with
        backtick but never closes before EOF). The tokenizer must
        terminate without hang, returning the partial capture and
        end position equal to source length.
        """
        source = "`/admin/incomplete/${qs"
        # Direct invocation of the shared substrate — the helper
        # returns (partial, len(source)) without raising or hanging.
        lit, end = _extract_balanced_template_literal(source, 0)
        self.assertEqual(end, len(source))
        # Partial capture — does not end with a closing backtick.
        self.assertEqual(lit, source)
        self.assertFalse(lit.endswith("`"))

    def test_negative_7_public_get_json_still_invisible(self):
        """M26.1 §5.b + §3 scope boundary — `fetchVehicleDetail` at
        api.ts:626 uses the public `getJSON` helper, which is not
        enumerated in ``_HELPER_CALL_RE`` (matches only
        ``authGetJSON`` / ``authPostJSON`` etc.). The M26 parser fix
        addresses ONLY the nested-template-literal defect; the
        public-fetch-helper regex gap is a separate defect deferred
        to M27+ per MILESTONE_26_PLANNING.md §3 (row 5
        `vehicles/<int:vehicle_id>/`).

        Asserts that even after the fix, a wrapper calling
        ``getJSON(\\`/vehicles/${id}/${qs ? \\`?${qs}\\` : ""}\\`)``
        produces zero consumers — its coverage claim is intentionally
        NOT recognized until the M27+ scope opens.
        """
        source = (
            "export function fetchVehicleDetailLike() {\n"
            "  return getJSON<Any>(\n"
            "    `/vehicles/${vehicleId}/${qs ? `?${qs}` : \"\"}`,\n"
            "  );\n"
            "}\n"
        )
        consumers = extract_frontend_consumers(source)
        matches = [c for c in consumers if c.wrapper_name == "fetchVehicleDetailLike"]
        self.assertEqual(
            len(matches),
            0,
            "getJSON is intentionally not enumerated in _HELPER_CALL_RE "
            "until the M27+ public-fetch-helper refinement ships",
        )
