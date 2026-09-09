"""In-memory token-bucket rate limiter middleware.

Protects the whole API against abuse with a simple per-IP sliding window.
Suitable for an academic demo; use Redis in production.
"""
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, per_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.hits: dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.per_seconds
        key = f"{client}:{request.url.path}"
        self.hits[key] = [t for t in self.hits[key] if t > window_start]
        if len(self.hits[key]) >= self.max_requests:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again later."}, status_code=429
            )
        self.hits[key].append(now)
        return await call_next(request)