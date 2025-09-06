# app/fsm.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class FillState:
    """Состояние прохождения анкеты пользователем."""
    meeting_id: int
    current_q_idx: int = 0  # индекс текущего вопроса (0..n-1)


# Простое хранилище состояний в памяти процесса.
# Для продакшена можно заменить на Redis/БД.
_STATE: Dict[int, FillState] = {}


def start_fill(chat_id: int, meeting_id: int) -> None:
    """Начать заполнение анкеты по встрече."""
    _STATE[chat_id] = FillState(meeting_id=meeting_id, current_q_idx=0)


def get_state(chat_id: int) -> Optional[FillState]:
    """Получить состояние пользователя (или None)."""
    return _STATE.get(chat_id)


def advance(chat_id: int) -> None:
    """Перейти к следующему вопросу."""
    st = _STATE.get(chat_id)
    if st:
        st.current_q_idx += 1


def clear_state(chat_id: int) -> None:
    """Сбросить состояние пользователя."""
    _STATE.pop(chat_id, None)
