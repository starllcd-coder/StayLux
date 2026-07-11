from __future__ import annotations

import os
from fnmatch import fnmatch

from django.http import HttpResponse


class SimpleCORSMiddleware:
    """
    Lightweight CORS middleware for local mobile/web app development.
    No external dependency required.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.allow_all = os.environ.get("STAYLUX_CORS_ALLOW_ALL", "1") == "1"
        raw = os.environ.get(
            "STAYLUX_CORS_ALLOWED_ORIGINS",
            "http://localhost:*,http://127.0.0.1:*",
        )
        self.allowed_patterns = [x.strip() for x in raw.split(",") if x.strip()]

    def _is_allowed_origin(self, origin: str) -> bool:
        if not origin:
            return False
        if self.allow_all:
            return True
        return any(fnmatch(origin, pattern) for pattern in self.allowed_patterns)

    def _is_api_path(self, path: str) -> bool:
        return path.startswith("/api/")

    def _apply_cors_headers(self, response, origin: str, request_headers: str = ""):
        response["Access-Control-Allow-Origin"] = origin
        response["Vary"] = "Origin"
        response["Access-Control-Allow-Credentials"] = "true"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = request_headers or "Authorization, Content-Type, Accept, Origin, X-Requested-With"
        return response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        req_headers = request.headers.get("Access-Control-Request-Headers", "")
        is_cors = bool(origin and self._is_allowed_origin(origin) and self._is_api_path(request.path))

        if is_cors and request.method == "OPTIONS":
            return self._apply_cors_headers(HttpResponse(status=204), origin, req_headers)

        response = self.get_response(request)
        if is_cors:
            response = self._apply_cors_headers(response, origin, req_headers)
        return response
