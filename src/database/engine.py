"""SQLAlchemy engine and session management"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker

from src.config import PostgresConfig


class Database:
    """Database connection manager"""

    def __init__(self, config: PostgresConfig):
        self.config = config

        self.sync_engine = create_engine(
            config.sync_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
        self.SyncSession = sessionmaker(bind=self.sync_engine)

        self.async_engine = create_async_engine(
            config.async_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
        self.AsyncSession = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def create_tables(self):
        from src.database.tables import Base

        Base.metadata.create_all(self.sync_engine)

    def get_sync_session(self) -> Session:
        return self.SyncSession()

    async def close(self):
        await self.async_engine.dispose()
        self.sync_engine.dispose()

    def is_connected(self) -> bool:
        try:
            with self.sync_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False