from __future__ import annotations

import inspect
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

from .db import SessionLocal
from . import repo


def _wants_db_user(func: Callable) -> bool:
    """Определяем, ожидает ли хендлер позиционные параметры (db, user)."""
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    # Требуем минимум 4 параметра: update, context, db, user
    # Имена третьего/четвёртого параметров проверяем «по смыслу».
    return (
        len(params) >= 4
        and params[0] in ("update",)
        and params[1] in ("context",)
        and params[2] in ("db", "session", "conn")
        and params[3] in ("user", "current_user")
    )


def require_login(func: Callable):
    wants = _wants_db_user(func)

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        async with SessionLocal() as db:
            user = await repo.get_active_user(db, update.effective_user.id)
            if not user:
                await update.message.reply_text("❌ Вы не авторизованы. Используйте /login.")
                return
            if wants:
                return await func(update, context, db, user, *args, **kwargs)
            return await func(update, context, *args, **kwargs)

    return wrapper


def require_role(role_name: str):
    """Проверка роли. Админ имеет все права.
    Если хендлер ожидает (db, user), мы их передадим.
    """
    def decorator(func: Callable):
        wants = _wants_db_user(func)

        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            async with SessionLocal() as db:
                user = await repo.get_active_user(db, update.effective_user.id)
                if not user:
                    await update.message.reply_text("❌ Вы не авторизованы. Используйте /login.")
                    return
                role = user.role.name if user.role else ""
                if role != "Администратор" and role != role_name:
                    await update.message.reply_text("⛔ Недостаточно прав для этой команды.")
                    return
                if wants:
                    return await func(update, context, db, user, *args, **kwargs)
                return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


from datetime import datetime

def parse_meeting_form(text: str):
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 5:
        raise ValueError("Нужно 5 параметров: Title | Desc | Dept | Country | Deadline")

    title, desc, dept, country, deadline_str = parts[:5]

    # Преобразуем "2025-12-01" → datetime
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
    except ValueError:
        # Если формат неверный, можно вернуть None или поднять ошибку
        raise ValueError("⛔ Формат даты: YYYY-MM-DD (например, 2025-12-01)")

    return title, desc, dept, country, deadline

