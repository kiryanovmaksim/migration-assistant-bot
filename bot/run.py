# run.py
from app.bot import build_app


def main():
    app = build_app()
    print("🤖 Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
