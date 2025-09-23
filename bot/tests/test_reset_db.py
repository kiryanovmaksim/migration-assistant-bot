import asyncio
from passlib.hash import bcrypt
from sqlalchemy import select

from bot.reset_and_check_db import reset_db
from bot.app.db import SessionLocal
from bot.app.models import Role, User



def test_reset_and_models():
    reset_db()

    async def inner():
        async with SessionLocal() as session:
            # проверяем роли
            roles = (await session.execute(select(Role))).scalars().all()
            assert len(roles) >= 3
            assert {r.name for r in roles} >= {"Администратор", "Модератор", "Участник"}

            # создаём пользователя
            pwd = "secret123"
            user = User(username="testuser", password_hash=bcrypt.hash(pwd), role_id=roles[2].id)
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # проверяем пароль
            assert bcrypt.verify(pwd, user.password_hash)
            assert not bcrypt.verify("wrongpass", user.password_hash)

    asyncio.run(inner())
