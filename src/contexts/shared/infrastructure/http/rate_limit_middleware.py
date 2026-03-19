import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, client_id: str) -> None:
        cutoff = time.time() - self._window_seconds
        self._timestamps[client_id] = [
            ts for ts in self._timestamps[client_id] if ts > cutoff
        ]
        if not self._timestamps[client_id]:
            del self._timestamps[client_id]

    def is_allowed(self, client_id: str) -> bool:
        self._cleanup(client_id)
        if len(self._timestamps[client_id]) < self._max_requests:
            self._timestamps[client_id].append(time.time())
            return True
        return False

    def remaining(self, client_id: str) -> int:
        self._cleanup(client_id)
        return max(0, self._max_requests - len(self._timestamps.get(client_id, [])))

    def reset_time(self, client_id: str) -> float:
        self._cleanup(client_id)
        timestamps = self._timestamps.get(client_id, [])
        if not timestamps:
            return time.time() + self._window_seconds
        return timestamps[0] + self._window_seconds


def create_rate_limit_middleware(
    max_requests: int,
    window_seconds: float,
    exclude_paths: list[str],
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    limiter = SlidingWindowRateLimiter(
        max_requests=max_requests,
        window_seconds=window_seconds,
    )

    async def middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in exclude_paths:
            return await call_next(request)

        client_id = request.client.host if request.client else "unknown"

        if not limiter.is_allowed(client_id):
            reset = limiter.reset_time(client_id)
            retry_after = max(0, int(reset - time.time()))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset)),
                },
            )

        response = await call_next(request)
        reset = limiter.reset_time(client_id)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(limiter.remaining(client_id))
        response.headers["X-RateLimit-Reset"] = str(int(reset))
        return response

    return middleware
