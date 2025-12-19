import os
import logging
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(name)

# Получаем токен из переменных окружения bothost.ru
TOKEN = os.getenv('API_TOKEN')
if not TOKEN:
    logger.error("❌ API_TOKEN не найден в переменных окружения!")
    exit(1)

# ===================== БАЗА ДАННЫХ В КОДЕ =====================
# ВСЕ ДАННЫЕ ХРАНЯТСЯ ЗДЕСЬ! (объявляем ПЕРЕД функциями)
USERS_DATABASE = {}
# или если хотите тестовых пользователей:
# USERS_DATABASE = {
#     "6956241293": {
#         "username": "test_user",
#         "first_name": "Тест",
#         "coins": 1000,
#         "bank": 0
#     }
# }

def save_database_to_file():
    """Сохранить базу данных в отдельный файл (для резервной копии)"""
    try:
        with open('database_backup.py', 'w', encoding='utf-8') as f:
            f.write('# АВТОСОХРАНЕННАЯ БАЗА ДАННЫХ БОТА\n')
            f.write('# НЕ РЕДАКТИРУЙТЕ ВРУЧНУЮ!\n\n')
            f.write('USERS_DATABASE = ')
            f.write(json.dumps(USERS_DATABASE, ensure_ascii=False, indent=2))
            f.write('\n\n# Конец базы данных')
        logger.info(f"💾 База сохранена в файл: {len(USERS_DATABASE)} пользователей")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения базы: {e}")

def load_database_from_file():
    """Загрузить базу данных из файла при запуске"""
    global USERS_DATABASE
    try:
        if os.path.exists('database_backup.py'):
            with open('database_backup.py', 'r', encoding='utf-8') as f:
                content = f.read()
                if 'USERS_DATABASE = ' in content:
                    # Безопасное извлечение данных
                    import ast
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'USERS_DATABASE = ' in line:
                            db_str = '\n'.join(lines[i:])
                            # Находим начало и конец словаря
                            start = db_str.find('{')
                            end = db_str.rfind('}') + 1
                            if start != -1 and end != -1:
                                db_dict_str = db_str[start:end]
                                USERS_DATABASE = ast.literal_eval(db_dict_str)
                                logger.info(f"✅ Загружено {len(USERS_DATABASE)} пользователей из файла")
                                break
    except Exception as e:
        logger.warning(f"Не удалось загрузить базу: {e}")
        USERS_DATABASE = {}

# Загружаем базу при старте
load_database_from_file()

def get_user(user_id):
    """Получить данные пользователя"""
    return USERS_DATABASE.get(str(user_id))

def save_user(user_data):
    """Сохранить/обновить данные пользователя"""
    user_id = str(user_data['user_id'])
    
    if user_id not in USERS_DATABASE:
        # Новый пользователь
        USERS_DATABASE[user_id] = {
            'user_id': user_data['user_id'],
            'username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'coins': 1000,  # Стартовый баланс
            'bank': 0,
            'last_daily': None,
            'last_work': None,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # Сохраняем при добавлении нового пользователя
        save_database_to_file()
    else:
        # Обновляем существующего
USERS_DATABASE[user_id].update({
            'username': user_data.get('username') or USERS_DATABASE[user_id].get('username'),
            'first_name': user_data.get('first_name') or USERS_DATABASE[user_id].get('first_name'),
            'last_name': user_data.get('last_name') or USERS_DATABASE[user_id].get('last_name'),
            'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return True

def add_coins(user_id, amount):
    """Добавить монеты пользователю"""
    user_id_str = str(user_id)
    
    if user_id_str in USERS_DATABASE:
        USERS_DATABASE[user_id_str]['coins'] = USERS_DATABASE[user_id_str].get('coins', 0) + amount
        USERS_DATABASE[user_id_str]['last_active'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Сохраняем при изменении баланса
        save_database_to_file()
        return USERS_DATABASE[user_id_str]['coins']
    return None

def get_balance(user_id):
    """Получить баланс пользователя"""
    user = get_user(user_id)
    if user:
        return user.get('coins', 0), user.get('bank', 0)
    return 0, 0

def get_top_users(limit=10):
    """Получить топ пользователей по монетам"""
    sorted_users = sorted(
        USERS_DATABASE.items(),
        key=lambda x: x[1].get('coins', 0),
        reverse=True
    )[:limit]
    
    return [
        {
            'user_id': user_id,
            'username': data.get('username'),
            'first_name': data.get('first_name'),
            'coins': data.get('coins', 0)
        }
        for user_id, data in sorted_users
    ]

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
application.add_handler(CommandHandler("work", work_command))
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

