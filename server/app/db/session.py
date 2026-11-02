import os
from typing import Any

from sqlalchemy import DefaultClause, event, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.db.base import Base

SessionFactory = async_sessionmaker[AsyncSession]


def create_engine(url: str) -> AsyncEngine:
    if url.startswith("sqlite") and ":memory:" not in url:
        path = url.split("///", 1)[1]
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    engine = create_async_engine(url)

    if url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_foreign_keys(dbapi_connection: Any, _: Any) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys = ON")

    return engine


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    return async_sessionmaker(engine, expire_on_commit=False)


def _add_missing_columns(connection: Connection) -> None:
    """`create_all` creates missing tables but never alters an existing one: add the columns
    a newer version introduced (they are all nullable or have a default)."""
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            kind = column.type.compile(connection.dialect)
            default = (
                f" DEFAULT {column.server_default.arg}" if isinstance(column.server_default, DefaultClause) else ""
            )
            connection.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {kind}{default}'))


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_add_missing_columns)
