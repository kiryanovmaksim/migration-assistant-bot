# app/db.py
from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select
from passlib.hash import bcrypt

from .config import settings


# ---------- Engine & Session ----------

# Выбираем строку подключения:
# - если запускаем pytest (PYTEST_CURRENT_TEST есть в окружении) → DB_DSN_TEST
# - иначе → DB_DSN (боевой/разработческий режим)
if "PYTEST_CURRENT_TEST" in os.environ:
    dsn = os.getenv("DB_DSN_TEST")
else:
    dsn = os.getenv("DB_DSN", "sqlite+aiosqlite:///./data/bot.db")

if dsn and dsn.startswith("sqlite+aiosqlite:///"):
    raw_path = dsn.replace("sqlite+aiosqlite:///", "")
    # путь всегда от корня проекта
    project_root = Path(__file__).resolve().parents[2]  # подняться до корня
    abs_path = (project_root / raw_path).resolve()
    dsn = f"sqlite+aiosqlite:///{abs_path}"


engine = create_async_engine(dsn, echo=False, future=True)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Базовый класс для ORM-моделей."""
    pass


# ---------- Init DB ----------

async def init_db() -> None:
    """
    Создаёт таблицы при первом запуске и выполняет сидинг.
    Для SQLite дополнительно гарантирует наличие каталога data/.
    """
    if dsn.startswith("sqlite+aiosqlite:///"):
        db_path = dsn.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_defaults()


# ---------- Seed data ----------

async def seed_defaults() -> None:
    """Создание базовых ролей и администратора"""
    from .models import Role, User

    async with SessionLocal() as s:
        # роли
        roles = (await s.execute(select(Role))).scalars().all()
        if not roles:
            s.add_all([
                Role(name="Администратор"),
                Role(name="Модератор"),
                Role(name="Участник"),
            ])
            await s.commit()

        # админ
        if settings.ADMIN_USERNAME:
            res = await s.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
            admin = res.scalar_one_or_none()
            if not admin:
                admin_role = (await s.execute(select(Role).where(Role.name == "Администратор"))).scalar_one()
                s.add(User(
                    username=settings.ADMIN_USERNAME,
                    password_hash=bcrypt.hash(settings.ADMIN_PASSWORD or "admin123"),
                    role_id=admin_role.id,
                    fio="Default Admin",
                    is_active=True
                ))
                await s.commit()
