# app/utils.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Iterable


def is_admin(user_id: int, admin_ids: Iterable[int]) -> bool:
    """Проверка прав администратора по списку ID из .env."""
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

    Примеры даты:
        2025-09-30
        2025-09-30 18:30
        30.09.2025
        (пусто) — без дедлайна

    Возвращает кортеж:
        (title: str, description: Optional[str], department: Optional[str],
         country: Optional[str], deadline_at: Optional[datetime])
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
        # минимальная защита: не даём создать встречу без заголовка
        title = "Untitled meeting"

    return title, description, department, country, deadline_at
