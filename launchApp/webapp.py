# launchApp.py
import os
import sys
import asyncio

# Убедимся, что видим проект
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bot.app.bot import build_app


async def main():
    print("🤖 Bot is running on PythonAnywhere... Press Ctrl+C to stop.")
    app = build_app()
    await app.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
