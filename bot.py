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
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения bothost.ru
TOKEN = os.getenv('API_TOKEN')
if not TOKEN:
    logger.error("❌ API_TOKEN не найден в переменных окружения!")
    exit(1)

# Файл для хранения данных пользователей (вместо БД)
DATA_FILE = 'users_data.json'

def load_users_data():
    """Загрузить данные пользователей из файла"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
    return {}

def save_users_data(data):
    """Сохранить данные пользователей в файл"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        return False

def get_user(user_id):
    """Получить данные пользователя"""
    data = load_users_data()
    return data.get(str(user_id))

def save_user(user_data):
    """Сохранить/обновить данные пользователя"""
    data = load_users_data()
    user_id = str(user_data['user_id'])
    
    # Если пользователь уже есть, обновляем только отсутствующие поля
    if user_id in data:
        data[user_id].update({
            'username': user_data.get('username', data[user_id].get('username')),
            'first_name': user_data.get('first_name', data[user_id].get('first_name')),
            'last_name': user_data.get('last_name', data[user_id].get('last_name'))
        })
    else:
        # Создаем нового пользователя с начальным балансом
        data[user_id] = {
            'user_id': user_data['user_id'],
            'username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'coins': 1000,  # Начальный баланс
            'bank': 0,      # Деньги в банке
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_active': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    return save_users_data(data)

def add_coins(user_id, amount):
    """Добавить монеты пользователю"""
    data = load_users_data()
    user_id_str = str(user_id)
    
    if user_id_str in data:
        data[user_id_str]['coins'] = data[user_id_str].get('coins', 0) + amount
        data[user_id_str]['last_active'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_users_data(data)
        return data[user_id_str]['coins']
    return None

def get_balance(user_id):
    """Получить баланс пользователя"""
    user = get_user(user_id)
    if user:
        return user.get('coins', 0), user.get('bank', 0)
    return 0, 0

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
        # Обновляем последнюю активность
        save_user(user_data)

    # Создаем ссылку на профиль пользователя
    username = f"@{user.username}" if user.username else user.first_name
    user_mention = f'<a href="tg://user?id={user.id}">{username}</a>'
    
    # Получаем баланс
    coins, bank = get_balance(user.id)
    
    welcome_text =  f"{user_mention}, приветствую 🤚🏻\n\n"
    welcome_text += f"🎗 Меня зовут PGB, я многофункциональный игровой развлекательный бот 🎗\n\n"
    welcome_text += f"🎮 В боте вы сможете поиграть во множество игр, зарабатывать валюты, копать руды, завести питомца, открывать кейсы и многое другое! 🎮\n\n"
    welcome_text += f"💥 Имеются различные имущества, статусы, работы, которые вы сможете купить и улучшать 💥\n\n"
    
    if welcome_bonus:
        welcome_text += f"🎁 <b>Вам начислен стартовый бонус: 1000 монет!</b>\n\n"
    
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
    
    balance_text = f"💰 <b>БАЛАНС {user.first_name}</b>\n\n"
    balance_text += f"🪙 <b>Наличные:</b> {coins} монет\n"
    balance_text += f"🏦 <b>В банке:</b> {bank} монет\n"
    balance_text += f"📊 <b>Всего:</b> {total} монет\n\n"
    
    if coins < 100:
        balance_text += f"💡 <i>Совет: используйте /work чтобы заработать больше монет!</i>"
    elif coins < 1000:
        balance_text += f"💡 <i>Хороший старт! Попробуйте /daily за ежедневным бонусом!</i>"
    else:
        balance_text += f"💡 <i>Отлично! Можете сохранить деньги в банке!</i>"

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
    
    # Начисляем бонус (случайный от 50 до 500 монет)
    import random
    bonus_amount = random.randint(100, 1000)
    
    # Обновляем баланс
    new_balance = add_coins(user.id, bonus_amount)
    
    # Обновляем дату получения бонуса
    data = load_users_data()
    data[str(user.id)]['last_daily'] = today
    save_users_data(data)
    
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
    
    # Начисляем заработок (случайный от 10 до 100 монет)
    import random
    work_amount = random.randint(50, 250)
    
    # Обновляем баланс
    new_balance = add_coins(user.id, work_amount)
    
    # Обновляем время последней работы
    data = load_users_data()
    data[str(user.id)]['last_work'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_users_data(data)
    
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = "🆘 <b>ПОМОЩЬ ПО КОМАНДАМ</b>\n\n"
    
    help_text += "💰 <b>ЭКОНОМИКА:</b>\n"
    help_text += "• /start - Начать игру\n"
    help_text += "• /balance - Ваш баланс монет\n"
    help_text += "• /daily - Ежедневный бонус (100-1000 монет)\n"
    help_text += "• /work - Заработать монеты (50-250 монет)\n\n"
    
    help_text += "🎮 <b>РАЗВЛЕЧЕНИЯ:</b>\n"
    help_text += "• /casino [ставка] - Играть в казино\n"
    help_text += "• /roll [число] - Угадать число\n"
    help_text += "• /coin - Орел или решка\n\n"
    
    help_text += "📊 <b>ИНФОРМАЦИЯ:</b>\n"
    help_text += "• /top - Топ игроков по монетам\n"
    help_text += "• /profile - Ваш профиль\n"
    help_text += "• /ping - Проверка работы бота\n\n"
    
    help_text += "⚡ <b>В РАЗРАБОТКЕ:</b>\n"
    help_text += "• Магазин предметов\n"
    help_text += "• Система бизнесов\n"
    help_text += "• Кейсы и инвентарь\n"
    help_text += "• Питомцы и дома"

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
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ping", ping_command))
        
        logger.info(f"🤖 Бот запускается с токеном: {TOKEN[:10]}...")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
if __name__ == '__main__':  # ← ИСПРАВЛЕНО: ДВОЙНЫЕ ПОДЧЕРКИВАНИЯ!
    main()



