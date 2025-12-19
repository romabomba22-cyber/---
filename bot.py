import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    
    # Создаем клавиатуру с кнопками-ссылками
    keyboard = [
        [
            InlineKeyboardButton("📱 Мой Telegram", url="https://t.me/your_username"),
            InlineKeyboardButton("💻 GitHub", url="https://github.com/romabomba22-cyber")
        ],
        [
            InlineKeyboardButton("🚀 Донат", url="https://www.donationalerts.com/r/your_donate"),
            InlineKeyboardButton("📚 Документация", url="https://core.telegram.org/bots/api")
        ],
        [
            InlineKeyboardButton("💰 Баланс", callback_data="balance"),
            InlineKeyboardButton("🎮 Играть", callback_data="play")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Бот работает!\n"
        f"👋 Привет, {user.first_name}!\n"
        f"🆔 Твой ID: {user.id}\n\n"
        f"📋 Команды:\n"
        f"/help - Помощь\n"
        f"/ping - Проверка связи\n\n"
        f"👇 Используй кнопки ниже:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    # Клавиатура для команды help
    keyboard = [
        [
            InlineKeyboardButton("📱 Telegram", url="https://t.me/your_username"),
            InlineKeyboardButton("💻 GitHub", url="https://github.com/romabomba22-cyber")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🆘 *Помощь по командам:*\n\n"
        "/start - Начать (с кнопками)\n"
        "/help - Эта справка\n"
        "/ping - Проверка работы бота\n\n"
        "⚡ Бот работает на bothost.ru\n\n"
        "🔗 *Полезные ссылки:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ping"""
    await update.message.reply_text("🏓 PONG! Бот активен!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "balance":
        await query.edit_message_text(
            text="💰 *Баланс*\n\n"
                 "Функция баланса скоро появится!\n"
                 "Сейчас доступны команды:\n"
                 "/help - Помощь\n"
                 "/ping - Проверка связи",
            parse_mode='Markdown'
        )
    elif query.data == "play":
        await query.edit_message_text(
            text="🎮 *Игровой модуль*\n\n"
                 "Игровые функции в разработке!\n"
                 "Следите за обновлениями.",
            parse_mode='Markdown'
        )

def main():
    """Запуск бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ping", ping_command))
        
        # Регистрируем обработчик кнопок
from telegram.ext import CallbackQueryHandler
        application.add_handler(CallbackQueryHandler(button_handler))
        
        logger.info(f"🤖 Бот запускается с токеном: {TOKEN[:10]}...")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    main()
