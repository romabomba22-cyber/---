import logging
import random
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Импортируем наши модули
from config import config
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(name)

# Flask приложение для веб-сервера
app = Flask(name)

# ===================== КОМАНДЫ БОТА =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Получаем или создаем пользователя
    user_data, inventory, business_count = db.get_user(user.id)
    
    # Определяем, где вызвана команда
    if chat.type in ['group', 'supergroup']:
        welcome = f"👋 Привет, {user.first_name}!\nЯ бот-экономика для чатов!\n\n"
        welcome += "💡 Используйте меня в личных сообщениях для полного функционала:\n"
        welcome += f"👉 Напишите мне: @{context.bot.username}"
    else:
        welcome = f"""
🎮 *ДОБРО ПОЖАЛОВАТЬ, {user.first_name}!*

💰 *Ваш начальный капитал:*
• Монеты: {user_data['coins']}
• Клики: {user_data['clicks']}/50

📊 *Ваш инвентарь:*
• Обычные кейсы: {inventory.get('regular_cases', 0)}
• Золотые кейсы: {inventory.get('golden_cases', 0)}
• Бизнесы: {business_count}

🎯 *ОСНОВНЫЕ КОМАНДЫ:*
/daily - Ежедневный бонус (1000 монет)
/click - Кликер (заработать монеты)
/balance - Ваш баланс
/cases - Открыть кейсы
/casino - Играть в казино
/business - Управление бизнесом
/inventory - Ваш инвентарь
/shop - Магазин
/top - Топ игроков
/help - Помощь

⚡ *Быстрые команды в чатах:* 
!баланс - Показать баланс
!топ - Показать топ чата
        """
    
    await update.message.reply_text(
        welcome, 
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Играть", callback_data="play")],
            [InlineKeyboardButton("💰 Баланс", callback_data="balance"),
             InlineKeyboardButton("🏆 Топ", callback_data="top")]
        ])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🆘 *ПОМОЩЬ ПО КОМАНДАМ:*

*💰 Экономика:*
/start - Начать игру
/balance - Ваш баланс
/daily - Ежедневный бонус (1000 монет)
/click - Заработать кликами (1 клик = 1 монета)

*🎮 Игры:*
/casino [ставка] - Играть в казино (50/50)
/cases - Открыть кейсы
/open [тип] - Открыть кейс (regular/golden)

*🏢 Бизнес:*
/business - Ваши бизнесы
/buy_business [тип] - Купить бизнес
/collect - Собрать доход с бизнесов

*🛒 Магазин:*
/shop - Магазин предметов
/buy_case [тип] - Купить кейс

*📊 Информация:*
/top - Топ-10 игроков
/inventory - Ваш инвентарь
/profile - Ваш профиль

*⚡ Команды в чатах:*
!баланс - Показать баланс
!топ - Топ чата
!игроки - Список игроков
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /balance"""
    user = update.effective_user
    user_data, inventory, business_count = db.get_user(user.id)
    
    balance_text = f"""
💰 *БАЛАНС {user.first_name}*

*Наличные:* {user_data['coins']} монет
*В банке:* {user_data['bank']} монет
*Доступные клики:* {user_data['clicks']}/50

*📦 Инвентарь:*
• Обычные кейсы: {inventory.get('regular_cases', 0)}
• Золотые кейсы: {inventory.get('golden_cases', 0)}
• Бизнесы: {business_count}

*🎰 Казино:*
Побед: {user_data['casino_wins']}
Поражений: {user_data['casino_losses']}
    """
    
    await update.message.reply_text(balance_text, parse_mode=ParseMode.MARKDOWN)
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /daily - ежедневный бонус"""
    user = update.effective_user
    user_data, _, _ = db.get_user(user.id)
    
    # Проверяем, получал ли уже сегодня
    last_daily = user_data.get('last_daily')
    today = datetime.now().strftime('%Y-%m-%d')
    
    if last_daily == today:
        await update.message.reply_text("❌ Вы уже получали ежедневный бонус сегодня!\nПриходите завтра.")
        return
    
    # Начисляем бонус
    db.add_coins(user.id, config.DAILY_BONUS, 'daily')
    db.update_user(user.id, last_daily=today)
    
    await update.message.reply_text(
        f"🎉 *ЕЖЕДНЕВНЫЙ БОНУС!*\n\n"
        f"💰 Вы получили: {config.DAILY_BONUS} монет!\n"
        f"💳 Ваш баланс: {user_data['coins'] + config.DAILY_BONUS} монет",
        parse_mode=ParseMode.MARKDOWN
    )

async def click_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /click - кликер"""
    user = update.effective_user
    user_data, _, _ = db.get_user(user.id)
    
    if user_data['clicks'] <= 0:
        await update.message.reply_text("❌ У вас закончились клики!\nОни восстановятся через некоторое время.")
        return
    
    # Начисляем монеты за клик
    reward = random.randint(1, 5)  # Случайная награда 1-5 монет
    db.add_coins(user.id, reward, 'click')
    db.update_user(user.id, clicks=user_data['clicks'] - 1)
    
    # Случайный шанс найти кейс
    found_case = ""
    if random.random() < 0.1:  # 10% шанс
        db.add_to_inventory(user.id, 'case_regular')
        found_case = "\n🎁 Вы нашли обычный кейс!"
    
    await update.message.reply_text(
        f"🖱 *КЛИК!*\n\n"
        f"💰 Заработано: {reward} монет\n"
        f"🔋 Осталось кликов: {user_data['clicks'] - 1}\n"
        f"{found_case}",
        parse_mode=ParseMode.MARKDOWN
    )

async def casino_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /casino"""
    user = update.effective_user
    user_data, _, _ = db.get_user(user.id)
    
    if not context.args:
        await update.message.reply_text(
            "🎰 *КАЗИНО 50/50*\n\n"
            "Использование: /casino [ставка]\n\n"
            "Пример: /casino 100\n"
            "Ваш баланс: {} монет".format(user_data['coins']),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        bet = int(context.args[0])
        if bet <= 0:
            await update.message.reply_text("❌ Ставка должна быть больше 0!")
            return
        if bet > user_data['coins']:
            await update.message.reply_text(f"❌ Недостаточно монет! У вас: {user_data['coins']}")
            return
    except ValueError:
        await update.message.reply_text("❌ Используйте число для ставки!")
        return
    
    # Игра 50/50
    if random.choice([True, False]):
        # Выигрыш
        win_amount = bet * 2
        db.add_coins(user.id, win_amount, 'casino_win')
        db.update_user(user.id, casino_wins=user_data['casino_wins'] + 1)
        
        await update.message.reply_text(
            f"🎉 *ВЫ ВЫИГРАЛИ!*\n\n"
            f"💰 Ставка: {bet} монет\n"
            f"🏆 Выигрыш: {win_amount} монет\n"
            f"💳 Новый баланс: {user_data['coins'] - bet + win_amount}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Проигрыш
        db.add_coins(user.id, -bet, 'casino_loss')
        db.update_user(user.id, casino_losses=user_data['casino_losses'] + 1)
        
        await update.message.reply_text(
            f"😔 *ВЫ ПРОИГРАЛИ*\n\n"
            f"💰 Потеряно: {bet} монет\n"
            f"💳 Новый баланс: {user_data['coins'] - bet}\n\n"
            f"Удачи в следующий раз!",
            parse_mode=ParseMode.MARKDOWN
        )
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /top - топ игроков"""
    top_users = db.get_top_users(10)
    
    if not top_users:
        await update.message.reply_text("📊 Топ игроков пуст!")
        return
    
    top_text = "🏆 *ТОП-10 ИГРОКОВ*\n\n"
    for i, user in enumerate(top_users, 1):
        name = user.get('first_name', user.get('username', f'Игрок {user["user_id"]}'))
        coins = user.get('coins', 0)
        top_text += f"{i}. {name}: {coins} монет\n"
    
    await update.message.reply_text(top_text, parse_mode=ParseMode.MARKDOWN)

async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /inventory"""
    user = update.effective_user
    user_data, inventory, business_count = db.get_user(user.id)
    
    inv_text = f"""
📦 *ИНВЕНТАРЬ {user.first_name}*

*🎁 Кейсы:*
• Обычные: {inventory.get('regular_cases', 0)}
• Золотые: {inventory.get('golden_cases', 0)}

*🏢 Бизнесы:* {business_count}

*💰 Ресурсы:*
• Монеты: {user_data['coins']}
• Клики: {user_data['clicks']}/50
• В банке: {user_data['bank']}

*🛒 Чтобы открыть кейсы:* /cases
*🏢 Управление бизнесом:* /business
    """
    
    await update.message.reply_text(inv_text, parse_mode=ParseMode.MARKDOWN)

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /shop"""
    shop_text = """
🛒 *МАГАЗИН*

*🎁 Кейсы:*
• Обычный кейс - 100 монет
  Команда: /buy_case regular
  
• Золотой кейс - 1000 монет
  Команда: /buy_case golden

*🏢 Бизнесы:*
• Магазин (уровень 1) - 5000 монет
  Команда: /buy_business shop
  
• Кафе (уровень 1) - 10000 монет
  Команда: /buy_business cafe
  
• Фабрика (уровень 1) - 50000 монет
  Команда: /buy_business factory
  
• Комплекс (уровень 1) - 100000 монет
  Команда: /buy_business complex

*💡 Ваш баланс:* /balance
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Купить кейс", callback_data="shop_cases")],
        [InlineKeyboardButton("🏢 Купить бизнес", callback_data="shop_business")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance")]
    ])
    
    await update.message.reply_text(shop_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cases"""
    user = update.effective_user
    user_data, inventory, _ = db.get_user(user.id)
    
    cases_text = f"""
🎁 *ВАШИ КЕЙСЫ*

*Доступно:*
• Обычные: {inventory.get('regular_cases', 0)}
• Золотые: {inventory.get('golden_cases', 0)}

*Команды для открытия:*
/open regular - Открыть обычный кейс
/open golden - Открыть золотой кейс

*🎰 Шансы обычного кейса:*
• 50% - 10-50 монет
• 30% - 50-100 монет  
• 15% - 100-500 монет
• 5% - 500-1000 монет

*🌟 Шансы золотого кейса:*
• 40% - 500-1000 монет
• 30% - 1000-5000 монет
• 20% - 5000-10000 монет
• 10% - 10000-50000 монет
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Открыть обычный", callback_data="open_regular"),
         InlineKeyboardButton("🌟 Открыть золотой", callback_data="open_golden")],
        [InlineKeyboardButton("🛒 Купить еще", callback_data="shop")]
    ])
    
    await update.message.reply_text(cases_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def business_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /business"""
    user = update.effective_user
    
    business_text = """
🏢 *БИЗНЕС СИСТЕМА*

*Доступные бизнесы:*
1. 🏪 Магазин
   • Цена: 5000 монет
   • Доход: 100 монет/час
   • Команда: /buy_business shop

2. ☕ Кафе  
   • Цена: 10000 монет
   • Доход: 250 монет/час
   • Команда: /buy_business cafe

3. 🏭 Фабрика
   • Цена: 50000 монет
   • Доход: 1000 монет/час
   • Команда: /buy_business factory

4. 🏙️ Комплекс
   • Цена: 100000 монет
   • Доход: 2500 монет/час
   • Команда: /buy_business complex
*Управление:*
/collect - Собрать доход со всех бизнесов
/my_business - Мои бизнесы
/upgrade_business - Улучшить бизнес
    """
    
    await update.message.reply_text(business_text, parse_mode=ParseMode.MARKDOWN)

# ===================== ЧАТ КОМАНДЫ =====================

async def chat_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда !баланс для чатов"""
    user = update.effective_user
    user_data, _, _ = db.get_user(user.id)
    
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    await update.message.reply_text(
        f"💰 *{user.first_name}*\n"
        f"Монеты: {user_data['coins']}\n"
        f"Банк: {user_data['bank']}",
        parse_mode=ParseMode.MARKDOWN
    )

async def chat_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда !топ для чатов"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    top_users = db.get_top_users(5)
    
    if not top_users:
        await update.message.reply_text("📊 В чате еще нет игроков!")
        return
    
    top_text = "🏆 *ТОП ЧАТА*\n\n"
    for i, user in enumerate(top_users, 1):
        name = user.get('first_name', user.get('username', f'Игрок'))
        coins = user.get('coins', 0)
        top_text += f"{i}. {name}: {coins} монет\n"
    
    await update.message.reply_text(top_text, parse_mode=ParseMode.MARKDOWN)

# ===================== CALLBACK ОБРАБОТЧИКИ =====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "balance":
        user_data, inventory, business_count = db.get_user(user.id)
        await query.edit_message_text(
            f"💰 *Баланс:* {user_data['coins']} монет\n"
            f"🎁 *Кейсы:* {inventory.get('regular_cases', 0)} обычных, {inventory.get('golden_cases', 0)} золотых",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif query.data == "top":
        await top_command_with_query(query, context)
    
    elif query.data == "play":
        await query.edit_message_text(
            "🎮 *ВЫБЕРИТЕ ИГРУ:*\n\n"
            "💰 /daily - Ежедневный бонус\n"
            "🖱 /click - Кликер\n"
            "🎰 /casino - Казино\n"
            "🎁 /cases - Кейсы",
            parse_mode=ParseMode.MARKDOWN
        )

async def top_command_with_query(query, context):
    """Отправка топа через inline-кнопку"""
    top_users = db.get_top_users(5)
    
    if not top_users:
        await query.edit_message_text("📊 Топ игроков пуст!")
        return
    
    top_text = "🏆 *ТОП-5 ИГРОКОВ*\n\n"
    for i, user in enumerate(top_users, 1):
        name = user.get('first_name', user.get('username', f'Игрок {user["user_id"]}'))
        coins = user.get('coins', 0)
        top_text += f"{i}. {name}: {coins} монет\n"
    
    await query.edit_message_text(top_text, parse_mode=ParseMode.MARKDOWN)

# ===================== ОБРАБОТЧИК СООБЩЕНИЙ =====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text.lower()
    
    # Игнорируем команды
    if text.startswith('/') or text.startswith('!'):
        return
    
    # Простые ответы на приветствия
    if any(word in text for word in ['привет', 'hello', 'hi', 'хай']):
        await update.message.reply_text(f"👋 Привет, {update.effective_user.first_name}!")
    
    elif any(word in text for word in ['баланс', 'деньги', 'монеты']):
        await balance_command(update, context)
    
    elif any(word in text for word in ['топ', 'рейтинг']):
        await top_command(update, context)

# ===================== FLASK ДЛЯ WEBHOOK =====================

@app.route('/')
def home():
    return "🤖 Бот экономика работает!"

@app.route('/health')
def health():
    return "OK", 200

# ===================== ЗАПУСК БОТА =====================
def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(config.TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("click", click_command))
    application.add_handler(CommandHandler("casino", casino_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("inventory", inventory_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("cases", cases_command))
    application.add_handler(CommandHandler("business", business_command))
    
    # Команды для чатов
    application.add_handler(MessageHandler(filters.Regex(r'^!баланс$'), chat_balance))
    application.add_handler(MessageHandler(filters.Regex(r'^!топ$'), chat_top))
    application.add_handler(MessageHandler(filters.Regex(r'^!игроки$'), chat_top))
    
    # Inline кнопки
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("🤖 Бот запускается...")
    
    # Для bothost.ru используем polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if name == 'main':
    # Запускаем Flask в отдельном потоке
    import threading
    
    def run_flask():
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота
    main()
