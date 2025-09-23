from flask import Flask

# Создаём Flask-приложение
app = Flask(__name__)

@app.route("/")
def index():
    return "🤖 Bot WebApp is running!"

@app.route("/ping")
def ping():
    return "pong"

# Локальный запуск
if __name__ == "__main__":
    # локально можно зайти на http://127.0.0.1:5000/
    app.run(host="0.0.0.0", port=5000, debug=True)
