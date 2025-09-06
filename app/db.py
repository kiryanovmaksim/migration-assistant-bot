# app/db.py
from __future__ import annotations

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from .config import settings


# ---------- Engine & Session ----------

# echo=False чтобы не засорять логи; можно включить при отладке
engine = create_async_engine(settings.DB_DSN, echo=False, future=True)

# Фабрика асинхронных сессий
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Базовый класс для ORM-моделей."""
    pass


# ---------- Init ----------

async def init_db() -> None:
    """
    Создаёт таблицы при первом запуске без ручных SQL-скриптов.
    Для SQLite дополнительно гарантирует наличие папки data/.
    """
    # Если SQLite — гарантируем существование каталога файла БД
    if settings.DB_DSN.startswith("sqlite+aiosqlite:///"):
        db_path = settings.DB_DSN.split("sqlite+aiosqlite:///")[1]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    # Важно импортировать модели перед create_all
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
