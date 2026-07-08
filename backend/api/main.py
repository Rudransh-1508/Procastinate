"""FastAPI entrypoint.

Mounts the API under /api, starts the scheduler + DB on startup, wires
Google-OAuth authentication, and (in production) serves the built React
frontend.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import config
from db.db import init_db
from api.routes import router
from services.checkin_scheduler import start_scheduler
from auth.db import create_auth_tables
from auth.router import router as google_auth_router
from auth.schemas import UserRead, UserUpdate
from auth.users import auth_backend, fastapi_users

logging.basicConfig(level=logging.INFO)

_scheduler = None
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    init_db()
    await create_auth_tables()
    _scheduler = start_scheduler()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="Procrastination Profiler API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth routes (must be registered before the SPA catch-all below) -------
app.include_router(google_auth_router, prefix="/api")
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/api/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/api/users", tags=["users"]
)

# --- App routes --------------------------------------------------------------
app.include_router(router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}


# Serve the built frontend in production (no-op during dev — Vite serves it).
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"detail": "frontend not built"}
