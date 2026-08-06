import os
import time
from collections import defaultdict
from urllib.parse import urlparse

from fastapi import Request, HTTPException

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "https://REPLACE_WITH_YOUR_DOMAIN.com")
RATE_LIMIT_PER_HOUR = 5
_WINDOW_SECONDS = 3600

_request_log: dict[str, list[float]] = defaultdict(list)


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    parsed = urlparse(origin)
    allowed = urlparse(ALLOWED_ORIGIN)
    if (parsed.scheme, parsed.netloc) != (allowed.scheme, allowed.netloc):
        raise HTTPException(status_code=403, detail="origin not allowed")


def _check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    recent = [t for t in _request_log.get(client_ip, []) if now - t < _WINDOW_SECONDS]
    if len(recent) >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(status_code=429, detail="rate limit exceeded, try again later")
    recent.append(now)
    _request_log[client_ip] = recent


def security_gate(request: Request) -> None:
    _check_origin(request)
    _check_rate_limit(request)
