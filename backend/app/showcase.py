"""Explicit public showcase: signed anonymous ownership and bounded request rates."""
from collections import OrderedDict, deque
import hashlib
import hmac
import secrets
from time import monotonic, time
from urllib.parse import urlparse
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

KEY = secrets.token_bytes(32)
COOKIE = "orbit_session"
WINDOW = 60
MAX_CLIENTS = 2048

class ShowcaseMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.clients = OrderedDict()

    async def dispatch(self, request, call_next):
        token = request.cookies.get(COOKIE, "")
        parts = token.split(".")
        valid = False
        if len(parts) == 3:
            identity, issued, signature = parts
            expected = hmac.new(KEY, f"{identity}.{issued}".encode(), hashlib.sha256).hexdigest()
            valid = hmac.compare_digest(signature, expected) and issued.isdigit() and 0 <= time()-int(issued) < 86400
        if not valid:
            identity, issued = secrets.token_hex(24), str(int(time()))
            signature = hmac.new(KEY, f"{identity}.{issued}".encode(), hashlib.sha256).hexdigest()
            token = f"{identity}.{issued}.{signature}"
        request.state.showcase_owner = identity
        if request.url.path.startswith("/api/") and (request.method == "POST" or request.url.path.endswith("/assessment")):
            is_post = request.method == "POST"
            origin = request.headers.get("origin")
            if is_post and origin and urlparse(origin).netloc != request.url.netloc:
                return JSONResponse({"detail": "Use this site's own analysis page."}, status_code=403)
            length = request.headers.get("content-length", "")
            if is_post and (not length.isdigit() or int(length) > 11 * 1024 * 1024):
                return JSONResponse({"detail": "Request must have a valid size below 11 MiB."}, status_code=413)
            client = (request.client.host if request.client else "unknown", "post" if is_post else "assessment")
            now = monotonic()
            recent = self.clients.pop(client, deque())
            while recent and now-recent[0] >= WINDOW:
                recent.popleft()
            self.clients[client] = recent
            while len(self.clients) > MAX_CLIENTS:
                self.clients.popitem(last=False)
            if len(recent) >= (10 if is_post else 120):
                return JSONResponse({"detail": "Too many analyses. Please wait one minute."}, status_code=429, headers={"Retry-After": "60"})
            recent.append(now)
        response = await call_next(request)
        if not valid:
            response.set_cookie(COOKIE, token, httponly=True, secure=request.url.scheme == "https", samesite="lax", max_age=86400)
        return response

def showcase_access(request: Request):
    return request.state.showcase_owner
