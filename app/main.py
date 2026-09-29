import os
import secrets
import threading
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.routers import settings, ideas, scripts, characters, audio, render, scene_director, projects, youtube
from app.config import SettingsCorruptError
from app.storage import ROOT, StorageError
from app.services.project_service import RevisionConflict, ProjectCorruptError

app = FastAPI(title="Kids Video Studio", version="1.1.0")
_sessions = {}
_session_lock = threading.RLock()
_session_ttl = 8 * 60 * 60


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    testing = os.environ.get("KIDS_STUDIO_TESTING") == "1"
    allowed = {"localhost", "127.0.0.1", "::1"}
    if testing:
        allowed.add("testserver")
    try:
        target = urlsplit("http://" + request.headers.get("host", ""))
        if target.hostname not in allowed or target.username or target.password or target.path or target.query or target.fragment:
            return JSONResponse({"detail": "Untrusted host"}, status_code=403)
        target.port
        peer = request.client.host if request.client else ""
        if peer not in {"127.0.0.1", "::1", "localhost"} and not (testing and peer in {"testclient", "testserver"}):
            return JSONResponse({"detail": "Studio is loopback-only"}, status_code=403)
        callback = request.url.path == "/api/youtube/auth/callback" and request.method == "GET"
        origin = request.headers.get("origin")
        if origin:
            source = urlsplit(origin)
            expected_port = target.port or (443 if request.url.scheme == "https" else 80)
            source_port = source.port or (443 if source.scheme == "https" else 80)
            if source.scheme != request.url.scheme or source.hostname != target.hostname or source_port != expected_port or source.path or source.query or source.fragment or source.username:
                return JSONResponse({"detail": "Untrusted origin"}, status_code=403)
        if not callback and request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}:
            return JSONResponse({"detail": "Cross-site requests are not allowed"}, status_code=403)
    except ValueError:
        return JSONResponse({"detail": "Invalid request origin"}, status_code=403)

    now = time.monotonic()
    with _session_lock:
        for key in list(_sessions):
            if _sessions[key]["expires"] < now:
                del _sessions[key]
        session_id = request.cookies.get("studio_session", "")
        session = _sessions.get(session_id)
        request.state.studio_session = session_id if session else None
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            token = request.headers.get("X-Studio-Token", "")
            if not session or not token.isascii() or not secrets.compare_digest(token, session["token"]):
                return JSONResponse({"detail": "Missing or invalid studio session token"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/session")
def get_session(request: Request):
    with _session_lock:
        session_id = request.state.studio_session
        if not session_id:
            if len(_sessions) >= 128:
                oldest = min(_sessions, key=lambda key: _sessions[key]["expires"])
                del _sessions[oldest]
            session_id = secrets.token_urlsafe(32)
            _sessions[session_id] = {"token": secrets.token_urlsafe(32), "expires": time.monotonic() + _session_ttl}
        response = JSONResponse({"csrf_token": _sessions[session_id]["token"]})
        response.set_cookie("studio_session", session_id, httponly=True, samesite="lax", secure=request.url.scheme == "https", max_age=_session_ttl)
        return response


@app.exception_handler(StorageError)
async def invalid_storage(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(RevisionConflict)
async def revision_conflict(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(ProjectCorruptError)
@app.exception_handler(SettingsCorruptError)
async def corrupt_storage(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)


for router in (settings, ideas, scripts, characters, audio, render, scene_director, projects, youtube):
    app.include_router(router.router)

static_path = ROOT / "app" / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
def read_root():
    return FileResponse(static_path / "index.html")


@app.get("/review")
@app.get("/gallery")
def read_review():
    return FileResponse(static_path / "review.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Kids Video Studio"}
