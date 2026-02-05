import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение при команде /start"""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.first_name}! 👋\n"
        f"Я простой бот, работающий на Render.\n"
        f"Твой ID: {user.id}"
    )

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку по командам"""
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Начать общение\n"
        "/help - Показать эту справку\n"
        "/about - Информация о боте"
    )

# Команда /about
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о боте"""
    await update.message.reply_text(
        "🤖 Это тестовый бот для демонстрации работы на Render\n"
        "⚡ Бот работает 24/7 на бесплатном хостинге\n"
        "📦 Версия: 1.0"
    )

# Обработка ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Логирует ошибки"""
    logger.error(f"Ошибка: {context.error}")

# Главная функция
def main():
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
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()