
"""
Security middleware for TigerPad.

Provides:
- Request IDs for tracing
- HTTP security headers
- Development rate limiting

The in-memory rate limiter is intended for local development.
Production deployments with multiple workers should use a
shared rate-limit service such as Redis or an API gateway.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from TP_App.config import settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a validated request identifier."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied = request.headers.get("X-Request-ID", "")

        try:
            request_id = str(UUID(supplied))
        except (ValueError, AttributeError):
            request_id = str(uuid4())

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request_id)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add defensive HTTP response headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        response.headers.setdefault(
            "X-Content-Type-Options",
            "nosniff",
        )

        response.headers.setdefault(
            "X-Frame-Options",
            "DENY",
        )

        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )

        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )

        if settings.ENVIRONMENT.lower() in {
            "production",
            "prod",
        }:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

            if (
                not request.url.path.startswith("/docs")
                and not request.url.path.startswith("/redoc")
            ):
                response.headers.setdefault(
                    "Content-Security-Policy",
                    "default-src 'self'; "
                    "base-uri 'self'; "
                    "frame-ancestors 'none'; "
                    "object-src 'none'",
                )

        if request.url.path.startswith(
            f"{settings.API_PREFIX}/auth/"
        ):
            response.headers.setdefault(
                "Cache-Control",
                "no-store",
            )

        return response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Apply development rate limits by client IP and request path.

    This implementation is process-local and should not be
    treated as distributed production rate limiting.
    """

    def __init__(
        self,
        app,
        requests: int,
        window_seconds: int,
        enabled: bool,
        auth_requests: int | None = None,
        max_keys: int | None = None,
    ) -> None:
        super().__init__(app)

        self.requests = max(1, requests)
        self.window_seconds = max(1, window_seconds)
        self.enabled = enabled
        self.auth_requests = max(
            1,
            auth_requests or requests,
        )
        self.max_keys = max(
            100,
            max_keys or 10000,
        )

        self.request_history: dict[
            tuple[str, str],
            deque[float],
        ] = defaultdict(deque)

    @staticmethod
    def _client_key(
        request: Request,
    ) -> tuple[str, str]:
        client_host = (
            request.client.host
            if request.client is not None
            else "unknown"
        )

        return client_host, request.url.path

    def _is_exempt_path(
        self,
        request: Request,
    ) -> bool:
        exempt_paths = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

        return request.url.path in exempt_paths

    def _request_limit(
        self,
        request: Request,
    ) -> int:
        if request.url.path.startswith(
            f"{settings.API_PREFIX}/auth/"
        ):
            return self.auth_requests

        return self.requests

    def _remove_expired_requests(
        self,
        timestamps: deque[float],
        now: float,
    ) -> None:
        cutoff = now - self.window_seconds

        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[
            [Request],
            Awaitable[Response],
        ],
    ) -> Response:
        if not self.enabled or self._is_exempt_path(request):
            return await call_next(request)

        now = time.monotonic()
        key = self._client_key(request)

        # Remove expired entries before allocating new keys.
        if (
            key not in self.request_history
            and len(self.request_history) >= self.max_keys
        ):
            stale_keys = [
                existing_key
                for existing_key, values
                in self.request_history.items()
                if (
                    not values
                    or values[-1]
                    <= now - self.window_seconds
                )
            ]

            for stale_key in stale_keys:
                self.request_history.pop(
                    stale_key,
                    None,
                )

            # Bound the number of tracked keys even when
            # many different clients send requests.
            if len(self.request_history) >= self.max_keys:
                oldest_key = min(
                    self.request_history,
                    key=lambda existing_key: (
                        self.request_history[existing_key][-1]
                        if self.request_history[existing_key]
                        else float("-inf")
                    ),
                )

                self.request_history.pop(
                    oldest_key,
                    None,
                )

        timestamps = self.request_history[key]

        self._remove_expired_requests(
            timestamps=timestamps,
            now=now,
        )

        if len(timestamps) >= self._request_limit(request):
            retry_after = max(
                1,
                int(
                    self.window_seconds
                    - (now - timestamps[0])
                ) + 1,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": (
                        "Too many requests. "
                        "Please wait before trying again."
                    ),
                },
                headers={
                    "Retry-After": str(retry_after),
                },
            )

        timestamps.append(now)

        return await call_next(request)


def rate_limit_is_enabled() -> bool:
    """Return whether rate limiting is enabled."""

    return bool(settings.RATE_LIMIT_ENABLED)
