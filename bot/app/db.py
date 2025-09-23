# app/db.py
from __future__ import annotations

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select
from passlib.hash import bcrypt

from .config import settings


# ---------- Engine & Session ----------

engine = create_async_engine(settings.DB_DSN, echo=False, future=True)

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
    if settings.DB_DSN.startswith("sqlite+aiosqlite:///"):
        db_path = settings.DB_DSN.split("sqlite+aiosqlite:///")[1]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_defaults()


# ---------- Seed ----------

async def seed_defaults() -> None:
    """Создание базовых ролей и администратора"""
    from .models import Role, User

    async with SessionLocal() as s:
        # Роли
        roles = (await s.execute(select(Role))).scalars().all()
        if not roles:
            s.add_all([
                Role(name="Администратор"),
                Role(name="Модератор"),
                Role(name="Участник"),
            ])
            await s.commit()

        # Админ
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
