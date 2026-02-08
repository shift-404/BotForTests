from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🌱 Бот фермы 'Смак природи' работает в фоновом режиме."

# Этот эндпоинт нужен для проверки здоровья от Render
@app.route('/health')
def health():
    return "OK", 200

# Функция для запуска из командной строки
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
