import os
import logging
import json
import random
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===================== НАСТРОЙКИ =====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(name)

TOKEN = os.getenv('API_TOKEN')
if not TOKEN:
    logger.error("❌ API_TOKEN не найден!")
    exit(1)

# ===================== ПРОСТАЯ БАЗА В ПАМЯТИ =====================
# ВСЕ ДАННЫЕ ЗДЕСЬ
users_db = {}  # ← ПРОСТАЯ переменная, никаких ошибок!

def load_db():
    """Загрузить базу из файла"""
    global users_db
    try:
        if os.path.exists('db_backup.txt'):
            with open('db_backup.txt', 'r', encoding='utf-8') as f:
                users_db = json.load(f)
            logger.info(f"✅ База загружена: {len(users_db)} пользователей")
    except:
        users_db = {}

def save_db():
    """Сохранить базу в файл"""
    try:
        with open('db_backup.txt', 'w', encoding='utf-8') as f:
            json.dump(users_db, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")

# Загружаем при старте
load_db()

def get_user(user_id):
    """Получить пользователя"""
    return users_db.get(str(user_id))

def save_user(user_id, username="", first_name=""):
    """Сохранить пользователя"""
    user_id_str = str(user_id)
    
    if user_id_str not in users_db:
        users_db[user_id_str] = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'coins': 1000,
            'bank': 0,
            'last_daily': None,
            'last_work': None,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_db()  # Сохраняем нового пользователя
        return True
    return False

def add_coins(user_id, amount):
    """Добавить монеты"""
    user_id_str = str(user_id)
    if user_id_str in users_db:
        users_db[user_id_str]['coins'] = users_db[user_id_str].get('coins', 0) + amount
        save_db()  # Сохраняем изменение
        return users_db[user_id_str]['coins']
    return 0

def get_balance(user_id):
    """Получить баланс"""
    user = get_user(user_id)
    if user:
        return user.get('coins', 0), user.get('bank', 0)
    return 0, 0


# ===================== КОМАНДЫ БОТА =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем и сохраняем пользователя
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }
    
    if not get_user(user.id):
        save_user(user_data)
        welcome_bonus = True
    else:
        welcome_bonus = False
        save_user(user_data)

    # Создаем ссылку на профиль пользователя
    username = f"@{user.username}" if user.username else user.first_name
    user_mention = f'<a href="tg://user?id={user.id}">{username}</a>'
    
    # Получаем баланс
    coins, bank = get_balance(user.id)
    
    welcome_text = f"{user_mention}, приветствую 🤚🏻\n\n"
    welcome_text += f"🎗 Меня зовут PGB, я многофункциональный игровой развлекательный бот 🎗\n\n"
    welcome_text += f"🎮 В боте вы сможете поиграть во множество игр, зарабатывать валюты, копать руды, завести питомца, открывать кейсы и многое другое! 🎮\n\n"
    welcome_text += f"💥 Имеются различные имущества, статусы, работы, которые вы сможете купить и улучшать 💥\n\n"
    
    if welcome_bonus:
        welcome_text += f"🎁 Вам начислен стартовый бонус: 1000 монет!\n\n"
    
   
    welcome_text += f"❇️ Добро пожаловать! ❇️"

    await update.message.reply_text(welcome_text, parse_mode="HTML")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /balance - показать баланс"""
    user = update.effective_user
    
    # Получаем или создаем пользователя
    if not get_user(user.id):
        save_user({
            'user_id': user.id,
            'username': user.username,
'first_name': user.first_name,
            'last_name': user.last_name
        })
    
    coins, bank = get_balance(user.id)
    total = coins + bank
    
    balance_text = f"💰 {user.first_name}, <b>ваш баланс:</b>\n\n"
    balance_text += f"💵 <b>Монеты:</b> {coins}\n"
    balance_text += f"🏦 <b>В банке:</b> {bank}\n"
    balance_text += f"📊 <b>Всего:</b> {total} монет\n\n"
    
    if coins < 100:
        balance_text += f"💡 Используйте /work чтобы заработать!"
    elif coins > 5000:
        balance_text += f"🎉 Отличный результат!"

    await update.message.reply_text(balance_text, parse_mode="HTML")

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /daily - ежедневный бонус"""
    user = update.effective_user
    
    # Проверяем, получал ли уже сегодня
    user_data = get_user(user.id)
    if not user_data:
        save_user({
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
        user_data = get_user(user.id)
    
    last_daily = user_data.get('last_daily')
    today = datetime.now().strftime('%Y-%m-%d')
    
    if last_daily == today:
        await update.message.reply_text(
            "❌ <b>Вы уже получали ежедневный бонус сегодня!</b>\n"
            "Приходите завтра за новым бонусом! 🗓️",
            parse_mode="HTML"
        )
        return
    
    # Начисляем бонус
    import random
    bonus_amount = random.randint(100, 1000)
    
    # Обновляем баланс
    new_balance = add_coins(user.id, bonus_amount)
    
    # Обновляем дату получения бонуса
    USERS_DATABASE[str(user.id)]['last_daily'] = today
    
    await update.message.reply_text(
        f"🎉 <b>ЕЖЕДНЕВНЫЙ БОНУС!</b>\n\n"
        f"💰 <b>Вы получили:</b> {bonus_amount} монет!\n"
        f"💳 <b>Ваш баланс:</b> {new_balance} монет\n\n"
        f"🔄 Следующий бонус через 24 часа!",
        parse_mode="HTML"
    )

async def work_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /work - заработать монеты"""
    user = update.effective_user
    
    # Проверяем, не работал ли слишком часто (раз в 5 минут)
    user_data = get_user(user.id)
    if not user_data:
        save_user({
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
        user_data = get_user(user.id)
    
    last_work = user_data.get('last_work')
    if last_work:
        last_work_dt = datetime.strptime(last_work, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        diff = (now - last_work_dt).seconds
        
        if diff < 300:  # 5 минут = 300 секунд
            minutes_left = 5 - (diff // 60)
            await update.message.reply_text(
                f"⏳ <b>Отдохните немного!</b>\n\n"
                f"Вы уже работали недавно.\n"
                f"Следующая работа через {minutes_left} минут.",
                parse_mode="HTML"
            )
            return
    
    # Начисляем заработок
    import random
    work_amount = random.randint(50, 250)
    
    # Обновляем баланс
    new_balance = add_coins(user.id, work_amount)
    
    # Обновляем время последней работы
    USERS_DATABASE[str(user.id)]['last_work'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Случайные сообщения о работе
    jobs = [
        "поработали в кафе ☕",
        "сделали заказ в доставке 🛵",
        "поработали программистом 💻",
        "построили дом 🏗️",
        "продали товары в магазине 🛒",
        "собрали урожай на ферме 🌾"
    ]
    
    job = random.choice(jobs)
    
    await update.message.reply_text(
        f"💼 <b>ХОРОШАЯ РАБОТА!</b>\n\n"
        f"Вы {job}\n"
        f"💰 <b>Заработано:</b> {work_amount} монет\n"
        f"💳 <b>Ваш баланс:</b> {new_balance} монет\n\n"
        f"🔄 Следующая работа через 5 минут",
        parse_mode="HTML"
    )
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /top - топ игроков"""
    top_users = get_top_users(10)
    
    if not top_users:
        await update.message.reply_text("📊 Топ игроков пуст!")
        return
    
    top_text = "🏆 <b>ТОП-10 ИГРОКОВ ПО МОНЕТАМ</b>\n\n"
    for i, user in enumerate(top_users, 1):
        name = user.get('first_name') or user.get('username') or f"Игрок {user['user_id']}"
        coins = user.get('coins', 0)
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
        top_text += f"{medal} {name}: <b>{coins}</b> монет\n"
    
    total_users = len(USERS_DATABASE)
    total_coins = sum(user.get('coins', 0) for user in USERS_DATABASE.values())
    
    top_text += f"\n📊 <b>Статистика:</b>\n"
    top_text += f"👥 Всего игроков: {total_users}\n"
    top_text += f"💰 Всего монет в игре: {total_coins}"

    await update.message.reply_text(top_text, parse_mode="HTML")

async def save_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /save_db - сохранить базу данных"""
    save_database_to_file()
    await update.message.reply_text(
        f"💾 <b>База данных сохранена!</b>\n\n"
        f"📁 Файл: database_backup.py\n"
        f"👥 Пользователей: {len(USERS_DATABASE)}\n"
        f"💰 Всего монет: {sum(user.get('coins', 0) for user in USERS_DATABASE.values())}",
        parse_mode="HTML"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика бота"""
    total_users = len(USERS_DATABASE)
    total_coins = sum(user.get('coins', 0) for user in USERS_DATABASE.values())
    active_today = sum(
        1 for user in USERS_DATABASE.values()
        if user.get('last_active', '').startswith(datetime.now().strftime('%Y-%m-%d'))
    )
    
    stats_text = "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
    stats_text += f"👥 <b>Всего пользователей:</b> {total_users}\n"
    stats_text += f"💰 <b>Всего монет в игре:</b> {total_coins}\n"
    stats_text += f"📈 <b>Активных сегодня:</b> {active_today}\n\n"
    stats_text += f"💾 <b>База данных:</b> В памяти\n"
    stats_text += f"🔄 <b>Автосохранение:</b> При изменениях\n\n"
    stats_text += f"⚡ Данные сохраняются при обновлении кода!"

    await update.message.reply_text(stats_text, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = "🆘 <b>ПОМОЩЬ ПО КОМАНДАМ</b>\n\n"
    
    help_text += "💰 <b>ЭКОНОМИКА:</b>\n"
    help_text += "• /start - Начать игру\n"
    help_text += "• /balance - Ваш баланс монет\n"
    help_text += "• /daily - Ежедневный бонус (100-1000 монет)\n"
    help_text += "• /work - Заработать монеты (50-250 монет)\n\n"
    
    help_text += "📊 <b>ИНФОРМАЦИЯ:</b>\n"
    help_text += "• /top - Топ игроков\n"
    help_text += "• /stats - Статистика бота\n"
    help_text += "• /save_db - Сохранить базу\n"
    help_text += "• /ping - Проверка работы\n\n"
    
    help_text += "🎮 <b>В РАЗРАБОТКЕ:</b>\n"
    help_text += "• /casino - Казино\n"
    help_text += "• Магазин предметов\n"
    help_text += "• Кейсы и инвентарь"

    await update.message.reply_text(help_text, parse_mode="HTML")

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
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("daily", daily_command))
        application.add_handler(CommandHandler("top", top_command))
        application.add_handler(CommandHandler("save_db", save_db_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ping", ping_command))
        
        logger.info(f"🤖 Бот запускается. Пользователей в БД: {len(USERS_DATABASE)}")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    main()



