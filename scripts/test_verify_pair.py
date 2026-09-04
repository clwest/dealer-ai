"""Unit tests for scripts/verify_pair.py.

The state that matters most: **404 on the version URL with a failing
liveness probe must resolve to UNREACHABLE, not NO_VERSION_ENDPOINT.**
That is the case that would let a dead server look merely old — and
letting an operator conclude "just restart" when what actually
happened is "the machine crashed" is exactly the failure the fifth
state was added to prevent.

These tests mock the two HTTP entry points (``_fetch`` for the version
URL and ``_liveness_probe`` for the liveness URL) so the tests never
touch a network. Everything below runs in one Python process, offline.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import verify_pair as vp  # noqa: E402


HEAD_SHA = "abcdef0123456789abcdef0123456789abcdef01"
OLD_SHA = "1111111111111111111111111111111111111111"


def _mk_report(label="backend", base="http://x"):
    return vp.ServerReport(
        label=label,
        version_url=base + "/version",
        liveness_url=base + "/liveness",
    )


def _probe_and_verdict(version_result, liveness_result=None, head=HEAD_SHA):
    """Drive one server through _probe_server + _verdict_for with the
    two HTTP calls stubbed. Returns (state, line)."""
    report = _mk_report()
    fetch_calls = {"n": 0}

    def fake_fetch(url, timeout=3.0):
        fetch_calls["n"] += 1
        return version_result

    def fake_liveness(url, timeout=3.0):
        return liveness_result if liveness_result is not None else (False, "not called")

    with mock.patch.object(vp, "_fetch", side_effect=fake_fetch), \
            mock.patch.object(vp, "_liveness_probe", side_effect=fake_liveness):
        vp._probe_server(report)
    with mock.patch.object(vp, "_commits_behind", return_value=1):
        return vp._verdict_for(report, head)


class TestVerifyPairStates(unittest.TestCase):
    def test_match_when_sha_equals_head(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(status=200, identity={"sha": HEAD_SHA, "dirty": False})
        )
        self.assertEqual(state, "MATCH")
        self.assertIn(HEAD_SHA[:7], line)

    def test_stale_when_sha_differs(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(status=200, identity={"sha": OLD_SHA})
        )
        self.assertEqual(state, "STALE")
        self.assertIn(OLD_SHA[:7], line)
        self.assertIn("1 commit behind", line)

    def test_unreadable_when_sha_null(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(status=200, identity={"sha": None})
        )
        self.assertEqual(state, "UNREADABLE")
        self.assertIn("sha is null", line)

    def test_unreadable_when_body_wont_parse(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(status=200, identity=None, parse_error="invalid JSON: garbage")
        )
        self.assertEqual(state, "UNREADABLE")
        self.assertIn("will not parse", line)

    def test_unreadable_carries_non_200_non_404_status(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(status=500, parse_error="HTTP 500 (expected 200)")
        )
        self.assertEqual(state, "UNREADABLE")
        self.assertIn("HTTP 500", line)

    def test_unreachable_on_connection_refused(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(conn_error="URLError: [Errno 61] Connection refused")
        )
        self.assertEqual(state, "UNREACHABLE")
        self.assertIn("Connection refused", line)

    # -- the fifth state, both branches ------------------------------------

    def test_no_version_endpoint_when_404_and_liveness_alive(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(status=404, parse_error="HTTP 404 Not Found"),
            liveness_result=(True, "HTTP 200"),
        )
        self.assertEqual(state, "NO_VERSION_ENDPOINT")
        self.assertIn("predates the check", line)
        self.assertIn("TASK_restart-servers.md", line)

    def test_404_with_failed_liveness_is_UNREACHABLE_not_no_version_endpoint(self):
        """The case that matters most. See module docstring."""
        state, line = _probe_and_verdict(
            vp.FetchResult(status=404, parse_error="HTTP 404 Not Found"),
            liveness_result=(False, "URLError: [Errno 61] Connection refused"),
        )
        self.assertEqual(state, "UNREACHABLE")
        # The message must NOT suggest "just restart" — the process
        # might be dead, and telling an operator "just restart" when
        # the machine crashed is the exact failure the fifth state was
        # added to prevent.
        self.assertNotIn("predates", line)
        self.assertIn("liveness probe", line)

    def test_liveness_alive_covers_401_and_403_and_404_and_500(self):
        """Liveness is 'process handled the request', not 'URL was
        found'. A 401/403/404/500 on the liveness URL still means the
        process is up — so a 404 on the version URL with any of these
        for liveness must still resolve to NO_VERSION_ENDPOINT, not
        UNREACHABLE."""
        for code in (401, 403, 404, 500):
            state, _line = _probe_and_verdict(
                vp.FetchResult(status=404),
                liveness_result=(True, f"HTTP {code}"),
            )
            self.assertEqual(
                state, "NO_VERSION_ENDPOINT",
                f"liveness HTTP {code} should count as alive",
            )

    # -- HEAD unreadable case ----------------------------------------------

    def test_unknown_state_when_head_sha_unreadable(self):
        state, line = _probe_and_verdict(
            vp.FetchResult(status=200, identity={"sha": HEAD_SHA}),
            head=None,
        )
        self.assertEqual(state, "UNKNOWN")
        self.assertIn("HEAD could not be read", line)


class TestFetch(unittest.TestCase):
    """Direct tests on _fetch — the shape it hands back to _verdict_for
    is the whole contract, so exercise the four exit paths."""

    def _mock_urlopen(self, body, status=200):
        m = mock.MagicMock()
        m.__enter__ = mock.MagicMock(return_value=m)
        m.__exit__ = mock.MagicMock(return_value=False)
        m.status = status
        m.read = mock.MagicMock(return_value=body.encode("utf-8"))
        return m

    def test_fetch_returns_identity_on_200_valid_json(self):
        payload = {"sha": HEAD_SHA, "dirty": False, "pid": 42}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_urlopen(json.dumps(payload))):
            r = vp._fetch("http://x/version")
        self.assertEqual(r.status, 200)
        self.assertEqual(r.identity, payload)
        self.assertIsNone(r.parse_error)
        self.assertIsNone(r.conn_error)

    def test_fetch_records_404_status_from_HTTPError(self):
        err = urllib.error.HTTPError(
            "http://x/version", 404, "Not Found", hdrs=None, fp=io.BytesIO(b""),
        )
        with mock.patch("urllib.request.urlopen", side_effect=err):
            r = vp._fetch("http://x/version")
        # Key property: status is 404 (not None), so _verdict_for can
        # tell "404" apart from "connection refused".
        self.assertEqual(r.status, 404)
        self.assertIsNone(r.conn_error)
        self.assertIsNone(r.identity)

    def test_fetch_records_conn_error_and_leaves_status_None(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            r = vp._fetch("http://x/version")
        self.assertIsNone(r.status)
        self.assertIsNotNone(r.conn_error)
        self.assertIn("URLError", r.conn_error)

    def test_fetch_records_parse_error_when_body_isnt_json(self):
        with mock.patch("urllib.request.urlopen", return_value=self._mock_urlopen("not json")):
            r = vp._fetch("http://x/version")
        self.assertEqual(r.status, 200)
        self.assertIsNone(r.identity)
        self.assertIn("invalid JSON", r.parse_error)


class TestProbeServerLivenessGating(unittest.TestCase):
    """Only the 404 branch should call the liveness probe. On MATCH /
    STALE / UNREACHABLE / UNREADABLE-other paths the checker must NOT
    make an extra HTTP call — it wastes time in the healthy case and
    would hide problems in the error cases."""

    def _probe(self, version_result):
        report = _mk_report()
        with mock.patch.object(vp, "_fetch", return_value=version_result), \
                mock.patch.object(
                    vp, "_liveness_probe", return_value=(True, "HTTP 200")
                ) as m_liveness:
            vp._probe_server(report)
            return report, m_liveness

    def test_liveness_not_called_on_200(self):
        _r, m = self._probe(vp.FetchResult(status=200, identity={"sha": HEAD_SHA}))
        m.assert_not_called()

    def test_liveness_not_called_on_connection_refused(self):
        _r, m = self._probe(vp.FetchResult(conn_error="refused"))
        m.assert_not_called()

    def test_liveness_not_called_on_500(self):
        _r, m = self._probe(vp.FetchResult(status=500))
        m.assert_not_called()

    def test_liveness_IS_called_on_404(self):
        _r, m = self._probe(vp.FetchResult(status=404))
        m.assert_called_once()


if __name__ == "__main__":
    unittest.main()
