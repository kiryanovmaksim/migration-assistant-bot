import os
import sqlite3
import asyncio

from passlib.hash import bcrypt
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Role, User

BASE_DIR = os.path.dirname(__file__)          # bot/
DATA_DIR = os.path.join(BASE_DIR, "data")     # bot/data

SQL_FILE = os.path.join(DATA_DIR, "init.sql")
DB_FILE = os.path.join(DATA_DIR, "bot.db")


def reset_db():
    """Удаляем старую БД и создаём новую из init.sql"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("Старая база удалена.")

    with sqlite3.connect(DB_FILE) as conn, open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()
        conn.executescript(sql_script)
        conn.commit()
        print("База создана из init.sql.")


async def check_models():
    """Проверяем, что модели видят таблицы и можно работать"""
    async with SessionLocal() as session:
        roles = (await session.execute(select(Role))).scalars().all()
        print("Роли из БД:")
        for r in roles:
            print(f" - {r.id}: {r.name}")

        # создаём пользователя с паролем
        password = "secret123"
        user = User(username="testuser", password_hash=bcrypt.hash(password), role_id=roles[2].id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"Создан пользователь: {user.id}, {user.username}, роль={user.role_id}")

        # проверка пароля
        is_valid = bcrypt.verify(password, user.password_hash)
        print("Проверка пароля 'secret123':", "OK" if is_valid else "FAIL")

        is_valid_wrong = bcrypt.verify("wrongpass", user.password_hash)
        print("Проверка неверного пароля:", "OK" if is_valid_wrong else "FAIL")


if __name__ == "__main__":
    reset_db()
    asyncio.run(check_models())
