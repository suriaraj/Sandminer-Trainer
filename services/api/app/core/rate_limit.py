"""Fail-closed Redis-backed burst limits for sensitive entry points.

Use a gateway/user-aware policy before public deployment behind trusted proxies.
"""
import hashlib
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from app.core.config import get_settings


RULES: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (10, 60),
    "/api/v1/auth/register": (5, 60),
    "/api/v1/auth/refresh": (30, 60),
    "/api/v1/payments/webhooks/sandbox": (120, 60),
}
_SCRIPT = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then redis.call("EXPIRE", KEYS[1], ARGV[1]) end
return count
"""
_client = redis.from_url(get_settings().redis_url, decode_responses=True)


async def limit_sensitive_routes(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    rule = RULES.get(request.url.path)
    if rule is None or request.method != "POST":
        return await call_next(request)

    limit, window = rule
    client_ip = request.client.host if request.client else "unresolved"
    client_digest = hashlib.sha256(client_ip.encode()).hexdigest()[:24]
    key = f"pyro:rate:{request.url.path}:{client_digest}"
    try:
        count = await _client.eval(_SCRIPT, 1, key, window)
    except RedisError:
        # Silently dropping the limiter on auth routes allows brute force attempts.
        return JSONResponse(
            {"detail": "Authentication service temporarily unavailable"},
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )
    if count > limit:
        return JSONResponse(
            {"detail": "Too many requests; retry after the limit window"},
            status_code=429,
            headers={
                "Retry-After": str(window),
                "Cache-Control": "no-store",
            },
        )
    return await call_next(request)
