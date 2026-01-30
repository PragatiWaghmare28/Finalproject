from fastapi import Request, HTTPException, Depends
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_429_TOO_MANY_REQUESTS
from time import time
from functools import wraps
from .config import get_settings

settings = get_settings()

# Simple in-memory counters: {key_or_ip: [timestamps]}
_LIMIT_STORE = {}

def _cleanup_old(entries, window):
    cutoff = time() - window
    while entries and entries[0] < cutoff:
        entries.pop(0)


async def require_api_key(request: Request):
    """Dependency that enforces an API key header `X-API-Key`."""
    header = request.headers.get("x-api-key") or request.headers.get("authorization")
    key = None
    if header:
        if header.lower().startswith("bearer "):
            key = header.split(None, 1)[1].strip()
        else:
            key = header.strip()

    if not key or not settings.api_key or key != settings.api_key:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")

    return key


def rate_limiter(limit: int, window_seconds: int):
    """Return a dependency that rate-limits by API key (or client IP if no key).

    Usage: add `Depends(rate_limiter(5,60))` to endpoint to limit to 5 calls/minute.
    """
    async def _limiter(request: Request, key: str = Depends(require_api_key)):
        ident = key or request.client.host
        bucket = _LIMIT_STORE.setdefault(ident, [])
        _cleanup_old(bucket, window_seconds)
        if len(bucket) >= limit:
            raise HTTPException(status_code=HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        bucket.append(time())
        return True

    return _limiter

# Predefined common limits
rate_limit_chat = rate_limiter(limit=30, window_seconds=60)
rate_limit_quiz = rate_limiter(limit=10, window_seconds=60)
rate_limit_process = rate_limiter(limit=5, window_seconds=60)
