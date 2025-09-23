# app/config.py
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()


class Settings(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: list[int] = [
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
    ]
    DB_DSN: str = os.getenv("DB_DSN", "sqlite+aiosqlite:///./data/bot.db")

    # учётка для первичного администратора
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")



settings = Settings()
