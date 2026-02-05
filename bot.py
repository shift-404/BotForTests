import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from threading import Thread
from flask import Flask

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем простой Flask сервер для здоровья (требуется Render)
app = Flask('')

@app.route('/')
def home():
    return "Бот работает! ✅"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Запускаем Flask в отдельном потоке, если на Render
if os.getenv('RENDER'):
    Thread(target=run_flask, daemon=True).start()
    logger.info("Flask сервер запущен для Render")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start"""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.first_name}! 👋\n"
        f"Я простой бот, работающий на Render.\n"
        f"Твой ID: <code>{user.id}</code>"
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по командам"""
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Начать общение\n"
        "/help - Показать эту справку\n"
        "/about - Информация о боте"
    )

# Команда /about
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Информация о боте"""
    await update.message.reply_text(
        "🤖 Это тестовый бот для демонстрации работы на Render\n"
        "⚡ Бот работает 24/7 на бесплатном хостинге\n"
        "📦 Версия: 2.0 (обновлено для python-telegram-bot v21.x)"
    )

# Обработка ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибки"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)

# Главная функция
def main() -> None:
    """Запуск бота"""
    # Получаем токен из переменных окружения
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        logger.error("Токен не найден! Установите переменную окружения BOT_TOKEN")
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
