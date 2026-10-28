"""Small, bounded per-process limiter for the public entry points."""
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import Request
from starlette.responses import JSONResponse

_windows: OrderedDict[tuple[str, str], deque] = OrderedDict()
_lock = Lock()


async def public_rate_limit(request: Request, call_next):
    path = request.url.path
    category = "bootstrap" if path == "/v1/widget/bootstrap" else "message" if path.startswith("/v1/sessions/") and path.endswith("/messages") else None
    if request.method == "POST" and category:
        address = request.client.host if request.client else "unknown"
        key = (address, category)
        now = time.monotonic()
        with _lock:
            window = _windows.setdefault(key, deque())
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= (30 if category == "bootstrap" else 60):
                return JSONResponse({"detail": "Muitas solicitações em pouco tempo. Aguarde um minuto e tente novamente."}, status_code=429, headers={"Retry-After": "60"})
            window.append(now)
            _windows.move_to_end(key)
            while len(_windows) > 10000:
                _windows.popitem(last=False)
    return await call_next(request)
