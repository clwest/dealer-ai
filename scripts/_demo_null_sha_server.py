"""Tiny HTTP server for the verify_pair.py UNREADABLE demonstration.

Serves ``/api/dealer-ai/health/version/`` and ``/__version`` with an
identity payload whose ``sha`` is ``null`` — proving the checker treats
"answered but cannot say what it is" as its own state, never as MATCH.

Delete after the demonstration. Not imported by anything.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


PAYLOAD = json.dumps({
    "sha": None,
    "sha_short": None,
    "branch": None,
    "dirty": None,
    "booted_at": "2026-09-04T23:00:00Z",
    "pid": 0,
}).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 — stdlib naming
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, *_args):  # silence per-request stderr chatter
        return


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8103
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
