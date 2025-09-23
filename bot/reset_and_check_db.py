import os
import sqlite3

BASE_DIR = os.path.dirname(__file__)          # bot/
DATA_DIR = os.path.join(BASE_DIR, "data")     # bot/data

SQL_FILE = os.path.join(DATA_DIR, "init.sql")
DB_FILE = os.path.join(DATA_DIR, "test.db")


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


if __name__ == "__main__":
    reset_db()
