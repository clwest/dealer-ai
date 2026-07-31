from django.conf import settings


def _frame_ancestors() -> str:
    origins = ["'self'", *settings.DEALER_AI_EMBED_ALLOWED_ORIGINS]
    return " ".join(dict.fromkeys(origin for origin in origins if origin))


class EmbedFramePolicyMiddleware:
    """Scope iframe policy to the public assistant embed path.

    Django may not serve the SPA in every deployment, but when it does,
    this removes the global X-Frame-Options blocker for the embed route
    and replaces it with a CSP frame-ancestors allowlist.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.rstrip("/") == "/embed/assistant":
            response.headers.pop("X-Frame-Options", None)
            response.headers["Content-Security-Policy"] = (
                f"frame-ancestors {_frame_ancestors()}"
            )
        return response
