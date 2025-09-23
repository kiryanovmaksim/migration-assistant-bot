import os
import sqlite3

BASE_DIR = os.path.dirname(__file__)          # bot/
DATA_DIR = os.path.join(BASE_DIR, "data")     # bot/data

SQL_FILE = os.path.join(DATA_DIR, "init.sql")
DB_FILE = os.path.join(DATA_DIR, "bot.db")    # используем bot.db, а не test.db


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


from passlib.hash import bcrypt


def seed_password_hashes():
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from app.models import User

    async def inner():
        engine = create_async_engine(f"sqlite+aiosqlite:///{DB_FILE}")
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            # for u in users:
            #     if not u.password_hash.startswith("$2b$"):
            #         u.password_hash = bcrypt.hash(u.password_hash)
            await session.commit()

    asyncio.run(inner())


if __name__ == "__main__":
    reset_db()
    seed_password_hashes()
