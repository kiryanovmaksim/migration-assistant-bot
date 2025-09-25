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


# ---------------------------- auth -----------------------------

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


# ---------------------------- meetings -----------------------------

@require_login
async def meetings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with SessionLocal() as db:
        meetings = await repo.list_meetings(db)
        if not meetings:
            await update.message.reply_text("Встреч нет.")
            return
        text = "\n".join(f"{m.id}: {m.title} [{m.status}]" for m in meetings)
        await update.message.reply_text(f"📅 Встречи:\n{text}")


@require_role("Модератор")
async def newmeeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Использование: /newmeeting Title | Desc | Dept | Country | Deadline")
        return

    title, description, department, country, deadline_at = parse_meeting_form(text)
    async with SessionLocal() as db:
        meeting = await repo.create_meeting(db, title, description, department, country, deadline_at)
        await update.message.reply_text(f"✅ Встреча создана (id={meeting.id})")


@require_role("Модератор")
async def addquestion_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /addquestion <meeting_id> <текст>")
        return
    meeting_id = int(context.args[0])
    text = " ".join(context.args[1:])
    async with SessionLocal() as db:
        q = await repo.add_question(db, meeting_id, text)
        if q:
            await update.message.reply_text(f"➕ Вопрос добавлен (id={q.id})")
        else:
            await update.message.reply_text("❌ Встреча не найдена.")


@require_role("Модератор")
async def openmeeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /openmeeting <id>")
        return
    meeting_id = int(context.args[0])
    async with SessionLocal() as db:
        ok = await repo.set_meeting_status(db, meeting_id, "open")
        await update.message.reply_text("✅ Открыта" if ok else "❌ Не найдена")


@require_role("Модератор")
async def closemeeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /closemeeting <id>")
        return
    meeting_id = int(context.args[0])
    async with SessionLocal() as db:
        ok = await repo.set_meeting_status(db, meeting_id, "closed")
        await update.message.reply_text("✅ Закрыта" if ok else "❌ Не найдена")


@require_role("Администратор")
async def delmeeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /delmeeting <id>")
        return
    meeting_id = int(context.args[0])
    async with SessionLocal() as db:
        ok = await repo.delete_meeting(db, meeting_id)
        await update.message.reply_text("🗑 Удалена" if ok else "❌ Не найдена")


@require_role("Администратор")
async def exportmeeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /exportmeeting <id>")
        return
    meeting_id = int(context.args[0])
    async with SessionLocal() as db:
        # здесь должна быть логика экспорта в CSV
        await update.message.reply_text(f"📤 Экспорт встречи {meeting_id} (заглушка)")


# ---------------------------- roles -----------------------------
# (оставляем как было в этапе 5)

# ---------------------------- misc -----------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используйте /help.")

# команды управления ролями
async def roles_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with SessionLocal() as db:
        roles = await repo.list_roles(db)
        text = "📋 Роли:\n" + "\n".join(f"{r.id}. {r.name}" for r in roles)
        await update.message.reply_text(text)


@require_role("Администратор")
async def addrole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Использование: /addrole <название>")
        return
    async with SessionLocal() as db:
        r = await repo.create_role(db, context.args[0])
        await update.message.reply_text(f"✅ Роль создана: {r.name} (id={r.id})")


@require_role("Администратор")
async def renamerole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Использование: /renamerole <id> <новое название>")
        return
    role_id = int(context.args[0])
    new_name = context.args[1]
    async with SessionLocal() as db:
        ok = await repo.rename_role(db, role_id, new_name)
        await update.message.reply_text("✅ Роль обновлена" if ok else "❌ Роль не найдена")


@require_role("Администратор")
async def delrole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Использование: /delrole <id>")
        return
    role_id = int(context.args[0])
    async with SessionLocal() as db:
        ok = await repo.delete_role(db, role_id)
        await update.message.reply_text("✅ Роль удалена" if ok else "❌ Роль не найдена")


@require_role("Администратор")
async def setrole_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Использование: /setrole <username> <role_id>")
        return
    username = context.args[0]
    role_id = int(context.args[1])
    async with SessionLocal() as db:
        u = await repo.get_user_by_username(db, username)
        if not u:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        u.role_id = role_id
        await db.commit()
        await update.message.reply_text(f"✅ Пользователь {username} теперь имеет роль {role_id}")


from telegram import ReplyKeyboardMarkup
# остальное у тебя уже есть

# ---------------------------- menu -----------------------------

COMMANDS_BY_ROLE = {
    "Администратор": [
        "/roles", "/addrole", "/renamerole", "/delrole", "/setrole",
        "/meetings", "/newmeeting", "/addquestion", "/openmeeting", "/closemeeting",
        "/delmeeting", "/exportmeeting",
        "/questions", "/answer",
        "/whoami", "/logout",
    ],
    "Модератор": [
        "/meetings", "/newmeeting", "/addquestion", "/openmeeting", "/closemeeting",
        "/questions", "/answer",
        "/whoami", "/logout",
    ],
    "Участник": [
        "/meetings", "/questions", "/answer", "/whoami", "/logout",
    ],
}



@require_login
async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with SessionLocal() as db:
        user = await repo.get_active_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("⚠️ Вы не авторизованы")
            return

        role = user.role.name
        commands = COMMANDS_BY_ROLE.get(role, ["/meetings", "/logout"])
        # делим список на строки по 2 кнопки
        keyboard = [[cmd for cmd in commands[i:i + 2]] for i in range(0, len(commands), 2)]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"📋 Доступные команды для роли *{role}*:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# показать вопросы встречи
@require_login
async def questions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, db: AsyncSession, user: User):
    if not context.args:
        await update.message.reply_text("❌ Укажите ID встречи: /questions <meeting_id>")
        return
    meeting_id = int(context.args[0])
    questions = await repo.list_questions(db, meeting_id)
    if not questions:
        await update.message.reply_text("Нет вопросов для этой встречи.")
    else:
        text = "\n".join([f"{q.id}. {q.text}" for q in questions])
        await update.message.reply_text(f"Вопросы встречи {meeting_id}:\n{text}")

# ответить на вопрос
@require_login
async def answer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, db: AsyncSession, user: User):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Используйте: /answer <question_id> <текст>")
        return
    qid = int(context.args[0])
    text = " ".join(context.args[1:])
    await repo.add_answer(db, user.id, qid, text)
    await update.message.reply_text("✅ Ответ сохранён")

# ---------------------------- help -----------------------------

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 *TeamMeet Bot* — бот для управления командными встречами.\n\n"
        "Доступные команды:\n"
        "🔑 Аутентификация:\n"
        "  /login <username> <password> — вход\n"
        "  /logout — выход\n"
        "  /whoami — информация о текущем пользователе\n\n"
        "📅 Встречи:\n"
        "  /meetings — список встреч\n"
        "  /newmeeting <данные> — создать встречу (модератор)\n"
        "  /addquestion <meeting_id> <текст> — добавить вопрос (модератор)\n"
        "  /openmeeting <id> — открыть встречу (модератор)\n"
        "  /closemeeting <id> — закрыть встречу (модератор)\n"
        "  /delmeeting <id> — удалить встречу (админ)\n"
        "  /exportmeeting <id> — экспорт встречи (админ)\n\n"
        "❓ Вопросы:\n"
        "  /questions <meeting_id> — список вопросов\n"
        "  /answer <question_id> <текст> — ответить на вопрос\n\n"
        "👥 Роли:\n"
        "  /roles — список ролей\n"
        "  /addrole <название> — добавить роль (админ)\n"
        "  /renamerole <id> <название> — переименовать роль (админ)\n"
        "  /delrole <id> — удалить роль (админ)\n"
        "  /setrole <username> <role_id> — назначить роль (админ)\n\n"
        "📋 Другое:\n"
        "  /menu — показать меню\n"
        "  /help — помощь\n\n"
        "Автор: Кирьянов Максим"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------- init -----------------------------

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

    # meetings
    app.add_handler(CommandHandler("meetings", meetings_cmd))
    app.add_handler(CommandHandler("newmeeting", newmeeting_cmd))
    app.add_handler(CommandHandler("addquestion", addquestion_cmd))
    app.add_handler(CommandHandler("openmeeting", openmeeting_cmd))
    app.add_handler(CommandHandler("closemeeting", closemeeting_cmd))
    app.add_handler(CommandHandler("delmeeting", delmeeting_cmd))
    app.add_handler(CommandHandler("exportmeeting", exportmeeting_cmd))

    # roles (из этапа 5)
    app.add_handler(CommandHandler("roles", roles_cmd))
    app.add_handler(CommandHandler("addrole", addrole_cmd))
    app.add_handler(CommandHandler("renamerole", renamerole_cmd))
    app.add_handler(CommandHandler("delrole", delrole_cmd))
    app.add_handler(CommandHandler("setrole", setrole_cmd))

    app.add_handler(CommandHandler("questions", questions_cmd))
    app.add_handler(CommandHandler("answer", answer_cmd))

    # misc
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    # misc
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # menu
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.post_init = _on_startup
    return app


async def run() -> None:
    app = build_app()

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(run())
