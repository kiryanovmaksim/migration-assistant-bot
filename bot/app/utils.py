# app/utils.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Iterable, Callable, Any
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from .db import SessionLocal
from . import repo


# ---------- Проверка ролей / авторизации ----------

async def get_current_user(telegram_id: int):
    """Получить активного пользователя по telegram_id или None"""
    async with SessionLocal() as db:
        return await repo.get_active_user(db, telegram_id)


def require_login(handler: Callable) -> Callable:
    """Декоратор: пускает только авторизованных пользователей"""
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        telegram_id = update.effective_user.id
        user = await get_current_user(telegram_id)
        if not user:
            await update.message.reply_text("❌ Вы не авторизованы. Используйте команду /login.")
            return
        return await handler(update, context, *args, **kwargs)
    return wrapper


def require_role(role_name: str):
    """Декоратор: пускает только пользователей с указанной ролью"""
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            telegram_id = update.effective_user.id
            user = await get_current_user(telegram_id)
            if not user:
                await update.message.reply_text("❌ Вы не авторизованы. Используйте команду /login.")
                return
            if not user.role or user.role.name != role_name:
                await update.message.reply_text(f"⚠️ Недостаточно прав: требуется роль «{role_name}».")
                return
            return await handler(update, context, *args, **kwargs)
        return wrapper
    return decorator


# ---------- Старый код (оставляем) ----------

def is_admin(user_id: int, admin_ids: Iterable[int]) -> bool:
    """Проверка прав администратора по списку ID из .env (устаревшее решение)."""
    try:
        return int(user_id) in set(int(x) for x in admin_ids)
    except Exception:
        return False


def _try_parse_datetime(s: str) -> Optional[datetime]:
    """Парсинг даты дедлайна в нескольких удобных форматах."""
    s = s.strip()
    if not s:
        return None
    fmts = [
        "%Y-%m-%d",              # 2025-09-30
        "%Y-%m-%d %H:%M",        # 2025-09-30 18:30
        "%Y-%m-%dT%H:%M",        # 2025-09-30T18:30
        "%Y-%m-%dT%H:%M:%S",     # 2025-09-30T18:30:00
        "%d.%m.%Y",              # 30.09.2025
        "%d.%m.%Y %H:%M",        # 30.09.2025 18:30
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_meeting_form(text: str):
    """
    Парсит строку для создания встречи из админ-команды /new_meeting.

    Ожидаемый формат (пайп-разделитель):
        Title | Description | Department | Country | Deadline
    """
    parts = [p.strip() for p in (text or "").split("|")]
    while len(parts) < 5:
        parts.append("")

    title = parts[0]
    description = parts[1] or None
    department = parts[2] or None
    country = parts[3] or None
    deadline_at = _try_parse_datetime(parts[4])

    if not title:
        title = "Untitled meeting"

    return title, description, department, country, deadline_at
