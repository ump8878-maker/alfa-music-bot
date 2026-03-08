from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

# data/ в корне проекта для SQLite
_data_dir = Path(__file__).resolve().parent.parent / "data"
_data_dir.mkdir(exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Добавляем новые колонки если их нет (SQLite не поддерживает IF NOT EXISTS для ALTER)
        from sqlalchemy import text, inspect as sa_inspect
        def _ensure_columns(connection):
            inspector = sa_inspect(connection)
            columns = {c["name"] for c in inspector.get_columns("music_profiles")}
            if "guilty_genres" not in columns:
                connection.execute(text(
                    "ALTER TABLE music_profiles ADD COLUMN guilty_genres JSON"
                ))
        await conn.run_sync(_ensure_columns)
