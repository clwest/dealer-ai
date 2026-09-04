"""Read-only health endpoints.

``health_version`` returns the git identity this process booted with. The
values come from ``services.build_identity.BUILD_IDENTITY``, which was
captured at import time — this handler MUST NOT recompute the SHA. A
per-request ``git rev-parse HEAD`` would report the current working tree
and defeat the whole point of the check (the server would answer with a
commit it is not actually serving).
"""

from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .services.build_identity import BUILD_IDENTITY


@api_view(["GET"])
@permission_classes([AllowAny])
def health_version(_request):
    return Response(BUILD_IDENTITY)
