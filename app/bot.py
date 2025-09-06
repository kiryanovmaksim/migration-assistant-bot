# app/bot.py
"""
Telegram bot: встречи/опросы с ролями и БД.
- /start: список открытых встреч, начало заполнения
- /my: краткая инфа для пользователя (заглушка)
- /new_meeting (admin): создать встречу одной строкой
- /add_q (admin): добавить вопрос в встречу
- /open_meeting, /close_meeting (admin): смена статуса
- /export (admin): заглушка выгрузки JSON
Ответы сохраняются в БД, FSM хранится в памяти (минимальная версия).
"""

from __future__ import annotations
from typing import Callable, Awaitable
import io
import json
from loguru import logger
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .config import settings
from .db import init_db, SessionLocal
from . import repo
from .models import MeetingStatus
from .fsm import start_fill, get_state, advance, clear_state
from .utils import parse_meeting_form, is_admin


# ---------------------------- infra -----------------------------

async def _on_startup(app: Application) -> None:
    """Инициализация БД при старте приложения."""
    await init_db()
    logger.info("DB initialized, bot ready.")


def admin_only(func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]):
    """Декоратор для админ-команд по списку ID из .env (ADMIN_IDS)."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else 0
        if not is_admin(uid, settings.ADMIN_IDS):
            await update.effective_message.reply_text("Только для администраторов.")
            return
        return await func(update, context)
    return wrapper


# ---------------------------- user commands -----------------------------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает открытые встречи и предлагает выбрать."""
    uid = update.effective_user.id if update.effective_user else 0
    # регистрируем пользователя (если нет)
    async with SessionLocal() as db:
        await repo.get_or_create_user(db, uid, fio=update.effective_user.full_name if update.effective_user else None)
        meetings = await repo.list_open_meetings(db)

    if not meetings:
        await update.message.reply_text("Нет открытых встреч.")
        return

    kb = [[KeyboardButton(f"{m.id}: {m.title}")] for m in meetings]
    await update.message.reply_text(
        "Выберите встречу:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )


async def my_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Минимальная заглушка: отображает ваш Telegram ID."""
    uid = update.effective_user.id if update.effective_user else 0
    async with SessionLocal() as db:
        _ = await repo.get_or_create_user(db, uid)
    await update.message.reply_text(f"Ваш ID: {uid}\n(список ваших анкет появится позднее)")


# ---------------------------- admin commands -----------------------------

@admin_only
async def new_meeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает форму данных для новой встречи одной строкой."""
    await update.message.reply_text(
        "Отправьте данные встречи одной строкой:\n"
        "`Title | Description | Department | Country | 2025-09-30`",
        parse_mode="Markdown",
    )
    context.user_data["await_new_meeting"] = True


@admin_only
async def add_q_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает строку для добавления вопроса к встрече."""
    await update.message.reply_text(
        "Формат: meeting_id | type(text|choice|multi|bool|int) | order | required(0/1) | question text | options(csv)\n"
        "Пример: `1|choice|0|1|Какой формат? | Онлайн, Офлайн`",
        parse_mode="Markdown",
    )
    context.user_data["await_add_q"] = True


@admin_only
async def open_meeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Открывает встречу для ответов."""
    try:
        mid = int(context.args[0])
    except Exception:
        await update.message.reply_text("Использование: /open_meeting <meeting_id>")
        return
    async with SessionLocal() as db:
        await repo.set_meeting_status(db, mid, MeetingStatus.open)
    await update.message.reply_text(f"Встреча {mid} открыта.")


@admin_only
async def close_meeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Закрывает встречу."""
    try:
        mid = int(context.args[0])
    except Exception:
        await update.message.reply_text("Использование: /close_meeting <meeting_id>")
        return
    async with SessionLocal() as db:
        await repo.set_meeting_status(db, mid, MeetingStatus.closed)
    await update.message.reply_text(f"Встреча {mid} закрыта.")


@admin_only
async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Простая заглушка экспорта (для базовой версии)."""
    buf = io.BytesIO(json.dumps({"note": "export stub"}, ensure_ascii=False, indent=2).encode("utf-8"))
    buf.seek(0)
    await update.message.reply_document(document=InputFile(buf, filename="export.json"))


# ---------------------------- text handler (user flow) -----------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Общий обработчик текстов: админ-формы + прохождение анкеты."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # --- admin: обработка форм по контексту ---
    if context.user_data.get("await_new_meeting"):
        context.user_data["await_new_meeting"] = False
        title, description, department, country, deadline_at = parse_meeting_form(text)
        uid = update.effective_user.id if update.effective_user else 0
        async with SessionLocal() as db:
            user = await repo.get_or_create_user(db, uid)
            m = await repo.create_meeting(db, user.id, title, description, department, country, deadline_at)
        await update.message.reply_text(
            f"Встреча создана: ID={m.id}, статус=draft.\n"
            f"Откройте её командой: /open_meeting {m.id}"
        )
        return

    if context.user_data.get("await_add_q"):
        context.user_data["await_add_q"] = False
        try:
            mid, qtype, order, required, qtext, *opts = [p.strip() for p in text.split("|")]
            mid = int(mid)
            order = int(order)
            required = required in ("1", "true", "True", "да", "Да", "y", "Y")
            options = []
            if opts:
                options = [o.strip() for o in opts[-1].split(",") if o.strip()]
        except Exception:
            await update.message.reply_text("Неверный формат. Повторите /add_q.")
            return
        async with SessionLocal() as db:
            await repo.add_question(db, mid, qtext, qtype, order, required, options)
        await update.message.reply_text("Вопрос добавлен.")
        return

    # --- user: выбор встречи в виде "id: title" ---
    if ":" in text and text.split(":", 1)[0].strip().isdigit():
        mid = int(text.split(":", 1)[0])
        start_fill(update.effective_user.id, mid)
        await update.message.reply_text(f"Начинаем заполнение встречи {mid}.")
        async with SessionLocal() as db:
            meeting = await repo.get_meeting(db, mid)
            if not meeting or meeting.status != MeetingStatus.open:
                await update.message.reply_text("Встреча не найдена или не открыта.")
                return
            if not meeting.questions:
                await update.message.reply_text("Для встречи ещё не добавлены вопросы.")
                return
            await update.message.reply_text(meeting.questions[0].text)
        return

    # --- user: ответы по текущей анкете ---
    st = get_state(update.effective_user.id)
    if st:
        async with SessionLocal() as db:
            meeting = await repo.get_meeting(db, st.meeting_id)
            if not meeting or not meeting.questions:
                await update.message.reply_text("Ошибка: нет вопросов.")
                clear_state(update.effective_user.id)
                return

            # получить/создать response
            user = await repo.get_or_create_user(db, update.effective_user.id)
            resp = await repo.get_or_create_response(db, user.id, meeting.id)

            # текущий вопрос
            q = meeting.questions[st.current_q_idx]
            await repo.save_answer(db, resp.id, q.id, text)

            # след. вопрос или завершение
            if st.current_q_idx + 1 < len(meeting.questions):
                advance(update.effective_user.id)
                q_next = meeting.questions[st.current_q_idx + 1]
                await update.message.reply_text(q_next.text)
            else:
                await repo.submit_response(db, resp.id)
                clear_state(update.effective_user.id)
                await update.message.reply_text("Спасибо! Анкета отправлена.")
        return

    # по умолчанию
    await update.message.reply_text("Команда не распознана. Используйте /start.")


# ---------------------------- app factory -----------------------------

def build_app() -> Application:
    app = Application.builder().token(settings.BOT_TOKEN).build()

    # user
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("my", my_cmd))

    # admin
    app.add_handler(CommandHandler("new_meeting", new_meeting_cmd))
    app.add_handler(CommandHandler("add_q", add_q_cmd))
    app.add_handler(CommandHandler("open_meeting", open_meeting_cmd))
    app.add_handler(CommandHandler("close_meeting", close_meeting_cmd))
    app.add_handler(CommandHandler("export", export_cmd))

    # text flow
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # init hook
    app.post_init = _on_startup
    return app
