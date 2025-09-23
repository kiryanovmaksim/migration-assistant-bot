import asyncio
from sqlalchemy import select

from bot.reset_and_check_db import reset_db
from bot.app.db import SessionLocal
from bot.app import repo
from bot.app.models import Role



def test_repo_auth_and_roles():
    reset_db()

    async def inner():
        async with SessionLocal() as db:
            # роли уже есть
            roles = await repo.list_roles(db)
            role_user = next(r for r in roles if r.name == "Участник")

            # создаём пользователя
            u = await repo.create_user(db, "u1", "pass1", role_user.id)
            assert u.username == "u1"

            # проверяем вход
            u2 = await repo.authenticate_user(db, "u1", "pass1")
            assert u2 is not None
            bad = await repo.authenticate_user(db, "u1", "wrong")
            assert bad is None

            # проверяем сессии
            s = await repo.set_active_session(db, telegram_id=111, user_id=u.id)
            assert s.is_active
            active_user = await repo.get_active_user(db, 111)
            assert active_user.username == "u1"

            await repo.logout(db, 111)
            none_user = await repo.get_active_user(db, 111)
            assert none_user is None

            # проверяем CRUD ролей
            r = await repo.create_role(db, "Тестовая")
            all_roles = await repo.list_roles(db)
            assert any(rr.name == "Тестовая" for rr in all_roles)

            await repo.rename_role(db, r.id, "Тест-2")
            updated = (await db.execute(select(Role).where(Role.id == r.id))).scalar_one()
            assert updated.name == "Тест-2"

            ok = await repo.delete_role(db, r.id)
            assert ok

    asyncio.run(inner())
