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

# Получаем токен из переменных окружения bothost.ru
TOKEN = os.getenv('API_TOKEN')
if not TOKEN:
    logger.error("❌ API_TOKEN не найден в переменных окружения!")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"🤚🏻 {user.first_name}, приветствую 🤚🏻\n\n"

        f"🎗 Меня зовут *PGB*, я многофункциональный игровой развлекательный бот 🎗\n"

        f"🎮 В боте вы сможете поиграть во множество игр, зарабатывать валюты, копать руды, завести питомца, открывать кейсы и многое другое! 🎮\n\n"

        f"💥 Имеются различные имущества статусы, работы, которые вы сможете купить и улучшать 💥\n"

        f"📌 Подробнее познакомиться с ботом вы можете используя команды в главном меню 📌\n\n"

        f"❇️ Добро пожаловать! ❇️\n",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "🆘 *Помощь по командам:*\n\n"
        "/start - Начать\n"
        "/help - Эта справка\n"
        "/ping - Проверка работы бота\n\n",
        parse_mode='Markdown'
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ping"""
    await update.message.reply_text("🏓 PONG! Бот активен!")

def main():
    """Запуск бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ping", ping_command))
        
        logger.info(f"🤖 Бот запускается с токеном: {TOKEN[:10]}...")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    main()


