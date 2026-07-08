"""Async SQLAlchemy engine/session for the auth tables."""
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import config
from auth.models import Base, OAuthAccount, User

engine = create_async_engine(config.AUTH_DB_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_auth_tables() -> None:
    """Create the users/oauth_accounts tables. Idempotent, called on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def list_active_user_ids() -> list[str]:
    """All active user IDs, for background jobs that must run per-user."""
    async with async_session_maker() as session:
        result = await session.execute(select(User.id).where(User.is_active.is_(True)))
        return [str(uid) for uid in result.scalars().all()]
