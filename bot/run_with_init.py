# run.py
import sys
from sqlalchemy import delete

from app.bot import build_app
from app.config import settings
from app.db import init_db, SessionLocal
from app import repo
from app.models import MeetingStatus, Answer, Response, Option, Question, Meeting

# ВКЛ/ВЫКЛ очистку и автозаполнение БД
CLEAR_AND_SEED_DB = True


async def seed_db(clear: bool = True) -> None:
    """Очистить БД и добавить тестовые данные (2 встречи с вопросами)."""
    await init_db()
    async with SessionLocal() as db:
        if clear:
            # порядок удаления важен (снизу вверх по связям)
            await db.execute(delete(Answer))
            await db.execute(delete(Response))
            await db.execute(delete(Option))
            await db.execute(delete(Question))
            await db.execute(delete(Meeting))
            await db.commit()

        # Создаём/находим админа (по первому id из ADMIN_IDS, иначе телеграм-id=1)
        admin_tid = settings.ADMIN_IDS[0] if settings.ADMIN_IDS else 1
        admin_user = await repo.get_or_create_user(db, telegram_id=admin_tid, fio="Admin User")

        # Встреча 1: Планёрка
        m1 = await repo.create_meeting(
            db, created_by=admin_user.id,
            title="Планёрка", description="Еженедельное совещание",
            department="IT-отдел", country="Россия", deadline_at=None,
        )
        await repo.add_question(db, m1.id, "Какие задачи выполнены на неделе?", "text", 0, True, None)
        await repo.add_question(db, m1.id, "Сколько участников будет?", "int", 1, True, None)
        await repo.add_question(db, m1.id, "Нужна запись встречи?", "bool", 2, False, None)
        await repo.add_question(db, m1.id, "Формат встречи?", "choice", 3, True, ["Онлайн", "Офлайн"])
        await repo.set_meeting_status(db, m1.id, MeetingStatus.open)

        # Встреча 2: Ретроспектива
        m2 = await repo.create_meeting(
            db, created_by=admin_user.id,
            title="Ретроспектива", description="Итоги спринта и план улучшений",
            department="IT-отдел", country="Россия", deadline_at=None,
        )
        await repo.add_question(db, m2.id, "Что было хорошо?", "text", 0, True, None)
        await repo.add_question(db, m2.id, "Что улучшить?", "text", 1, True, None)
        await repo.add_question(db, m2.id, "Темы для обсуждения", "multi", 2, False,
                                ["Статусы", "Риски", "Блокеры", "Демо"])
        await repo.set_meeting_status(db, m2.id, MeetingStatus.open)


def main():
    import asyncio
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if CLEAR_AND_SEED_DB:
        asyncio.run(seed_db(clear=True))
        # важная строка: создаём новый цикл для run_polling()
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = build_app()
    print("🤖 Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
