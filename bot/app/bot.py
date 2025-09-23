from __future__ import annotations

import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import settings
from .db import SessionLocal
from . import repo
from .utils import parse_meeting_form, require_login, require_role


# ---------------------------- user commands -----------------------------

@require_login
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Добро пожаловать! Используйте /login для входа.")


@require_login
async def my_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with SessionLocal() as db:
        user = await repo.get_active_user(db, update.effective_user.id)
        if user:
            await update.message.reply_text(f"👤 {user.username}, роль: {user.role.name}")
        else:
            await update.message.reply_text("⚠️ Вы не авторизованы.")


# ---------------------------- meeting commands (admin only) -----------------------------

@require_role("Администратор")
async def new_meeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Использование: /new_meeting Title | Description | Department | Country | Deadline")
        return

    title, description, department, country, deadline_at = parse_meeting_form(text)

    async with SessionLocal() as db:
        meeting = await repo.create_meeting(db, title, description, department, country, deadline_at)
        await update.message.reply_text(f"✅ Встреча создана (id={meeting.id})")


@require_role("Администратор")
async def add_q_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /add_q <meeting_id> <текст вопроса>")
        return

    meeting_id = int(context.args[0])
    text = " ".join(context.args[1:])

    async with SessionLocal() as db:
        q = await repo.add_question(db, meeting_id, text)
        if q:
            await update.message.reply_text(f"➕ Вопрос добавлен (id={q.id})")
        else:
            await update.message.reply_text("❌ Встреча не найдена.")


@require_role("Администратор")
async def open_meeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /open_meeting <meeting_id>")
        return

    meeting_id = int(context.args[0])

    async with SessionLocal() as db:
        ok = await repo.set_meeting_status(db, meeting_id, is_open=True)
        if ok:
            await update.message.reply_text("✅ Встреча открыта.")
        else:
            await update.message.reply_text("❌ Встреча не найдена.")


@require_role("Администратор")
async def close_meeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /close_meeting <meeting_id>")
        return

    meeting_id = int(context.args[0])

    async with SessionLocal() as db:
        ok = await repo.set_meeting_status(db, meeting_id, is_open=False)
        if ok:
            await update.message.reply_text("✅ Встреча закрыта.")
        else:
            await update.message.reply_text("❌ Встреча не найдена.")


@require_role("Администратор")
async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /export <meeting_id>")
        return

    meeting_id = int(context.args[0])

    async with SessionLocal() as db:
        csv_bytes = await repo.export_meeting_csv(db, meeting_id)
        if csv_bytes:
            await update.message.reply_document(document=csv_bytes, filename=f"meeting_{meeting_id}.csv")
        else:
            await update.message.reply_text("❌ Встреча не найдена или пуста.")


# ---------------------------- auth commands -----------------------------

async def login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /login <username> <password>")
        return

    username, password = context.args[0], context.args[1]

    async with SessionLocal() as db:
        user = await repo.authenticate_user(db, username, password)
        if not user:
            await update.message.reply_text("❌ Неверный логин или пароль")
            return

        await repo.set_active_session(db, update.effective_user.id, user.id)
        await update.message.reply_text(f"✅ Успешный вход. Ваша роль: {user.role.name}")


@require_login
async def logout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with SessionLocal() as db:
        await repo.logout(db, update.effective_user.id)
    await update.message.reply_text("ℹ️ Вы вышли из системы")


@require_login
async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with SessionLocal() as db:
        user = await repo.get_active_user(db, update.effective_user.id)
        if user:
            await update.message.reply_text(f"👤 Вы вошли как {user.username}, роль: {user.role.name}")
        else:
            await update.message.reply_text("⚠️ Вы не вошли в систему")


# ---------------------------- role management (admin only) -----------------------------

@require_role("Администратор")
async def roles_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with SessionLocal() as db:
        roles = await repo.list_roles(db)
        if not roles:
            await update.message.reply_text("Ролей нет.")
            return
        text = "\n".join(f"{r.id}: {r.name}" for r in roles)
        await update.message.reply_text(f"Список ролей:\n{text}")


@require_role("Администратор")
async def addrole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /addrole <название>")
        return
    name = " ".join(context.args)
    async with SessionLocal() as db:
        role = await repo.create_role(db, name)
        await update.message.reply_text(f"✅ Роль создана: {role.id} → {role.name}")


@require_role("Администратор")
async def renamerole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /renamerole <id> <новое название>")
        return
    role_id, new_name = context.args[0], " ".join(context.args[1:])
    async with SessionLocal() as db:
        await repo.rename_role(db, int(role_id), new_name)
        await update.message.reply_text(f"✏️ Роль {role_id} переименована в {new_name}")


@require_role("Администратор")
async def delrole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /delrole <id>")
        return
    role_id = int(context.args[0])
    async with SessionLocal() as db:
        ok = await repo.delete_role(db, role_id)
        if ok:
            await update.message.reply_text(f"🗑 Роль {role_id} удалена.")
        else:
            await update.message.reply_text("⚠️ Невозможно удалить роль — она используется пользователями.")


@require_role("Администратор")
async def setrole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /setrole <username> <role_id>")
        return
    username, role_id = context.args[0], int(context.args[1])
    async with SessionLocal() as db:
        ok = await repo.set_user_role(db, username, role_id)
        if ok:
            await update.message.reply_text(f"✅ Пользователю {username} назначена роль {role_id}.")
        else:
            await update.message.reply_text("❌ Пользователь не найден.")


# ---------------------------- text flow -----------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используйте /help.")


# ---------------------------- init / build -----------------------------

async def _on_startup(app: Application) -> None:
    from .db import init_db
    await init_db()


def build_app() -> Application:
    app = Application.builder().token(settings.BOT_TOKEN).build()

    # auth
    app.add_handler(CommandHandler("login", login_cmd))
    app.add_handler(CommandHandler("logout", logout_cmd))
    app.add_handler(CommandHandler("whoami", whoami_cmd))

    # user
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("my", my_cmd))

    # admin meetings
    app.add_handler(CommandHandler("new_meeting", new_meeting_cmd))
    app.add_handler(CommandHandler("add_q", add_q_cmd))
    app.add_handler(CommandHandler("open_meeting", open_meeting_cmd))
    app.add_handler(CommandHandler("close_meeting", close_meeting_cmd))
    app.add_handler(CommandHandler("export", export_cmd))

    # role management
    app.add_handler(CommandHandler("roles", roles_cmd))
    app.add_handler(CommandHandler("addrole", addrole_cmd))
    app.add_handler(CommandHandler("renamerole", renamerole_cmd))
    app.add_handler(CommandHandler("delrole", delrole_cmd))
    app.add_handler(CommandHandler("setrole", setrole_cmd))

    # text flow
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # init hook
    app.post_init = _on_startup
    return app


async def run() -> None:
    app = build_app()
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(run())
