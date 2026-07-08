"""SQLAlchemy models for auth — the only part of this app that uses an ORM.

Domain data (tasks, events, check-ins, profile) stays on the existing raw
sqlite3 layer in db/db.py; these tables live in the same .db file but are
managed by fastapi-users via async SQLAlchemy.
"""
from fastapi_users.db import SQLAlchemyBaseOAuthAccountTableUUID, SQLAlchemyBaseUserTableUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship


class Base(DeclarativeBase):
    pass


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )
