"""UserManager, JWT auth backend, and the fastapi_users instance.

Bearer-token JWT auth (not cookies) — simplest to reason about across the
Vite dev server (:5173) and API (:8000) origins, no CORS-credential dance.
"""
import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from httpx_oauth.clients.google import GoogleOAuth2

import config
from auth.db import get_user_db
from auth.models import User
from db.db import generate_id, get_db

google_oauth_client = (
    GoogleOAuth2(config.GOOGLE_OAUTH_CLIENT_ID, config.GOOGLE_OAUTH_CLIENT_SECRET)
    if config.google_oauth_enabled()
    else None
)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = config.AUTH_SECRET
    verification_token_secret = config.AUTH_SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Seed an empty profile_state row for the new user (domain data, raw sqlite3)."""
        db = get_db()
        uid = str(user.id)
        if not db.execute("SELECT 1 FROM profile_state WHERE user_id = ?", (uid,)).fetchone():
            db.execute(
                "INSERT INTO profile_state (id, user_id, updated_at) VALUES (?, ?, NULL)",
                (generate_id(), uid),
            )
            db.commit()


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="api/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=config.AUTH_SECRET, lifetime_seconds=60 * 60 * 24 * 30)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_active_user_optional = fastapi_users.current_user(active=True, optional=True)
