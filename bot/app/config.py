# app/config.py
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()


class Settings(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    # список админов через запятую
    ADMIN_IDS: list[int] = [
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
    ]
    # строка подключения к БД (по умолчанию SQLite async)
    DB_DSN: str = os.getenv("DB_DSN", "sqlite+aiosqlite:///./data/bot.db")


settings = Settings()
