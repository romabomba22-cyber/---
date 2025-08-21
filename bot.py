import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters 
import sqlite3
from datetime import datetime, timedelta
import random
from functools import wraps
from telegram import  InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler  # Добавьте этот импорт
from typing import Union
from telegram import  CallbackQuery
from telegram.ext import  CallbackContext
from telegram.ext import Application

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from flask import Flask
import threading
import time
import traceback
import sqlite3
import asyncio


app = Flask(__name__)

# Замените на ваш токен
TOKEN = "7810592518:AAEk2sbprah37xVzqNdA2wuuxtuWWHW9PLk7810592518:AAEk2sbprah37xVzqNdA2wuuxtuWWHW9PLk"

def st(update: Update, context: CallbackContext):
    update.message.reply_text('Бот работает 24/7!')

# Эндпоинт для UptimeRobot
@app.route('/')
def home():
    return "Бот в сети!"




    

    


# Глобальная переменная для хранения кликов (временное решение)
user_clicks = {}
# Глобальная переменная для банка казино (кеширование)
CASINO_BANK = 0



# Настройки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMINS = [6956241293]  # Your Telegram ID
DB_NAME = 'bot.db'

def init_db():
    """Инициализация базы данных с правильным синтаксисом"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Удаляем старые таблицы (если нужно пересоздать)
        cursor.execute("DROP TABLE IF EXISTS inventory")
        cursor.execute("DROP TABLE IF EXISTS businesses")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS casino_bank")

        # Единая таблица пользователей (исправленная версия)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 100,
            balance INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 50,
            last_daily TEXT,
            bank INTEGER DEFAULT 0,
            
            registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            casino_bank INTEGER DEFAULT 0  # Добавлена запятая и переименовано поле
        )
        ''')

        # Таблица инвентаря (убраны дублирующие поля)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            regular_cases INTEGER DEFAULT 0,
            golden_cases INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        ''')

        # Таблица бизнесов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            user_id INTEGER,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('shop','cafe','factory','complex')),
            area INTEGER DEFAULT 1,
            price_per_m2 INTEGER NOT NULL,
            purchased_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        ''')

        # Таблица банка казино (отдельная)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS casino_bank (
            id INTEGER PRIMARY KEY DEFAULT 1,
            balance INTEGER DEFAULT 0
        )
        ''')

        # Инициализация банка
        cursor.execute('INSERT OR IGNORE INTO casino_bank (id, balance) VALUES (1, 0)')
        conn.commit()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {e}")
        raise
    finally:
        if conn:
            conn.close()







def get_user(user_id):
    """Получение всех данных пользователя с обработкой ошибок"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Основные данные пользователя
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            return None

        # Данные инвентаря
        cursor.execute('SELECT regular_cases, golden_cases FROM inventory WHERE user_id = ?', (user_id,))
        inventory_data = cursor.fetchone()

        return {
            'user_id': user_data[0],
            'username': user_data[1],
            'coins': user_data[2],
            'clicks': user_data[3],
            'last_daily': user_data[4],
            'bank': user_data[5] if len(user_data) > 5 else 0,
            'regular_cases': inventory_data[0] if inventory_data else 0,
            'golden_cases': inventory_data[1] if inventory_data else 0
        }

    except sqlite3.Error as e:
        print(f"Ошибка SQL в get_user: {e}")
        return None
    except Exception as e:
        print(f"Неизвестная ошибка в get_user: {e}")
        return None
    finally:
        if conn:
            conn.close()


def save_user(user):
    """Сохранение данных пользователя с транзакцией"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Начало транзакции
        cursor.execute("BEGIN TRANSACTION")

        # Обновление основной информации
        cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, coins, clicks, last_daily, bank)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user['user_id'],
            user.get('username'),
            user.get('coins', 100),
            user.get('clicks', 0),
            user.get('last_daily'),
            user.get('bank', 0)
        ))

        # Обновление инвентаря
        cursor.execute('''
        INSERT OR REPLACE INTO inventory 
        (user_id, regular_cases, golden_cases)
        VALUES (?, ?, ?)
        ''', (
            user['user_id'],
            user.get('regular_cases', 0),
            user.get('golden_cases', 0)
        ))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"Ошибка SQL в save_user: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"Неизвестная ошибка в save_user: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def admin_only(func):
    """Общий декоратор для проверки прав"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if update.effective_user.id not in ADMINS:
                await update.message.reply_text("🔐 Команда только для администраторов")
                return
            return await func(update, context)
        except Exception as e:
            print(f"ADMIN_CHECK ERROR: {traceback.format_exc()}")
            await update.message.reply_text("⚠️ Ошибка проверки прав")
    return wrapper

@admin_only
async def add_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдача монет"""
    try:
        if len(context.args) != 2:
            await update.message.reply_text(
                "ℹ️ Формат: /add_coins <ID> <количество>\n"
                "Пример: /add_coins 12345 100"
            )
            return

        user_id = int(context.args[0])
        coins = int(context.args[1])

        user_data = get_user(user_id) or {'user_id': user_id, 'coins': 0}
        user_data['coins'] += coins

        if not save_user(user_data):
            raise Exception("Ошибка сохранения")

        await update.message.reply_text(
            f"✅ Выдано {coins} монет\n"
            f"👤 ID: {user_id}\n"
            f"💰 Баланс: {user_data['coins']}"
        )

    except ValueError:
        await update.message.reply_text("❌ Некорректные аргументы")
    except Exception as e:
        print(f"COINS_ERROR: {traceback.format_exc()}")
        await update.message.reply_text("⚠️ Ошибка выдачи монет")

# 3. Команда выдачи кликов (полный рабочий вариант)
@admin_only
async def add_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print("Команда add_clicks вызвана")  # Логирование для отладки

        # Проверка аргументов
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "ℹ️ Формат: /add_clicks <ID> <количество>\n"
                "Пример: /add_clicks 12345 100"
            )
            return

        user_id = int(context.args[0])
        clicks = int(context.args[1])

        # Получаем или создаем пользователя
        user_data = get_user(user_id) or {
            'user_id': user_id,
            'clicks': 0,
            'coins': 100  # Стандартный баланс
        }

        # Обновляем клики
        user_data['clicks'] = user_data.get('clicks', 0) + clicks

        # Сохраняем с проверкой
        if not save_user(user_data):
            raise Exception("Ошибка сохранения кликов")

        # Успешный ответ
        response = (
            f"✅ Выдано {clicks} кликов пользователю {user_id}\n"
            f"🖱 Новый баланс: {user_data['clicks']}"
        )
        await update.message.reply_text(response)

    except ValueError:
        await update.message.reply_text("❌ ID и количество должны быть числами")
    except Exception as e:
        print(f"ADD_CLICKS ERROR: {traceback.format_exc()}")
        await update.message.reply_text("⚠️ Критическая ошибка при выдаче кликов")





    
        



# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_user(user.id):
        save_user({'user_id': user.id, 'username': user.username})

    # Создаем ссылку на профиль пользователя (используем HTML для надежности)
    username = f"@{user.username}" if user.username else user.first_name
    user_mention = f'<a href="tg://user?id={user.id}">{username}</a>'

    await update.message.reply_text(
        f"🤚🏻 {user_mention}, приветствую 🤚🏻\n\n"
        f"🎗 Меня зовут PGB, я многофункциональный игровой развлекательный бот 🎗\n\n"
        f"🎮 В боте ты сможешь поиграть во множество игр. Имеются различные дома, машины, телефоны, яхты, самолёты, которые ты можешь купить и улучшать 🎮\n\n"
        f"📌 Подробнее познакомиться с ботом ты можешь введя команду /help 📌\n\n"
        f"❇️ Добро пожаловать! ❇️",
        parse_mode="HTML"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Команды:\n/start\n/help\n/daily\n/balance")


async def casino_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        # Формируем обращение к пользователю
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        text = update.message.text.strip().lower()

        # Проверка команды
        if not text.startswith('казино '):
            return

        # Получение баланса из БД
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()

                # Создаем таблицу банка казино, если ее нет
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS casino_bank (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        balance INTEGER DEFAULT 0
                    )
                """)

                # Инициализируем банк, если он пустой
                cursor.execute("INSERT OR IGNORE INTO casino_bank (id, balance) VALUES (1, 0)")

                # Получаем баланс пользователя
                cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
                row = cursor.fetchone()

                if not row:
                    await update.message.reply_text(
                        f"❌ {mention}, ваш профиль не найден! Напишите /start",
                        parse_mode="HTML"
                    )
                    return

                current_balance = row[0]

                # Получаем текущий баланс банка казино
                cursor.execute("SELECT balance FROM casino_bank WHERE id=1")
                casino_bank_balance = cursor.fetchone()[0]

                conn.commit()

        except Exception as e:
            print(f"Ошибка БД: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка доступа к данным",
                parse_mode="HTML"
            )
            return

        # Обработка ставки
        try:
            bet_text = text.split()[1]
            bet = current_balance if bet_text.lower() in ["всё", "все"] else int(bet_text)

            if bet < 5:
                await update.message.reply_text(
                    f"❌ {mention}, <b>ставка не может быть меньше 5 монет</b> ❌",
                    parse_mode="HTML"
                )
                return
        except:
            await update.message.reply_text(
                f"🎰 {mention}, <b>используйте:</b>\n\n"
                f"⬜ <code>казино 100</code> <b>- конкретная ставка</b>\n\n"
                f"⬜ <code>казино всё</code> или <code>казино все</code> <b>- поставить весь баланс</b>\n\n",
                parse_mode="HTML"
            )
            return

        if bet > current_balance:
            await update.message.reply_text(
                f"❌ {mention}, <b>на балансе недостаточно монет</b> ❌\n\n"
                f"💰 <b>Ваш баланс:</b> {current_balance} <b>монет</b> 💰",
                parse_mode="HTML"
            )
            return

        # Игровая логика
        outcomes = [
            {"mult": -1.0, "text": "😭 сумма вашей ставки сгорела <b>(x0)</b>", "prob": 8},
            {"mult": -0.6, "text": "😕 вы проиграли <b>60%</b> ставки <b>(x0.60)</b>", "prob": 17},
            {"mult": -0.30, "text": "😣 вы проиграли <b>30%</b> ставки <b>(x0.30)</b>", "prob": 17},
            {"mult": -0.80, "text": "🙄 вы проиграли <b>80%</b> ставки <b>(x0.80)</b>", "prob": 17},
            {"mult": 0.60, "text": "😜 вы выиграли <b>60%</b> ставки <b>(x0.60)</b>", "prob": 16},
            {"mult": 0.30, "text": "🙂 вы выиграли <b>30%</b> ставки <b>(x0.30)</b>", "prob": 17},
            {"mult": 0, "text": "😶 сумма вашей ставки сохранена <b>(x0)</b>", "prob": 17},
            {"mult": 0.80, "text": "😍 вы выиграли <b>80%</b> ставки <b>(x0.80)</b>", "prob": 16},
            {"mult": 1.0, "text": "😊 вы выиграли <b>100%</b> ставки <b>(x1)</b>", "prob": 12},
            {"mult": 2.0, "text": "💰 вы выиграли <b>200%</b> ставки <b>(x2)</b>", "prob": 5},
            {"mult": 1.5, "text": "🤑 вы выиграли <b>150%</b> ставки <b>(x1.50)</b>", "prob": 7},
            {"mult": 5.0, "text": "🔥 вы выиграли <b>ДЖЕКПОТ x5</b>", "prob": 2},
            {"mult": -0.20, "text": "🤥 вы проиграли <b>20%</b> ставки <b>(x0.20)</b>", "prob": 14},
            {"mult": -0.10, "text": "😫 вы проиграли <b>10%</b> ставки <b>(x0.10)</b>", "prob": 14},
        ]

        chosen = random.choices(outcomes, weights=[o["prob"] for o in outcomes], k=1)[0]
        win = int(bet * chosen["mult"])
        new_balance = current_balance + win

        # Обновление балансов
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()

                # Обновляем баланс пользователя
                cursor.execute(
                    "UPDATE users SET coins=? WHERE user_id=?",
                    (new_balance, user.id)
                )

                # Если проигрыш - добавляем в банк казино
                if win < 0:
                    lost_amount = abs(win)
                    cursor.execute(
                        "UPDATE casino_bank SET balance=balance+? WHERE id=1",
                        (lost_amount,)
                    )

                conn.commit()

                # Получаем обновленный баланс банка казино
                cursor.execute("SELECT balance FROM casino_bank WHERE id=1")
                casino_bank_balance = cursor.fetchone()[0]

        except Exception as e:
            print(f"Ошибка обновления: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка сохранения результата",
                parse_mode="HTML"
            )
            return

        # Генерация слотов
        slots = ["🍒", "🍋", "🍊", "🍇", "💎", "🍕"]
        reels = [random.choice(slots), random.choice(slots), random.choice(slots)]

        if chosen["mult"] > 0:
            reels[1] = reels[0]
            if chosen["mult"] >= 2:
                reels[2] = reels[0]

        # Функция форматирования чисел
        def format_number(amount):
            return "{:,.0f}".format(amount).replace(",", " ")

        # Формирование результата
        result_msg = (
            f"🎰 {mention}, {chosen['text']} \n\n"
            f"┏━━━━━━━━━━━┓\n"
            f"┃  {reels[0]}  |  {reels[1]}  |  {reels[2]}  ┃\n"
            f"┗━━━━━━━━━━━┛\n\n"
        )

        if win > 0:
            result_msg += f"🔺️ Итог: <b>+{format_number(win)}</b> монет\n\n"
        elif win < 0:
            result_msg += f"🔻 Итог: <b>-{format_number(abs(win))}</b> монет\n\n"
        else:
            result_msg += f"🌸 Итог: <b>+0</b> монет\n\n"

        result_msg += (
            f"💰 <b>Ваш баланс:</b> {format_number(new_balance)} <b>монет</b> 💰\n\n"
            f"🏦 <b>Банк казино:</b> {format_number(casino_bank_balance)} <b>монет</b> 🏦\n\n"
        )

        await update.message.reply_text(
            result_msg,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text(
            f"⚠️ {mention}, техническая ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )

async def rob_bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для ограбления банка казино с разными исходами"""
    try:
        # Проверка входящего сообщения
        if not update or not update.message:
            return

        user = update.effective_user
        if not user:
            return

        # Форматирование имени пользователя
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            # Проверка времени последней попытки
            cursor.execute("""
                SELECT last_attempt FROM robbery_attempts 
                WHERE user_id = ?
            """, (user.id,))

            attempt_data = cursor.fetchone()

            if attempt_data:
                last_attempt = datetime.fromisoformat(attempt_data[0])
                if (datetime.now() - last_attempt) < timedelta(hours=12):
                    next_try = last_attempt + timedelta(hours=12)
                    await update.message.reply_text(
                        f"⏳ {mention}, следующая попытка доступна после:\n"
                        f"<b>{next_try.strftime('%d.%m.%Y в %H:%M')}</b>",
                        parse_mode="HTML"
                    )
                    return

            # Проверка баланса банка
            cursor.execute("SELECT balance FROM casino_bank WHERE id = 1")
            bank_balance = cursor.fetchone()[0]

            if bank_balance <= 0:
                await update.message.reply_text(
                    f"🏦 {mention}, банк казино пуст!",
                    parse_mode="HTML"
                )
                return

            # Система вероятностей (55% успех, 45% неудача)
            robbery_outcomes = [
                {"chance": 0.25, "min_percent": 0.05, "max_percent": 0.10, "emoji": "💰", "msg": "Вы украли {amount} монет ({percent}%)"},
                {"chance": 0.15, "min_percent": 0.10, "max_percent": 0.20, "emoji": "🎉", "msg": "Крупный куш! {amount} монет ({percent}%)"},
                {"chance": 0.10, "min_percent": 0.20, "max_percent": 0.30, "emoji": "🔥", "msg": "ДЖЕКПОТ! {amount} монет ({percent}%)"},
                {"chance": 0.05, "min_percent": 0.01, "max_percent": 0.05, "emoji": "🤑", "msg": "Мелкая кража: {amount} монет ({percent}%)"},
                {"chance": 0.45, "emoji": "🚨", "msg": "Ограбление провалилось!"}
            ]

            outcome = random.choices(
                robbery_outcomes,
                weights=[o["chance"] for o in robbery_outcomes],
                k=1
            )[0]

            if "min_percent" in outcome:  # Успешное ограбление
                percent = random.uniform(outcome["min_percent"], outcome["max_percent"])
                stolen_amount = int(bank_balance * percent)
                formatted_amount = "{:,}".format(stolen_amount).replace(",", " ")

                # Форматирование сообщения об успехе
                success_msg = outcome['msg'].replace('{amount}', formatted_amount)
                success_msg = success_msg.replace('{percent}', f"{percent*100:.1f}")

                message = (
                    f"{outcome['emoji']} {success_msg}\n\n"
                    f"🏦 Новый баланс банка: {bank_balance - stolen_amount:,} монет"
                )

                # Обновление балансов
                cursor.execute("""
                    UPDATE casino_bank 
                    SET balance = balance - ? 
                    WHERE id = 1
                """, (stolen_amount,))
                cursor.execute("""
                    UPDATE users 
                    SET coins = coins + ? 
                    WHERE user_id = ?
                """, (stolen_amount, user.id))
            else:  # Неудачное ограбление
                message = f"{outcome['emoji']} {outcome['msg']}"

                # Штраф 5% от баланса (макс. 10к)
                cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user.id,))
                user_balance = cursor.fetchone()[0]
                penalty = min(int(user_balance * 0.05), 30000)

                if penalty > 0:
                    cursor.execute("""
                        UPDATE users 
                        SET coins = coins - ? 
                        WHERE user_id = ?
                    """, (penalty, user.id))

                    cursor.execute("""
                        UPDATE casino_bank 
                        SET balance = balance + ? 
                        WHERE id = 1
                    """, (penalty,))

                    message += f"\n💸 Штраф: {penalty:,} монет"

            # Сохраняем время попытки
            cursor.execute("""
                INSERT OR REPLACE INTO robbery_attempts 
                (user_id, last_attempt) 
                VALUES (?, ?)
            """, (user.id, datetime.now().isoformat()))

            conn.commit()

            # Отправка результата
            await update.message.reply_text(
                f"🎰 {mention}, <b>РЕЗУЛЬТАТ ОГРАБЛЕНИЯ:</b>\n\n"
                f"{message}\n\n"
                f"⏳ Следующая попытка через 12 часов",
                parse_mode="HTML"
            )

    except sqlite3.Error as e:
        print(f"Ошибка БД в rob_bank: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка базы данных",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Общая ошибка в rob_bank: {e}")
        await update.message.reply_text(
            "⚠️ Произошла непредвиденная ошибка",
            parse_mode="HTML"
        )


async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущий баланс банка казино"""
    try:
        # Проверка входящего сообщения
        if not update or not update.message:
            return

        user = update.effective_user
        if not user:
            return

        # Форматирование имени пользователя
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()

                # Проверка существования таблицы
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='casino_bank'
                """)
                if not cursor.fetchone():
                    await update.message.reply_text(
                        f"🏦 {mention}, банк казино еще не создан",
                        parse_mode="HTML"
                    )
                    return

                # Получаем баланс банка
                cursor.execute("SELECT balance FROM casino_bank WHERE id=1")
                result = cursor.fetchone()

                if not result:
                    # Если запись отсутствует, создаем новую
                    cursor.execute("""
                        INSERT INTO casino_bank (id, balance) 
                        VALUES (1, 0)
                    """)
                    conn.commit()
                    balance = 0
                else:
                    balance = result[0]

                # Форматирование баланса
                formatted_balance = "{:,}".format(balance).replace(",", " ")

                await update.message.reply_text(
                    f"🏦 {mention}, текущий баланс банка казино составляет:\n\n"
                    f"💰 <b>{formatted_balance}</b> монет 💰\n\n",
                    parse_mode="HTML"
                )

        except sqlite3.Error as e:
            print(f"Ошибка БД в bank_command: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, произошла ошибка базы данных",
                parse_mode="HTML"
            )

    except Exception as e:
        print(f"Общая ошибка в bank_command: {e}")
        await update.message.reply_text(
            "⚠️ Произошла непредвиденная ошибка",
            parse_mode="HTML"
        )




async def rob_treasury(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для ограбления казны с 50% шансом успеха и ограничением 24 часа"""
    user = update.effective_user
    if not user:
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Создаем таблицу для хранения времени последнего ограбления
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS treasury_robbery (
                user_id INTEGER PRIMARY KEY,
                last_robbery TEXT
            )
        ''')

        # Проверяем время последнего ограбления
        cursor.execute('SELECT last_robbery FROM treasury_robbery WHERE user_id = ?', (user.id,))
        result = cursor.fetchone()

        current_time = datetime.now()
        mention = user.mention_markdown()

        if result and result[0]:
            last_robbery = datetime.fromisoformat(result[0])
            if (current_time - last_robbery) < timedelta(hours=24):
                time_left = last_robbery + timedelta(hours=24) - current_time
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60

                await update.message.reply_text(
                    f"⏳ {mention}, *вы уже грабили казну сегодня!* ⏳\n\n"
                    f"🕒 Следующая попытка через *{hours} ч {minutes} мин*\n\n"
                    f"💤 Отдохните и возвращайтесь позже!",
                    parse_mode="Markdown"
                )
                return

        # Получаем текущий баланс пользователя
        cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user.id,))
        user_result = cursor.fetchone()

        if not user_result:
            # Если пользователя нет в базе, создаем запись
            cursor.execute(
                'INSERT INTO users (user_id, username, coins) VALUES (?, ?, 0)',
                (user.id, user.username or "Unknown")
            )
            user_balance = 0
        else:
            user_balance = user_result[0]

        # 50% шанс успеха
        is_success = random.random() <= 0.5

        if is_success:
            # Успешное ограбление
            stolen_amount = random.randint(20000, 40000)
            new_balance = user_balance + stolen_amount

            # Обновляем баланс пользователя
            cursor.execute(
                'UPDATE users SET coins = ? WHERE user_id = ?',
                (new_balance, user.id)
            )

            # Сохраняем время ограбления
            cursor.execute('''
                INSERT OR REPLACE INTO treasury_robbery 
                (user_id, last_robbery) 
                VALUES (?, ?)
            ''', (user.id, current_time.isoformat()))

            conn.commit()

            await update.message.reply_text(
                f"💰 {mention}, *ограбление казны удалось!* 🎉\n\n"
                f"🤑 Вы украли *{stolen_amount:,}* монет\n"
                f"💵 Ваш баланс: *{new_balance:,}* монет\n\n"
                f"⏳ Следующая попытка через 24 часа",
                parse_mode="Markdown"
            )
        else:
            # Неудачное ограбление (без штрафа)
            # Все равно сохраняем время попытки
            cursor.execute('''
                INSERT OR REPLACE INTO treasury_robbery 
                (user_id, last_robbery) 
                VALUES (?, ?)
            ''', (user.id, current_time.isoformat()))

            conn.commit()

            await update.message.reply_text(
                f"🚫 {mention}, *ограбление провалилось!* 😞\n\n"
                f"👮 Охрана заметила вас и вы сбежали\n"
                f"💸 Штраф не назначен\n\n"
                f"⏳ Попробуйте снова через 24 часа",
                parse_mode="Markdown"
            )
    except sqlite3.Error as e:
        print(f"Ошибка БД в rob_treasury: {e}")
        if conn:
            conn.rollback()
        await update.message.reply_text(
            "⚠️ Произошла ошибка базы данных",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Общая ошибка в rob_treasury: {e}")
        if conn:
            conn.rollback()
        await update.message.reply_text(
            "⚠️ Произошла непредвиденная ошибка",
            parse_mode="Markdown"
        )
    finally:
        if conn:
            conn.close()






async def football_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        # Формируем обращение к пользователю
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        text = update.message.text.strip().lower()

        # Проверка команды
        if not text.startswith('футбол '):
            return

        # Получение баланса из БД
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
            row = cursor.fetchone()

            if not row:
                await update.message.reply_text(
                    f"❌ {mention}, <b>ваш профиль не найден!</b> Напишите /start",
                    parse_mode="HTML"
                )
                conn.close()
                return

            current_balance = row[0]
            conn.close()
        except Exception as e:
            print(f"Ошибка БД: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка доступа к данным",
                parse_mode="HTML"
            )
            return

        # Обработка ставки
        try:
            bet_text = text.split()[1]
            if bet_text.lower() in ["всё", "все"]:
                bet = current_balance
            else:
                bet = int(bet_text)

            if bet < 5:
                await update.message.reply_text(
                    f"❌ {mention}, <b>ставка не может быть меньше 5 монет</b> ❌",
                    parse_mode="HTML"
                )
                return
        except:
            await update.message.reply_text(
                f"⚽️ {mention}, используйте:\n\n"
                f"⬜ <code>футбол 100</code> <b>- конкретная ставка</b>\n\n"
                f"⬜ <code>футбол всё</code> или <code>футбол все</code> <b>- поставить весь баланс</b>\n\n",
                parse_mode="HTML"
            )
            return

        if bet > current_balance:
            await update.message.reply_text(
                f"❌ {mention}, <b>на балансе недостаточно монет</b> ❌\n\n"
                f"💰 <b>Ваш баланс:</b> {current_balance} <b>монет </b>💰",
                parse_mode="HTML"
            )
            return

        # Игровая логика
        outcomes = [
            
            {"mult": -0.5, "text": "😕 <b>вы проиграли</b> 50% <b>ставки </b> (x0.50) ", "prob": 15},
            {"mult": -0.25, "text": "😣 <b>вы проиграли</b> 25% <b>ставки</b> (x0.25) ", "prob": 15},
            {"mult": -0.75, "text": "🙄 <b>вы проиграли</b> 75% <b>ставки</b> (x0.75) ", "prob": 15},
            {"mult": 0.5, "text": "😜 <b>вы выиграли</b> 50% <b>ставки</b> (x0.50) ", "prob": 15},
            {"mult": 0.25, "text": "🙂 <b>вы выиграли</b> 25% <b>ставки</b> (x0.25) ", "prob": 15},
            {"mult": 0, "text": "😶 <b>сумма вашей ставки сохранена</b> (x0) ", "prob": 15},
            {"mult": 0.75, "text": "😍 <b>вы выиграли</b> 75% <b>ставки</b> (x0.75) ", "prob": 15},
            {"mult": -0.40, "text": "🤨 <b>вы проиграли</b> 40% <b>ставки</b> (x0.40) ", "prob": 15},
            {"mult": 0.30, "text": "🤨 <b>вы выиграли</b> 30% <b>ставки</b> (x0.30) ", "prob": 15},
            {"mult": -0.10, "text": "🤨 <b>вы проиграли</b> 10% <b>ставки</b> (x0.10) ", "prob": 15},
            
            {"mult": 1.5, "text": "💰 <b>вы выиграли</b> 150% <b>ставки</b> (x1.5) ", "prob": 5},
            
            
            
        ]

        chosen = random.choices(outcomes, weights=[o["prob"] for o in outcomes], k=1)[0]
        win = int(bet * chosen["mult"])
        new_balance = current_balance + win
# Обновление баланса
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET coins=? WHERE user_id=?",
                (new_balance, user.id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка обновления: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка сохранения результата",
                parse_mode="HTML"
            )
            return

        # Добавьте эту функцию в начало вашего кода
        def format_number(number):
            return "{:,}".format(int(number)).replace(",", " ")

        # Затем обновите часть формирования сообщения:
        result_msg = f"⚽️ {mention}, {chosen['text']}\n\n"
        result_msg += f"💎 <b>Ставка:</b> {format_number(bet)} <b>монет</b>\n"

        if win > 0:
            result_msg += f"🔺️ <b>Итог:</b> + {format_number(win)} <b>монет</b>\n\n"
        elif win < 0:
            result_msg += f"🔻 <b>Итог:</b> - {format_number(abs(win))} <b>монет</b>\n\n"
        else:
            result_msg += f"🌸 <b>Итог:</b> +0 <b>монет</b>\n\n"

        result_msg += f"💰 <b>Ваш баланс:</b> {format_number(new_balance)} <b>монет</b> 💰\n\n"

        await update.message.reply_text(
            result_msg,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text(
            f"⚠️ {mention}, техническая ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )


async def basketball_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        # Формируем обращение
        mention = f'<a href="tg://user?id={user.id}">{user.username or user.first_name}</a>'
        text = update.message.text.strip().lower()

        if not text.startswith('баскетбол '):
            return

        # Получаем баланс
        try:
            with sqlite3.connect(DB_NAME) as conn:
                current_balance = conn.execute(
                    "SELECT coins FROM users WHERE user_id=?", 
                    (user.id,)
                ).fetchone()[0] or 0
        except Exception as e:
            print(f"Ошибка БД: {e}")
            await update.message.reply_text(f"⚠️ {mention}, ошибка доступа к данным", parse_mode="HTML")
            return

        # Обработка ставки
        try:
            bet_text = text.split()[1]
            bet = current_balance if bet_text.lower() in ["всё", "все"] else int(bet_text)
            
            if bet < 5:
                await update.message.reply_text(
                     f"❌ {mention}, <b>ставка не может быть меньше 5 монет</b> ❌",
                    parse_mode="HTML"
                )
                return
                
            if bet > current_balance:
                await update.message.reply_text(
                    f"❌ {mention}, <b>на балансе недостаточно монет</b> ❌\n\n"
                    f"💰 <b>Ваш баланс:</b> {current_balance} <b>монет </b>💰",
                    parse_mode="HTML"
                )
                return
                
        except (IndexError, ValueError):
            await update.message.reply_text(
                f"🏀 {mention}, используйте:\n\n"
                f"⬜ <code>баскетбол 100</code> <b>- конкретная ставка</b>\n\n"
                f"⬜ <code>баскетбол всё</code> или <code>баскетбол все</code> <b>- поставить весь баланс</b>\n\n",
                parse_mode="HTML"
            )
            return

        outcomes = [
            # Крупные проигрыши (но не уводят баланс в минус)
            {"mult": -1.0, "text": "😡 <b>сумма вашей ставки сгорела</b> (x0)", "prob": 10},
            {"mult": -0.8, "text": "😭 <b>вы проиграли</b> 80% <b>ставки</b> (x0.80)", "prob": 15},
            {"mult": -0.6, "text": "😤 <b>вы проиграли</b> 60% <b>ставки</b> (x0.60)", "prob": 16},
            {"mult": -0.5, "text": "😶 <b>вы проиграли</b> 50% <b>ставки</b> (x0.50)", "prob": 16},
            {"mult": -0.3, "text": "🙄 <b>вы проиграли</b> 30% <b>ставки</b> (x0.30)", "prob": 17},

            # Нейтральные исходы
            {"mult": 0, "text": "🤔 <b>сумма вашей ставки сохранена</b> (x0)", "prob": 17},
            {"mult": 0.1, "text": "🤩 <b>вы выиграли</b> 10% <b>ставки</b> (x0.10)", "prob": 17},

            # Небольшие выигрыши
            {"mult": 0.5, "text": "🙂 <b>вы выиграли</b> 50% <b>ставки</b> (x0.50)", "prob": 16},
            {"mult": 0.8, "text": "😃 <b>вы выиграли</b> 80% <b>ставки</b> (x0.80)", "prob": 16},
            {"mult": 1.0, "text": "😊 <b>вы выиграли</b> 100% <b>ставки</b> (x1)", "prob": 15},
            {"mult": 1.2, "text": "👍 <b>вы выиграли</b> 120% <b>ставки</b> (x1.20)", "prob": 13},

            # Крупные выигрыши
            {"mult": 1.5, "text": "😍 <b>вы выиграли</b> 150% <b>ставки</b> (x1.50)", "prob": 12},
            {"mult": 2.0, "text": "🤑 <b>вы выиграли</b> 200% <b>ставки</b> (x2)", "prob": 10},
            

            # Джекпоты
            
            {"mult": 5.0, "text": "🚀 <b>вы выиграли</b> ДЖЕКПОТ 500% <b>ставки</b> (x5)", "prob": 1},
           

            # Новые редкие исходы
            {"mult": 0.3, "text": "🎽 <b>вы выиграли</b> 30% <b>ставки</b> (x0.30)", "prob": 15},
            {"mult": 1.8, "text": "🏆 <b>вы выиграли</b> 180% <b>ставки</b> (x1.8)", "prob": 8},
            {"mult": 0.7, "text": "🤝 <b>вы выиграли</b> 70% <b>ставки</b> (x0.70)", "prob": 10},
            {"mult": -0.4, "text": "😓 <b>вы проиграли</b> 40% <b>ставки</b> (x0.40)", "prob": 16}
        ]

        chosen = random.choices(outcomes, weights=[o["prob"] for o in outcomes], k=1)[0]
        win = int(bet * chosen["mult"])
        new_balance = current_balance + win
        # Обновление баланса
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET coins=? WHERE user_id=?",
                (new_balance, user.id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка обновления: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка сохранения результата",
                parse_mode="HTML"
            )
            return

        # Добавьте эту функцию в начало вашего кода
        def format_number(number):
            return "{:,}".format(int(number)).replace(",", " ")

        # Затем обновите часть формирования сообщения:
        result_msg = f"🏀 {mention}, {chosen['text']}\n\n"
        result_msg += f"💎 <b>Ставка:</b> {format_number(bet)} <b>монет</b>\n"

        if win > 0:
            result_msg += f"🔺️ <b>Итог:</b> + {format_number(win)} <b>монет</b>\n\n"
        elif win < 0:
            result_msg += f"🔻 <b>Итог:</b> - {format_number(abs(win))} <b>монет</b>\n\n"
        else:
            result_msg += f"🌸 <b>Итог:</b> +0 <b>монет</b>\n\n"

        result_msg += f"💰 <b>Ваш баланс:</b> {format_number(new_balance)} <b>монет</b> 💰\n\n"

        await update.message.reply_text(
            result_msg,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text(
            f"⚠️ {mention}, техническая ошибка",
            parse_mode="HTML"
        )




async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает баланс пользователя (клики, монеты, дом и дату регистрации)"""
    user = update.effective_user
    conn = None

    # Форматируем обращение с @ником
    username = f"@{user.username}" if user.username else user.first_name
    mention = f'<a href="tg://user?id={user.id}">{username}</a>'

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Получаем данные пользователя (добавляем registered)
        cursor.execute(
            "SELECT clicks, coins, registered FROM users WHERE user_id = ?", 
            (user.id,)
        )
        result = cursor.fetchone()

        # Получаем дом пользователя
        cursor.execute(
            "SELECT house_name FROM user_houses WHERE user_id = ?",
            (user.id,)
        )
        house_result = cursor.fetchone()

        # Форматируем числа с пробелами
        def format_number(num):
            return "{:,}".format(num).replace(",", " ")

        if result:
            clicks, coins, registered_date = result
            formatted_coins = format_number(coins)

            # Форматируем дату регистрации
            if registered_date:
                # Если дата в формате строки
                if isinstance(registered_date, str):
                    try:
                        # Пробуем разные форматы дат
                        try:
                            reg_date = datetime.fromisoformat(registered_date.replace('Z', '+00:00'))
                        except:
                            # Если не ISO формат, пробуем распарсить
                            reg_date = datetime.strptime(registered_date, "%Y-%m-%d %H:%M:%S")
                    except:
                        reg_date = datetime.now()
                # Если дата в формате datetime или другом
                else:
                    reg_date = registered_date
                
                formatted_date = reg_date.strftime("%d.%m.%Y в %H:%M")
            else:
                formatted_date = datetime.now().strftime("%d.%m.%Y в %H:%M")

            # Формируем сообщение о доме
            if house_result:
                house_info = f"{house_result[0]}"
            else:
                house_info = "Нет дома"

            message = (
                f"✨️ {mention}, <b>ваш баланс:</b>  ✨️\n\n"
                
                f"<blockquote>💸 <b>Монеты:</b> <code>{formatted_coins}</code>\n"
                f"🕹 <b>Клики монет:</b> <code>{format_number(clicks)}</code>\n"
                f"🌸 <b>Рейтинг:</b> <code>0</code>\n"
                f"⚕️ <b>Опыт:</b> <code>0</code>\n\n" 
                
                
                
                f"🏆 <b>Статус:</b> Нет\n"
                f"💎 <b>Билет:</b> Нет\n"  
                f"⭐ <b>Ранги:</b> Нет\n\n" 
                

                f"🏠 <b>Дом:</b> {house_info}\n\n"
                f"📅 <b>Дата регистрации:</b> {formatted_date}</blockquote>\n" 
            )

        else:
            message = "⚠️ Вы еще не зарегистрированы в системе. Начните с /start"

        await update.message.reply_text(
            message,
            parse_mode='HTML'
        )

    except Exception as e:
        print(f"Ошибка в balance: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при получении баланса")
    finally:
        if conn:
            conn.close()

async def tops_command(update: Update, context: CallbackContext):
    """Обработчик команды /tops с защитой от ошибок"""
    try:
        user = update.effective_user
        chat = update.effective_chat

        # Генерация уникальной сессии
        session_key = int(time.time())

        # Сохраняем данные сессии
        context.user_data['tops_session'] = {
            'owner_id': user.id,
            'chat_id': chat.id,
            'key': session_key,
            'active': True
        }

        # Создаем клавиатуру с уникальным ключом
        keyboard = [
            [InlineKeyboardButton("💰 Топ монет", callback_data=f"tops_coins_{session_key}")],
            [InlineKeyboardButton("💎 Топ кликов", callback_data=f"tops_clicks_{session_key}")]
        ]

        # Отправляем новое сообщение
        message = await context.bot.send_message(
            chat_id=chat.id,
            text="📊 Выберите тип топа:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Сохраняем ID сообщения
        context.user_data['tops_session']['message_id'] = message.message_id

    except Exception as e:
        print(f"TOPS_COMMAND ERROR: {traceback.format_exc()}")
        await update.message.reply_text("⚠️ Не удалось создать меню топа")

def validate_tops_session(query, context) -> bool:
    """Проверяет валидность сессии топа"""
    session = context.user_data.get('tops_session', {})
    if not session.get('active', False):
        return False

    try:
        # Извлекаем ключ из callback_data
        key = int(query.data.split('_')[-1])
        return (
            query.from_user.id == session['owner_id'] and
            query.message.chat.id == session['chat_id'] and
            key == session['key']
        )
    except:
        return False

async def tops_coins_handler(update: Update, context: CallbackContext):
    """Обработчик топа монет"""
    query = update.callback_query
    await query.answer()

    if not validate_tops_session(query, context):
        await query.answer("🚫 Сессия устарела! Введите /tops", show_alert=True)
        return

    try:
        # Ваша логика показа топа монет
        await show_top_list(update, context, "coins", "🏆 Топ монет")
    except Exception as e:
        print(f"COINS_HANDLER ERROR: {traceback.format_exc()}")
        await query.edit_message_text("⚠️ Ошибка загрузки топа")

async def tops_clicks_handler(update: Update, context: CallbackContext):
    """Обработчик топа кликов"""
    query = update.callback_query
    await query.answer()

    if not validate_tops_session(query, context):
        await query.answer("🚫 Сессия устарела! Введите /tops", show_alert=True)
        return

    try:
        # Ваша логика показа топа кликов
        await show_top_list(update, context, "clicks", "⭐ Топ кликов")
    except Exception as e:
        print(f"CLICKS_HANDLER ERROR: {traceback.format_exc()}")
        await query.edit_message_text("⚠️ Ошибка загрузки топа")

async def show_top_list(update: Update, context: CallbackContext, column: str, title: str):
    """Универсальная функция показа топа с обработкой ошибок"""
    query = update.callback_query
    try:
        # 1. Получаем данные из БД
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT user_id, username, {column} FROM users "
                f"ORDER BY {column} DESC LIMIT 10"
            )
            top_users = cursor.fetchall()

        # 2. Формируем текст сообщения
        if not top_users:
            await query.edit_message_text(f"{title}\n\nТоп пока пуст!")
            return

        text = [f"<b>{title}</b>:\n"]
        for i, row in enumerate(top_users, 1):
            username = row['username'] or f"ID:{row['user_id']}"
            # Исправленное форматирование числа
            try:
                formatted_value = "{:,}".format(row[column]).replace(",", " ") if row[column] is not None else "0"
            except:
                formatted_value = str(row[column]) if row[column] is not None else "0"
            text.append(f"{i}. @{username} - {formatted_value}")

        # 3. Создаем клавиатуру с кнопкой "Назад"
        session_key = context.user_data['tops_session']['key']
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data=f"tops_back_{session_key}")]
        ]

        # 4. Обновляем сообщение
        await query.edit_message_text(
            text="\n".join(text),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except sqlite3.Error as e:
        print(f"DATABASE ERROR: {traceback.format_exc()}")
        await query.edit_message_text("⚠️ Ошибка базы данных")
    except Exception as e:
        print(f"TOP_LIST ERROR: {traceback.format_exc()}")
        await query.edit_message_text("⚠️ Ошибка формирования топа")



async def tops_back_handler(update: Update, context: CallbackContext):
    """Обработчик кнопки Назад"""
    query = update.callback_query
    await query.answer()

    if not validate_tops_session(query, context):
        await query.answer("🚫 Сессия устарела! Введите /tops", show_alert=True)
        return

    try:
        session = context.user_data['tops_session']
        keyboard = [
            [InlineKeyboardButton("💰 Топ монет", callback_data=f"tops_coins_{session['key']}")],
            [InlineKeyboardButton("💎 Топ кликов", callback_data=f"tops_clicks_{session['key']}")]
]

        await query.edit_message_text(
            text="📊 Выберите тип топа:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"BACK_HANDLER ERROR: {traceback.format_exc()}")
        await query.edit_message_text("⚠️ Ошибка возврата")






   








async def tapalka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение с кнопкой 'Начать тапать'"""
    user = update.effective_user
    conn = None

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Инициализация пользователя
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, coins, clicks) VALUES (?, ?, 100, 0)",
            (user.id, user.username)
            )
            # Явно обновляем clicks если они NULL
        cursor.execute(
                """UPDATE users SET clicks = 0 
                WHERE user_id = ? AND clicks IS NULL""",
                (user.id,)
            )
        conn.commit()

        # Кнопка для старта
        keyboard = [
            [InlineKeyboardButton("💵 Начать тапать монеты 💵", callback_data=f"start_tap_{user.id}")]
        ]

        await update.message.reply_text(
            f"💥 <b>Это Тапалка Монеты</b> 💥\n\n"

            f"🔰 <b>Монеты - это основная валюта бота, за которую можно купить множество разных товаров</b> 🔰\n\n"

            f"🎁 <b>Курс: 1 клик = 50 монет</b> 🎁\n\n" 

            f"🆘️ <b>По всем вопросам</b> ➡️ @Best_Primos\n\n",
            
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Ошибка в tapalka: {e}")
        await update.message.reply_text("⚠️ Ошибка при инициализации")
    finally:
        if conn:
            conn.close()


async def tapalka_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок с измененным порядком кнопок"""
    query = update.callback_query
    user = query.from_user

    try:
        # Разбираем callback_data
        data_parts = query.data.split('_')
        action = data_parts[0]
        owner_id = int(data_parts[-1])

        # Проверка владельца
        if user.id != owner_id:
            await query.answer("🚫 Это не ваша тапалка!", show_alert=True)
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        if action == "start":
            # Сразу переходим на основной экран
            cursor.execute("SELECT clicks FROM users WHERE user_id = ?", (user.id,))
            clicks = cursor.fetchone()[0]

            # Измененный порядок кнопок (баланс первый)
            keyboard = [
                [InlineKeyboardButton(f" 💰 Баланс: {clicks} 💰", callback_data="none")],
                [InlineKeyboardButton("⭐ Кликать ⭐", callback_data=f"tap_{user.id}")]
            ]

            await query.edit_message_text(
                f"🧩 Чтобы тапать монеты, нажимайте на кнопку «Кликать» 🧩\n\n"

                

                f"🎁 <b>Курс: 1 клик = 50 монет</b> 🎁\n\n"

                f"✨ Чтобы вывести клики Тапалки в монеты, напишите «Вывести клики» ✨\n\n",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
                
            )
            await query.answer()

        elif action == "tap":
            # Обработка тапа
            cursor.execute(
                "UPDATE users SET clicks = clicks + 1 WHERE user_id = ? RETURNING clicks",
                (user.id,)
            )
            new_clicks = cursor.fetchone()[0]
            conn.commit()

            # Обновляем кнопку баланса (она теперь первая)
            keyboard = [
                [InlineKeyboardButton(f" 💰 Баланс: {new_clicks} 💰", callback_data="none")],
                [InlineKeyboardButton("⭐ Кликать ⭐", callback_data=f"tap_{user.id}")]
            ]

            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await query.answer(f" ✅ +1 клик ✅")

        elif action == "none":
            await query.answer()

    except Exception as e:
        logger.error(f"Ошибка обработки кнопки: {e}")
        await query.answer("⚠️ Произошла ошибка")
    finally:
        if 'conn' in locals():
            conn.close()

async def open_case(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик открытия кейсов (до 10 за раз)"""
    user = update.effective_user
    if not user:
        return

    try:
        # Проверяем команду
        text = update.message.text.lower()
        if not any(cmd in text for cmd in ["открыть кейс", "open case"]):
            return

        # Парсим аргументы
        try:
            args = text.split()
            case_type = int(args[2])
            quantity = min(int(args[3]) if len(args) > 3 else 1, 1000000)  # Ограничение до 10
            if quantity <= 0:
                raise ValueError
        except:
            await update.message.reply_text(
                "ℹ️ Формат: «открыть кейс 1 [кол-во]»\n"
                "⚠️ Можно открыть до хуя кейсов за раз"
            )
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Проверяем наличие кейсов
        cursor.execute('SELECT regular_cases, golden_cases FROM inventory WHERE user_id = ?', (user.id,))
        cases = cursor.fetchone()

        if not cases:
            await update.message.reply_text("❌ У вас нет кейсов!")
            return

        case_names = ["обычных", "золотых"]
        available_cases = cases[0] if case_type == 1 else cases[1]

        if available_cases < quantity:
            await update.message.reply_text(
                f"❌ Недостаточно {case_names[case_type-1]} кейсов!\n"
                f"У вас: {available_cases} (попытка открыть: {quantity})"
            )
            return

        # Генерируем награды
        rewards = {
            'coins': 0,
            'clicks': 0,
            'items': []
        }

        for _ in range(quantity):
            if case_type == 1:  # Обычный кейс
                rewards['coins'] += random.randint(30, 100)
                rewards['clicks'] += random.randint(10, 50)
                # 30% шанс получить предмет (1-3 шт)
                
            else:  # Золотой кейс
                rewards['coins'] += random.randint(50, 100)
                rewards['clicks'] += random.randint(30, 80)
                # 60% шанс получить предмет (1-5 шт)
                

        # Обновляем баланс
        cursor.execute('''
        UPDATE users SET 
            coins = coins + ?,
            clicks = clicks + ?
        WHERE user_id = ?
        ''', (rewards['coins'], rewards['clicks'], user.id))

        # Уменьшаем кейсы
        cursor.execute(f'''
        UPDATE inventory SET
            {['regular_cases', 'golden_cases'][case_type-1]} = {['regular_cases', 'golden_cases'][case_type-1]} - ?
        WHERE user_id = ?
        ''', (quantity, user.id))

        conn.commit()

        # Формируем сообщение
        items_text = "\n▸ ".join(rewards['items']) if rewards['items'] else "нет"

        reward_message = (
            f"🎁 Вы открыли {quantity} {case_names[case_type-1]} кейс(ов)!\n\n"
            f"💰 Награды:\n"
            f"▸ Монеты: +{rewards['coins']}\n"
            f"▸ Клики: +{rewards['clicks']}\n"
            
        )

        await update.message.reply_text(reward_message)

    except Exception as e:
        print(f"🚨 Ошибка в open_case: {e}")
        await update.message.reply_text("❌ Произошла ошибка при открытии кейса")
    finally:
        conn.close()


async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых запросов на вывод с проверкой на 0 кликов"""
    user = update.effective_user
    text = update.message.text.lower()
    conn = None

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Получаем текущий баланс
        cursor.execute(
            "SELECT clicks, coins FROM users WHERE user_id = ?",
            (user.id,)
        )
        clicks, coins = cursor.fetchone()

        # Проверка на нулевые клики
        if clicks == 0:
            await update.message.reply_text("❌ <b>У вас на балансе нет кликов для вывода</b> ❌",
            parse_mode='HTML'
                                           )                                
            return
            

        # Определяем сумму вывода
        if "вывести клики" in text or "вывести все" in text:
            amount = clicks
        elif "вывести клики" in text:
            try:
                # Ищем число после слова "вывести"
                amount = int(text.split("вывести клики")[1].strip())
                if amount <= 0:
                    await update.message.reply_text("⚠️ Укажите положительное число!")
                    return
            except (ValueError, IndexError):
                await update.message.reply_text(
                    "ℹ️ <b>Используйте:</b>\n\n"
                    "'вывести клики' - <b>для всех кликов</b>\n"
                    "'вывести клики 100' - <b>для конкретной суммы</b>",
                    parse_mode='HTML'
                )
                return
        else:
            return

        # Проверяем достаточно ли кликов
        if amount > clicks:
            await update.message.reply_text(f"❌ <b>Недостаточно кликов на балансе</b> ❌\n\n" 
            f" 💵 <b>Ваш баланс:</b> {clicks} <b>кликов</b> 💵",
            parse_mode='HTML'
            )
            return

        # Конвертируем (1 клик = 2 монеты)
        converted_coins = amount * 50

        # Обновляем баланс
        cursor.execute(
            "UPDATE users SET clicks = clicks - ?, coins = coins + ? WHERE user_id = ?",
            (amount, converted_coins, user.id)
        )
        conn.commit()

        # Получаем новый баланс
        cursor.execute(
            "SELECT clicks, coins FROM users WHERE user_id = ?",
            (user.id,)
        )
        new_clicks, new_coins = cursor.fetchone()

        await update.message.reply_text(
            f"✅ <b>Успешный вывод! ✅</b>\n\n"
            f"▫️ Выведено: <b>{amount} кликов</b>\n"
            f"▫️ Получено: <b>{converted_coins} монет</b>\n\n"
            
            f"💎 <b>Кликов монет:</b> {new_clicks} \n"
            f"💵 <b>Монет:</b> {new_coins} ",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Ошибка вывода: {e}")
        await update.message.reply_text("⚠️ Ошибка при обработке запроса")
    finally:
        if conn:
            conn.close()

async def volleyball_bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        # Формируем обращение к пользователю
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        text = update.message.text.strip().lower()

        # Проверка команды
        if not text.startswith('волейбол '):
            return

        # Получение баланса из БД
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
            row = cursor.fetchone()

            if not row:
                await update.message.reply_text(
                    f"❌ {mention}, ваш профиль не найден! Напишите /start",
                    parse_mode="HTML"
                )
                conn.close()
                return

            current_balance = row[0]
            conn.close()
        except Exception as e:
            print(f"Ошибка БД: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка доступа к данным",
                parse_mode="HTML"
            )
            return

        # Обработка ставки
        try:
            bet_text = text.split()[1]
            bet = current_balance if bet_text.lower() in ["всё", "все"] else int(bet_text)

            if bet < 5:
                await update.message.reply_text(
                    f"❌ {mention}, <b>ставка не может быть меньше 5 монет</b> ❌",
                    parse_mode="HTML"
                )
                return
        except Exception as e:
            await update.message.reply_text(
                f"🏐 {mention}, используйте:\n\n"
                f"⬜ <code>волейбол 100</code> <b>- конкретная ставка</b>\n\n"
                f"⬜ <code>волейбол всё</code> или <code>волейбол все</code> <b>- поставить весь баланс</b>\n\n",
                parse_mode="HTML"
            )
            return

        # Проверка баланса
        if bet > current_balance:
            await update.message.reply_text(
                f"❌ {mention}, <b>на балансе недостаточно монет</b> ❌\n\n"
                f"💰 <b>Ваш баланс:</b> {current_balance} <b>монет</b> 💰",
                parse_mode="HTML"
            )
            return

        # Игровая логика
        outcomes = [
            {"result": "❌ Блок! Вы проиграли всю ставку", "mult": -1.0, "prob": 5},
            {"result": "😕 Аут! Вы проиграли 50% ставки", "mult": -0.5, "prob": 15},
            {"result": "🤔 Сет в пользу соперника. Вы проиграли 25%", "mult": -0.25, "prob": 15},
            {"result": "🙂 Ваша подача принята. Возврат ставки", "mult": 0.0, "prob": 15},
            {"result": "😊 Атакующий удар! Выигрыш 25%", "mult": 0.25, "prob": 15},
            {"result": "😍 Эйс! Выигрыш 50% ставки", "mult": 0.5, "prob": 15},
            {"result": "💰 Мощный удар! Выигрыш 75%", "mult": 0.75, "prob": 10},
            {"result": "🔥 Гол! Выигрыш 100% ставки", "mult": 1.0, "prob": 5},
            {"result": "🎯 Идеальная подача! Выигрыш 150%", "mult": 1.5, "prob": 3},
            {"result": "🏆 ЧИСТАЯ ПОБЕДА! Выигрыш 300%", "mult": 3.0, "prob": 2}
        ]

        chosen = random.choices(outcomes, weights=[o["prob"] for o in outcomes], k=1)[0]
        win = int(bet * chosen["mult"])
        new_balance = current_balance + win

        # Обновление баланса
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET coins=? WHERE user_id=?",
(new_balance, user.id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка обновления баланса: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка при обновлении баланса",
                parse_mode="HTML"
            )
            return

        # Функция форматирования чисел
        def format_number(amount):
            return "{:,.0f}".format(amount).replace(",", " ")

        # Формирование результата
        result_message = (
            f"🏐 {mention}, {chosen['result']} <b>(x{abs(chosen['mult'])})</b>\n\n"
            f"🔹 <b>Ставка:</b> {format_number(bet)} <b>монет</b>\n"
        )

        if win > 0:
            result_message += f"🔺️ <b>Итог:</b> +{format_number(win)} <b>монет</b>\n\n"
        elif win < 0:
            result_message += f"🔻 <b>Итог:</b> -{format_number(abs(win))} <b>монет</b>\n\n"
        else:
            result_message += f"🌸 <b>Итог:</b> +0 <b>монет</b>\n\n"

        result_message += f"💰 <b>Ваш баланс:</b> {format_number(new_balance)} <b>монет </b> 💰"

        await update.message.reply_text(
            result_message,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка в volleyball_bet_handler: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при обработке команды",
            parse_mode="HTML"
        )

async def darts_bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        # Формируем обращение к пользователю
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        text = update.message.text.strip().lower()

        # Проверка команды
        if not text.startswith('дартс '):
            return

        # Получение баланса из БД
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
                row = cursor.fetchone()

                if not row:
                    await update.message.reply_text(
                        f"❌ {mention}, ваш профиль не найден! Напишите /start",
                        parse_mode="HTML"
                    )
                    return

                current_balance = row[0]
        except Exception as e:
            print(f"Ошибка БД при получении баланса: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка доступа к данным",
                parse_mode="HTML"
            )
            return

        # Обработка ставки
        try:
            bet_text = text.split()[1]
            if bet_text.lower() in ["всё", "все"]:
                bet = current_balance
            else:
                bet = int(bet_text)

            if bet < 5:
                await update.message.reply_text(
                    f"❌ {mention}, <b>ставка не может быть меньше 5 монет</b> ❌",
                    parse_mode="HTML"
                )
                return
        except (IndexError, ValueError):
            await update.message.reply_text(
                f"🎯 {mention}, используйте:\n\n"
                f"⬜ <code>дартс 100</code> <b>- конкретная ставка</b>\n\n"
                f"⬜ <code>дартс всё</code> или <code>дартс все</code> <b>- поставить весь баланс</b>\n\n",
                parse_mode="HTML"
            )
            return

        if bet > current_balance:
            await update.message.reply_text(
                f"❌ {mention}, <b>на балансе недостаточно монет</b> ❌\n\n"
                f"💰 <b>Ваш баланс:</b> {current_balance} <b>монет</b>",
                parse_mode="HTML"
            )
            return

        # Игровая логика дартса
        outcomes = [
            {"points": 0, "result": "<b>вы проиграли всю сумму вашей ставки</b> 😣", "mult": -1.0, "prob": 3},
            {"points": random.randint(1, 20), "result": "<b>вы проиграли 50% своей ставки</b> 😕", "mult": -0.5, "prob": 15},
            {"points": random.randint(21, 40), "result": "<b>вы проиграли 25% своей ставки</b> 😶", "mult": -0.25, "prob": 15},
            {"points": random.randint(41, 60), "result": "<b>сумма вашей ставки сохранена</b> 🙂", "mult": 0.0, "prob": 16},
            {"points": random.randint(61, 80), "result": "<b>вы выиграли 25% своей ставки</b> 😊", "mult": 0.25, "prob": 15},
            {"points": random.randint(81, 100), "result": "<b>вы выиграли 50% своей ставки</b> 😍", "mult": 0.5, "prob": 15},
            {"points": random.randint(101, 120), "result": "<b>вы выиграли 75% своей ставки</b> 💰", "mult": 0.75, "prob": 15},
            {"points": random.randint(121, 140), "result": "<b>вы выиграли 100% своей ставки</b> 🔥", "mult": 1.0, "prob": 13},
            {"points": 150, "result": "<b>вы выиграли 150% своей ставки</b> 🎯", "mult": 1.5, "prob": 13},
            {"points": 180, "result": "<b>вы выиграли 300% своей ставки</b> 🏆", "mult": 3.0, "prob": 3},
            {"points": random.randint(45, 55), "result": "<b>вы проиграли 10% своей ставки</b> 🤨", "mult": -0.1, "prob": 15},
            
        ]

        chosen = random.choices(outcomes, weights=[o["prob"] for o in outcomes], k=1)[0]
        win = int(bet * chosen["mult"])
        new_balance = current_balance + win
# Обновление баланса
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET coins=? WHERE user_id=?",
                    (new_balance, user.id)
                )
                conn.commit()
        except Exception as e:
            print(f"Ошибка обновления баланса: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка при обновлении баланса",
                parse_mode="HTML"
            )
            return

        # Функция форматирования чисел
        def format_number(amount):
            return "{:,.0f}".format(amount).replace(",", " ")

        # Формирование результата с указанием очков
        result_message = (
            f"🎯 {mention}, {chosen['result']}\n\n"
            f"✏️ <b>Очки:</b> {chosen['points']}\n"
            f"📊 <b>Множитель:</b> x{abs(chosen['mult'])}\n\n"
            f"🔹 <b>Ставка:</b> {format_number(bet)} <b>монет</b>\n"
        )

        if win > 0:
            result_message += f"🔺️ <b>Итог:</b> +{format_number(win)} <b>монет</b>\n\n"
        elif win < 0:
            result_message += f"🔻 <b>Итог:</b> -{format_number(abs(win))} <b>монет</b>\n\n"
        else:
            result_message += f"🌸 <b>Итог:</b> +0 <b>монет</b>\n\n"

        result_message += f"💰 <b>Ваш баланс:</b> {format_number(new_balance)} <b>монет</b> 💰"

        await update.message.reply_text(
            result_message,
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Неожиданная ошибка в darts_bet_handler: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при обработке команды",
            parse_mode="HTML"
        )

async def dice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        # Формируем обращение к пользователю
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        text = update.message.text.strip().lower()

        # Проверка команды
        if not text.startswith('кубик '):
            return

        # Получение баланса из БД
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
                row = cursor.fetchone()

                if not row:
                    await update.message.reply_text(
                        f"❌ {mention}, ваш профиль не найден! Напишите /start",
                        parse_mode="HTML"
                    )
                    return

                current_balance = row[0]
        except Exception as e:
            print(f"Ошибка БД при получении баланса: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка доступа к данным",
                parse_mode="HTML"
            )
            return

        # Обработка ставки
        try:
            parts = text.split()
            if len(parts) != 3:
                raise ValueError("Неверный формат команды")

            user_guess = int(parts[1])
            if user_guess < 1 or user_guess > 6:
                raise ValueError("Число должно быть от 1 до 6")

            bet_text = parts[2]
            
            bet = current_balance
        
            bet = int(bet_text)

            if bet < 5:
                await update.message.reply_text(
                    f"❌ {mention}, <b>ставка не может быть меньше 5 монет</b> ❌",
                    parse_mode="HTML"
                )
                return
        except ValueError as e:
            await update.message.reply_text(
                f"🎲 {mention}, используйте:\n\n"
                f"⬜ <code>кубик 100</code> <b>- конкретная ставка</b>\n\n"
                
                
                f"⚡ <b>Число - от 1 до 6</b> ⚡\n",
                parse_mode="HTML"
            )
            return

        if bet > current_balance:
            await update.message.reply_text(
                f"❌ {mention}, <b>на балансе недостаточно монет</b> ❌\n\n"
                f"💰 <b>Ваш баланс:</b> {current_balance} <b>монет</b> 💰",
                parse_mode="HTML"
            )
            return

        # Отправка анимации кубика
        dice_message = await context.bot.send_dice(
            chat_id=update.message.chat_id,
            emoji="🎲"
        )

        # Получаем результат броска (1-6)
        dice_result = dice_message.dice.value

        # Ждем завершения анимации (3 секунды)
        await asyncio.sleep(2)

        # Определение выигрыша
        if dice_result == user_guess:
            win = int(bet * 2)  # 100% выигрыш за точное попадание
            result = "🎉 <b>Поздравляем! Вы угадали число и выиграли</b> 200% <b>ставки</b> 🎉\n"
        elif abs(dice_result - user_guess) == 1:
            if dice_result > user_guess:
                win = int(bet * 0.25)  # 30% за большее соседнее
                result = "👍 <b>Вы выиграли 25% ставки</b> 👍\n"
            else:
                win = int(bet * 0.15)  # 15% за меньшее соседнее
                result = "👌 <b>Вы выиграли 15% ставки</b> 👌\n"
        else:
            win = -bet  # Проигрыш всей ставки
            result = "❌ <b>Вы не угадали число и проиграли сумму ставки</b> ❌\n"

        new_balance = current_balance + win
# Обновление баланса
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET coins=? WHERE user_id=?",
                    (new_balance, user.id)
                )
                conn.commit()
        except Exception as e:
            print(f"Ошибка обновления баланса: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка при обновлении баланса",
                parse_mode="HTML"
            )
            return

        # Функция форматирования чисел
        def format_number(amount):
            return "{:,.0f}".format(amount).replace(",", " ")

        # Формирование результата
        result_message = (
            f"{result}\n"
            f"💎 <b>Ваше число:</b> {user_guess}\n"
            f"🎲 <b>Выпавшее число:</b> {dice_result}\n\n"
            f"🔹 <b>Ставка:</b> {format_number(bet)} <b>монет</b>\n"
        )

        if win > 0:
            result_message += f"🔺️ <b>Выигрыш:</b> +{format_number(win)} <b>монет</b>\n\n"
        elif win < 0:
            result_message += f"🔻 <b>Проигрыш:</b> -{format_number(abs(win))} <b>монет</b>\n\n"
        else:
            result_message += f"🌸 <b>Итог:</b> +0 <b>монет</b>\n\n"

        result_message += f"💰 <b>Ваш баланс:</b> {format_number(new_balance)} <b>монет</b> 💰\n\n"

        await update.message.reply_text(
            result_message,
            parse_mode="HTML",
            reply_to_message_id=dice_message.message_id
        )

    except Exception as e:
        print(f"Неожиданная ошибка в dice_handler: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при обработке команды",
            parse_mode="HTML"
        )



async def bowling_bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        # Формируем обращение к пользователю
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        text = update.message.text.strip().lower()

        # Проверка команды
        if not text.startswith('боулинг '):
            return

        # Получение баланса из БД
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
                row = cursor.fetchone()

                if not row:
                    await update.message.reply_text(
                        f"❌ {mention}, ваш профиль не найден! Напишите /start",
                        parse_mode="HTML"
                    )
                    return

                current_balance = row[0]
        except Exception as e:
            print(f"Ошибка БД: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка доступа к данным",
                parse_mode="HTML"
            )
            return

        # Обработка ставки
        try:
            bet_text = text.split()[1]
            bet = current_balance if bet_text.lower() in ["всё", "все"] else int(bet_text)

            if bet < 5:
                await update.message.reply_text(
                    f"❌ {mention}, <b>ставка не может быть меньше 5 монет</b> ❌",
                    parse_mode="HTML"
                )
                return
        except:
            await update.message.reply_text(
                f"🎳 {mention}, используйте:\n\n"
                f"⬜ <code>боулинг 100</code> <b>- конкретная ставка</b>\n\n"
                f"⬜ <code>боулинг всё</code> или <code>боулинг все</code> <b>- поставить весь баланс</b>\n\n",
                parse_mode="HTML"
            )
            return

        # Проверка баланса
        if bet > current_balance:
            await update.message.reply_text(
                f"❌ {mention}, <b>на балансе недостаточно монет</b> ❌\n\n"
                f"💰 <b>Ваш баланс:</b> {current_balance} <b>монет</b>",
                parse_mode="HTML"
            )
            return

        # Игровая логика боулинга
        outcomes = [
            {"pins": 0, "mult": -1.0, "text": "😭 сумма вашей ставки сгорела <b>(x0)</b>", "prob": 4},
            {"pins": 1, "mult": -0.75, "text": "😕 вы проиграли <b>75%</b> ставки <b>(x0.75)</b>", "prob": 13},
            {"pins": 2, "mult": -0.5, "text": "😣 вы проиграли <b>50%</b> ставки <b>(x0.50)</b>", "prob": 13},
            {"pins": 3, "mult": -0.25, "text": "🙄 вы проиграли <b>25%</b> ставки <b>(x0.25)</b>", "prob": 14},
            {"pins": 4, "mult": 0.25, "text": "🙂 вы выиграли <b>25%</b> ставки <b>(x0.25)</b>", "prob": 13},
            {"pins": 5, "mult": 0.5, "text": "😊 вы выиграли <b>50%</b> ставки <b>(x0.5)</b>", "prob": 13},
            {"pins": 6, "mult": 0.75, "text": "😍 вы выиграли <b>75%</b> ставки <b>(x0.75)</b>", "prob": 11},
            {"pins": 7, "mult": 1.0, "text": "💰 вы выиграли <b>100%</b> ставки <b>(x1)</b>", "prob": 10},
            {"pins": 8, "mult": 1.5, "text": "🤑 вы выиграли <b>150%</b> ставки <b>(x1.5)</b>", "prob": 8},
            {"pins": 9, "mult": 2.0, "text": "🔥 вы выиграли <b>200%</b> ставки <b>(x2)</b>", "prob": 4},
            {"pins": 10, "mult": 5.0, "text": "💥 <b>ДЖЕКПОТ!</b> Вы выиграли <b>500%</b> ставки <b>(x5)</b>", "prob": 1}
            
        ]

        chosen = random.choices(outcomes, weights=[o["prob"] for o in outcomes], k=1)[0]
        win = int(bet * chosen["mult"])
        new_balance = current_balance + win
# Обновление баланса
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET coins=? WHERE user_id=?",
                    (new_balance, user.id)
                )
                conn.commit()
        except Exception as e:
            print(f"Ошибка обновления: {e}")
            await update.message.reply_text(
                f"⚠️ {mention}, ошибка сохранения результата",
                parse_mode="HTML"
            )
            return

        # Функция форматирования чисел
        def format_number(amount):
            return "{:,.0f}".format(amount).replace(",", " ")

        # Формирование результата
        bet_type = "ВСЁ" if bet_text.lower() in ["всё", "все"] else f"{format_number(bet)}"
        result_message = (
            f"🎳 {mention}, {chosen['text']}\n\n"
            f"🔹 Сбито кеглей: <b>{chosen['pins']}/10</b>\n"
            f"📊 Итог: <b>{'+' if win > 0 else ''}{format_number(win)}</b> монет\n\n"
            f"💰 <b>Ваш баланс:</b> {format_number(new_balance)} <b>монет 💰</b>\n"
        )

        await update.message.reply_text(result_message, parse_mode="HTML")

    except Exception as e:
        print(f"Ошибка в bowling_bet_handler: {e}")
        await update.message.reply_text(
            f"⚠️ {mention}, произошла ошибка при обработке команды",
            parse_mode="HTML"
        )



async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение когда пользователь отправляет /contacts"""
    user = update.effective_user
    await update.message.reply_text(
       f"📍 Создатель бота - @Best_Primos 📍\n\n"
       f"📝 По всем вопросам и предложениям пишите в личку - @Best_Primos 📝\n\n"
       f"🎁 За предложения хороших идей предусмотрены награды в виде валюты монет 🎁"
    )



async def coin_flip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message or not update.message.text:
            return

        user = update.effective_user
        if not user:
            return

        text = update.message.text.strip().lower()  # Приводим к нижнему регистру
        parts = text.split()

        # Проверка формата команды (орёл/решка [ставка])
        if len(parts) < 2:
            await update.message.reply_text(
                "🎲 Используйте:\n"
                "• <code>орёл 100</code> - ставка на орла\n"
                "• <code>решка всё</code> - ставка на решку\n"
                "Минимум: 5 монет",
                parse_mode="HTML"
            )
            return

        # Определяем выбор пользователя (нормализуем варианты написания)
        user_choice = parts[0]
        if user_choice.startswith('ор'):  # Ловим "орёл", "орл", "орла" и т.д.
            user_choice = 'орёл'
        elif user_choice.startswith('реш'):  # Ловим "решка", "решетка" и т.д.
            user_choice = 'решка'
        else:
            await update.message.reply_text("❌ Укажите 'орёл' или 'решка'")
            return

        bet_text = ' '.join(parts[1:])  # Объединяем оставшиеся части

        # Получаем баланс
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
                row = cursor.fetchone()
                current_balance = row[0] if row else 0
        except Exception as e:
            print(f"DB error: {e}")
            await update.message.reply_text("⚠️ Ошибка базы данных")
            return

        # Обработка ставки
        try:
            if bet_text in ['всё', 'все']:
                bet = current_balance
            else:
                bet = int(bet_text)

            if bet < 5:
                await update.message.reply_text("❌ Минимальная ставка: 5 монет")
                return

            if bet > current_balance:
                await update.message.reply_text(f"❌ Недостаточно средств. Баланс: {current_balance}")
                return

        except ValueError:
            await update.message.reply_text("❌ Неверная сумма ставки")
            return

        # Отправка анимации
        dice_msg = await context.bot.send_dice(
            chat_id=update.effective_chat.id,
            emoji="🎰"
        )
        await asyncio.sleep(3)

        # Определяем результат
        result = 'орёл' if dice_msg.dice.value % 2 == 1 else 'решка'
        win = int(bet * 1.0) if result == user_choice else -bet
        new_balance = current_balance + win

        # Обновляем баланс
        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("UPDATE users SET coins=? WHERE user_id=?", (new_balance, user.id))
                conn.commit()
        except Exception as e:
            print(f"Balance update error: {e}")

        # Формируем результат
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        result_msg = (
            f"🪙 {mention}, вы {'выиграли' if win > 0 else 'проиграли'}!\n"
            f"▪️ Ваш выбор: {user_choice}\n"
            f"▪️ Выпало: {result}\n"
            f"💰 Ставка: {bet} монет\n"
            f"💸 Итог: {'+' if win > 0 else ''}{win} монет\n"
            f"💳 Баланс: {new_balance} монет"
        )

        await update.message.reply_text(
            result_msg,
            parse_mode="HTML",
            reply_to_message_id=dice_msg.message_id
        )

    except Exception as e:
        print(f"Error in coin_flip: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка")















    

async def transfer_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Проверка входящих данных
        if not update or not update.message:
            return

        user = update.effective_user
        if not user:
            return

        # Проверяем, что это ответ на сообщение
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ Нужно ответить на сообщение пользователя, которому хотите перевести монеты!",
                parse_mode="HTML"
            )
            return

        recipient_user = update.message.reply_to_message.from_user
        if not recipient_user:
            await update.message.reply_text(
                "❌ Не удалось определить получателя!",
                parse_mode="HTML"
            )
            return

        # Проверяем, что не пытаемся перевести себе
        if recipient_user.id == user.id:
            await update.message.reply_text(
                "❌ Нельзя переводить самому себе!",
                parse_mode="HTML"
            )
            return

        # Получаем сумму перевода из текста сообщения
        try:
            text = update.message.text.lower().strip()
            command, amount_str = text.split(maxsplit=1)
            amount = int(amount_str)

            if amount <= 0:
                await update.message.reply_text(
                    "❌ Сумма должна быть положительным числом!",
                    parse_mode="HTML"
                )
                return

            # Проверка минимальной суммы перевода
            if amount < 10:
                await update.message.reply_text(
                    "❌ Минимальная сумма перевода - 10 монет!",
                    parse_mode="HTML"
                )
                return

        except (IndexError, ValueError):
            await update.message.reply_text(
                "❌ Неверный формат. Используйте: \"Передать [сумма]\" (например: Передать 100)",
                parse_mode="HTML"
            )
            return

        # Получаем данные из БД
        conn = None
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Проверяем баланс отправителя
            cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
            sender_data = cursor.fetchone()

            if not sender_data:
                await update.message.reply_text(
                    "❌ Ваш профиль не найден! Напишите /start",
                    parse_mode="HTML"
                )
                return

            sender_balance = sender_data[0]

            if amount > sender_balance:
                await update.message.reply_text(
                    f"❌ Недостаточно монет! Ваш баланс: {sender_balance}",
                    parse_mode="HTML"
                )
                return

            # Проверяем существование получателя
            cursor.execute("SELECT 1 FROM users WHERE user_id=?", (recipient_user.id,))
            if not cursor.fetchone():
                await update.message.reply_text(
                    "❌ Получатель не зарегистрирован в боте!",
                    parse_mode="HTML"
                )
                return

            # Выполняем перевод в транзакции
            try:
                conn.execute("BEGIN TRANSACTION")

                # Списываем у отправителя
                cursor.execute(
                    "UPDATE users SET coins = coins - ? WHERE user_id = ?",
                    (amount, user.id)
                )

                # Зачисляем получателю
                cursor.execute(
                    "UPDATE users SET coins = coins + ? WHERE user_id = ?",
                    (amount, recipient_user.id)
                )

                conn.commit()
# Формируем упоминания
                sender_mention = f'<a href="tg://user?id={user.id}">{user.username or user.first_name}</a>'
                recipient_mention = f'<a href="tg://user?id={recipient_user.id}">{recipient_user.username or recipient_user.first_name}</a>'

                # Сообщение отправителю
                await update.message.reply_text(
                    f"✅ Вы успешно перевели <b>{amount}</b> монет пользователю {recipient_mention}!\n"
                    f"💰 Ваш новый баланс: <b>{sender_balance - amount}</b>",
                    parse_mode="HTML"
                )

                # Сообщение получателю (если бот может писать ему)
                try:
                    await context.bot.send_message(
                        chat_id=recipient_user.id,
                        text=f"🎉 {sender_mention} перевел(а) вам <b>{amount}</b> монет!\n",
                             
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Не удалось уведомить получателя: {e}")

            except Exception as e:
                conn.rollback()
                raise e

        except Exception as e:
            print(f"Ошибка при переводе: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при выполнении перевода. Попробуйте позже.",
                parse_mode="HTML"
            )

        finally:
            if conn:
                conn.close()

    except Exception as e:
        print(f"Ошибка в обработчике перевода: {e}")
        await update.message.reply_text(
            "⚠️ Произошла непредвиденная ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )


async def houses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Формируем правильное упоминание (без Unicode-иероглифов)
    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>' if not user.username else f'@{user.username}'

    houses_text = f"""
🔅 {user_mention}, доступные дома:

<blockquote>
🏡 ❶ <b>Тюремная камера</b> — 1.000 монет
🏡 ❷ <b>Землянка</b> — 2.000 монет
🏡 ❸ <b>Изба</b> — 2.500 монет
🏡 ❹ <b>Терем</b> — 3.000 монет
🏡 ❺ <b>Домик в деревне</b> — 4.500 монет
🏡 ❻ <b>Дача у моря</b> — 6.500 монет
🏡 ❼ <b>Большой дом</b> — 9.000 монет
🏡 ❽ <b>Вилла</b> — 13.000 монет
🏡 ❾ <b>Огромный коттедж</b> — 15.000 монет
🏡 ❿ <b>Собственный остров</b> — 19.000 монет
🏡 ⓫ <b>Усадьба</b> — 24.000 монет
🏡 ⓬ <b>Имперский особняк</b> — 30.000 монет
🏡 ⓭ <b>Царский дворец</b> — 37.000 монет
🏡 ⓮ <b>Роскошный отель</b> — 44.000 монет
🏡 ⓯ <b>Резиденция</b> — 52.000 монет
🏡 ⓰ <b>Гала-пентхаус</b> — 75.000 монет
🏡 ⓱ <b>Рыцарский замок</b> — 90.000 монет
🏡 ⓲ <b>Огромная крепость</b> — 100.000 монет
🏡 ⓳ <b>Умный мега-дом</b> — 120.000 монет
🏡 ⓴ <b>Дом будущего</b> — 150.000 монет
</blockquote>
✅️ <b>Для покупки дома напишите</b> «Купить дом [номер]» ✅️
"""

    await update.message.reply_text(
        houses_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def buy_house_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовой команды 'купить дом [номер]'"""
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower().strip()
    if not text.startswith('купить дом'):
        return


    user = update.effective_user
    if not user:
        return

    # Форматируем обращение с @ником
    username = f"@{user.username}" if user.username else user.first_name
    mention = f'<a href="tg://user?id={user.id}">{username}</a>'

    # Список доступных домов
    houses = {
        1: {"name": "Тюремная камера", "price": 1000, "emoji": "🏡"},
        2: {"name": "Землянка", "price": 2000, "emoji": "🏡"},
        3: {"name": "Изба", "price": 2500, "emoji": "🏡"},
        4: {"name": "Терем", "price": 3000, "emoji": "🏡"},
        5: {"name": "Домик в деревне", "price": 4500, "emoji": "🏡"},
        6: {"name": "Дача у моря", "price": 6500, "emoji": "🏡"},
        7: {"name": "Большой дом", "price": 9000, "emoji": "🏡"},
        8: {"name": "Вилла", "price": 13000, "emoji": "🏡"},
        9: {"name": "Огромный коттедж", "price": 15000, "emoji": "🏡"},
        10: {"name": "Собственный остров", "price": 19000, "emoji": "🏡"},
        11: {"name": "Усадьба", "price": 24000, "emoji": "🏡"},
        12: {"name": "Имперский особняк", "price": 30000, "emoji": "🏡"},
        13: {"name": "Царский дворец", "price": 37000, "emoji": "🏡"},
        14: {"name": "Роскошный отель", "price": 44000, "emoji": "🏡"},
        15: {"name": "Резиденция", "price": 52000, "emoji": "🏡"},
        16: {"name": "Гала-пентхаус", "price": 75000, "emoji": "🏡"},
        17: {"name": "Рыцарский замок", "price": 90000, "emoji": "🏡"},
        18: {"name": "Огромная крепость", "price": 100000, "emoji": "🏡"},
        19: {"name": "Умный мега-дом", "price": 120000, "emoji": "🏡"},
        20: {"name": "Дом будущего", "price": 150000, "emoji": "🏡"}
    }

    # Извлекаем номер дома из текста
    parts = text.split()
    if len(parts) < 3:
        # Показываем список домов если нет номера
        houses_list = "\n".join(
            [f"{house['emoji']}  {i:>2}. <b>{house['name']}</b> — {house['price']:,} монет" 
             for i, house in houses.items()]
        )

        await update.message.reply_text(
    
            f"💡 {mention}, напишите: <b>«купить дом [номер]»</b> 💡\n\n"
            f"💎 <b>Пример:</b> <code>купить дом 20</code> 💎\n\n",
            parse_mode="HTML"
        )
        return

    try:
        house_number = int(parts[2])
        if house_number not in houses:
            await update.message.reply_text(
                f"❌ {mention}, <b>такого дома не существует</b> ❌\n\n" 
                f"💒  <b>Доступные номера домов:</b> 1-20\n\n",
                parse_mode="HTML"
            )
            return

        house = houses[house_number]
        conn = None

        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Создаем таблицу для домов если не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_houses (
                    user_id INTEGER PRIMARY KEY,
                    house_id INTEGER,
                    house_name TEXT,
                    purchase_date TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            ''')

            # Проверяем текущий дом пользователя
            cursor.execute('''
                SELECT house_id, house_name FROM user_houses WHERE user_id = ?
            ''', (user.id,))
            current_house = cursor.fetchone()

            # Проверяем баланс пользователя
            cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user.id,))
            user_data = cursor.fetchone()

            if not user_data:
                await update.message.reply_text(
                    "❌ Ваш профиль не найден. Напишите /start",
                    parse_mode="HTML"
                )
                return

            user_balance = user_data[0]
# Если у пользователя уже есть дом
            if current_house:
                await update.message.reply_text(
                    f"❌ {mention}, <b>вы уже купили дом:</b> {current_house[1]} ❌\n\n"
                    f"⚡ <b>Одновременно можно владеть только одним домом</b> ⚡\n\n"
                    f"💡 <b>Чтобы купить этот дом, напишите</b> <code>продать дом</code> 💡\n\n",
                    parse_mode="HTML"
                )
                return

            # Проверяем достаточно ли денег
            if user_balance < house["price"]:
                await update.message.reply_text(
                    f"❌ {mention}, <b>вам не хватает</b> {house['price'] - user_balance:} <b>монет для покупки данного дома</b> ❌ \n\n"
                    f"💳 <b>Стоимость дома:</b> {house['price']:} <b>монет</b> 💳\n\n"
                    f"💰 <b>Ваш баланс:</b> {user_balance:,} <b>монет</b> 💰\n\n",
                    
                    parse_mode="HTML"
                )
                return

            # Покупка дома
            new_balance = user_balance - house["price"]

            # Обновляем баланс
            cursor.execute(
                'UPDATE users SET coins = ? WHERE user_id = ?',
                (new_balance, user.id)
            )

            # Добавляем дом пользователю
            cursor.execute('''
                INSERT INTO user_houses (user_id, house_id, house_name, purchase_date)
                VALUES (?, ?, ?, ?)
            ''', (user.id, house_number, house["name"], datetime.now().isoformat()))

            conn.commit()

            await update.message.reply_text(
                f"✅ {mention}, вы успешно купили <b>{house['name']}</b> ✅\n\n"
                
                f"💵 <b>Стоимость дома:</b> {house['price']:} <b>монет</b> 💵\n\n"
                f"💰 <b>Ваш баланс:</b> {new_balance:} <b>монет</b> 💰\n\n",
                
                parse_mode="HTML"
            )

        except sqlite3.Error as e:
            print(f"Ошибка БД: {e}")
            if conn:
                conn.rollback()
            await update.message.reply_text(
                "⚠️ Ошибка базы данных",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка: {e}")
            if conn:
                conn.rollback()
            await update.message.reply_text(
                "⚠️ Произошла ошибка",
                parse_mode="HTML"
            )
        finally:
            if conn:
                conn.close()

    except ValueError:
        await update.message.reply_text(
            f"🌸 {mention}, используйте: 🌸\n\n" 
            f"💎 <b>Купить дом [номер]</b> 💎\n\n"
            f"📋 <b>Например:</b> <code>купить дом 5</code> 📋\n\n",
            parse_mode="HTML"
        )

async def sell_house_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовой команды 'продать дом'"""
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower().strip()
    if text != 'продать дом':
        return

    user = update.effective_user
    if not user:
        return

    # Форматируем обращение с @ником
    username = f"@{user.username}" if user.username else user.first_name
    mention = f'<a href="tg://user?id={user.id}">{username}</a>'

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Проверяем есть ли дом у пользователя
        cursor.execute('''
            SELECT house_id, house_name FROM user_houses WHERE user_id = ?
        ''', (user.id,))
        current_house = cursor.fetchone()

        if not current_house:
            await update.message.reply_text(
                f"❌ {mention}, <b>у вас нет дома для продажи</b> ❌",
                parse_mode="HTML"
            )
            return

        house_id, house_name = current_house

        # Удаляем дом из базы
        cursor.execute('DELETE FROM user_houses WHERE user_id = ?', (user.id,))

        # Обнуляем площадь дома
        cursor.execute('''
            DELETE FROM house_area WHERE user_id = ?
        ''', (user.id,))

        conn.commit()

        await update.message.reply_text(
            f"✅ {mention}, <b>вы успешно продали свой дом</b> «{house_name}» \n\n",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Ошибка при продаже: {e}")
        if conn:
            conn.rollback()
        await update.message.reply_text(
            "⚠️ Ошибка при продаже дома",
            parse_mode="HTML"
        )
    finally:
        if conn:
            conn.close()



async def my_house_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовой команды 'мой дом' с кнопкой улучшения"""
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower().strip()
    if text != 'мой дом':
        return

    user = update.effective_user
    if not user:
        return

    # Форматируем обращение с @ником
    username = f"@{user.username}" if user.username else user.first_name
    mention = f'<a href="tg://user?id={user.id}">{username}</a>'

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Создаем таблицу для площади домов если не существует
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS house_area (
                user_id INTEGER PRIMARY KEY,
                house_id INTEGER,
                current_area INTEGER,
                max_area INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        cursor.execute('''
            SELECT house_name, purchase_date, house_id FROM user_houses WHERE user_id = ?
        ''', (user.id,))
        house_data = cursor.fetchone()

        if not house_data:
            await update.message.reply_text(
                "🏚️ <b>У вас пока нет дома</b>\n\n"
                "💡 Напишите <code>купить дом</code> чтобы посмотреть варианты",
                parse_mode="HTML"
            )
            return

        house_name, purchase_date, house_id = house_data
        purchase_time = datetime.fromisoformat(purchase_date)
        days_owned = (datetime.now() - purchase_time).days

        # Получаем информацию о площади
        cursor.execute('''
            SELECT current_area, max_area FROM house_area WHERE user_id = ?
        ''', (user.id,))
        area_data = cursor.fetchone()

        # Базовая площадь для каждого дома
        base_area = 7 + (house_id - 1) * 3
        max_possible_area = base_area * 10  # Увеличено в 10 раз

        if not area_data:
            cursor.execute('''
                INSERT INTO house_area (user_id, house_id, current_area, max_area)
                VALUES (?, ?, ?, ?)
            ''', (user.id, house_id, base_area, max_possible_area))
            conn.commit()
            current_area = base_area
            max_area = max_possible_area
        else:
            current_area, max_area = area_data

        # Стоимость улучшения: +50 монет за каждое улучшение
        improvements_count = current_area - base_area
        upgrade_cost = 100 + (improvements_count * 50)  # Начинается с 100, затем +50 за каждое улучшение

        # Создаем клавиатуру с кнопкой
        keyboard = [
            [InlineKeyboardButton(f"🔼 Улучшить (+1 м² за {upgrade_cost} монет)", callback_data=f"upgrade_house_{user.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            f"⭐ {mention}, <b>ваш дом:</b>\n\n"
            f"♦️ <b>Название:</b> {house_name}\n"
            f"🧾 <b>Дата покупки:</b> {purchase_time.strftime('%d.%m.%Y')}\n"
            f"⏰ <b>Владение:</b> {days_owned} дней\n\n"
            f"💎 <b>Площадь:</b> {current_area} м²/ {max_area} м²\n"
            
            f"💵 <b>Улучшение:</b> +1 м² за {upgrade_cost} монет\n\n"
            
            
            
        )

        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text(
            "⚠️ Ошибка при просмотре дома",
            parse_mode="HTML"
        )
    finally:
        if conn:
            conn.close()

async def upgrade_house_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback'а улучшения дома"""
    query = update.callback_query
    # УБИРАЕМ await query.answer() здесь - он будет вызван позже

    user_id = int(query.data.split('_')[-1])  # Извлекаем user_id из callback_data
    user = query.from_user

    # Проверяем, что кнопку нажал владелец дома
    if user.id != user_id:
        await query.answer("❌ Это не ваш дом!", show_alert=True)
        return

    # Форматируем обращение с @ником
    username = f"@{user.username}" if user.username else user.first_name
    mention = f'<a href="tg://user?id={user.id}">{username}</a>'

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Получаем информацию о доме
        cursor.execute('''
            SELECT house_id, house_name FROM user_houses WHERE user_id = ?
        ''', (user.id,))
        house_data = cursor.fetchone()

        if not house_data:
            await query.answer("❌ Дом не найден!", show_alert=True)
            return

        house_id, house_name = house_data

        # Получаем дату покупки для обновления сообщения
        cursor.execute('''
            SELECT purchase_date FROM user_houses WHERE user_id = ?
        ''', (user.id,))
        purchase_date = cursor.fetchone()[0]
        purchase_time = datetime.fromisoformat(purchase_date)
        days_owned = (datetime.now() - purchase_time).days

        # Получаем информацию о площади
        cursor.execute('''
            SELECT current_area, max_area FROM house_area WHERE user_id = ?
        ''', (user.id,))
        area_data = cursor.fetchone()

        # Получаем баланс пользователя
        cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user.id,))
        user_balance = cursor.fetchone()[0]

        # Рассчитываем параметры
        base_area = 7 + (house_id - 1) * 3
        if not area_data:
            current_area = base_area
            max_area = base_area * 10
        else:
            current_area, max_area = area_data

        # Проверяем можно ли улучшать дальше
        if current_area >= max_area:
            await query.answer("✅ Дом уже достиг максимальной площади!", show_alert=True)
            return

        # Стоимость улучшения: +50 монет за каждое улучшение
        improvements_count = current_area - base_area
        upgrade_cost = 100 + (improvements_count * 50)

        # Проверяем достаточно ли денег
        if user_balance < upgrade_cost:
            await query.answer(
                f"❌ Недостаточно монет!\nВаш баланс: {user_balance} монет",
                show_alert=True
            )
            return

        # Улучшаем дом
        new_area = current_area + 1
        new_balance = user_balance - upgrade_cost

        # Стоимость следующего улучшения (для новой площади)
        next_improvements_count = new_area - base_area
        next_upgrade_cost = 100 + (next_improvements_count * 50)

        cursor.execute('''
            INSERT OR REPLACE INTO house_area (user_id, house_id, current_area, max_area)
            VALUES (?, ?, ?, ?)
        ''', (user.id, house_id, new_area, max_area))

        cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_balance, user.id))
        conn.commit()

        # Показываем всплывающее уведомление (ТОЛЬКО ОДИН РАЗ)
        await query.answer(
            f"✅ Дом улучшен! +1 м² за {upgrade_cost} монет",
            show_alert=True
        )

        # Обновляем сообщение с новой площадью
        can_upgrade = new_area < max_area

        if can_upgrade:
            keyboard = [
                [InlineKeyboardButton(f"🔼 Улучшить (+1 м² за {next_upgrade_cost} монет)", callback_data=f"upgrade_house_{user.id}")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("✅ Достигнут максимум площади", callback_data="max_area_reached")]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
# Обновляем текст сообщения с НОВОЙ площадью
        new_message = (
            f"⭐ {mention}, <b>ваш дом:</b>\n\n"
            f"♦️ <b>Название:</b> {house_name}\n"
            f"🧾 <b>Дата покупки:</b> {purchase_time.strftime('%d.%m.%Y')}\n"
            f"⏰ <b>Владение:</b> {days_owned} дней\n\n"
            f"💎 <b>Площадь:</b> {new_area} м²/ {max_area} м²\n"
            f"💵 <b>Улучшение:</b> +1 м² за {next_upgrade_cost} монет\n\n"
        )

        # Обновляем и текст и кнопку
        await query.message.edit_text(
            new_message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Ошибка при улучшении: {e}")
        if conn:
            conn.rollback()
        await query.answer("⚠️ Ошибка при улучшении дома", show_alert=True)
    finally:
        if conn:
            conn.close()











async def yachts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Форматируем упоминание пользователя
    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>' if not user.username else f'@{user.username}'

    yachts_text = f"""
🔅 {user_mention}, доступные яхты:

<blockquote>
🛳 ❶ <b>Плот</b> — 1.000 монет
🛳 ❷ <b>Ванна</b> — 1.500 монет
🛳 ❸ <b>Гребная лодка</b> — 2.500 монет
🛳 ❹ <b>Моторная лодка</b> — 4.000 монет
🛳 ❺ <b>Моторная яхта</b> — 6.000 монет
🛳 ❻ <b>Мегаяхта</b> — 8.500 монет
🛳 ❼ <b>Гиперяхта</b> — 11.500 монет
🛳 ❽ <b>Яхта-вилла</b> — 15.000 монет
🛳 ❾ <b>Яхта-дворец</b> — 18.000 монет
🛳 ❿ <b>Океанская яхта</b> — 23.000 монет
🛳 ⓫ <b>Плавающий отель</b> — 27.000 монет
🛳 ⓬ <b>Частный паром</b> — 33.000 монет
🛳 ⓭ <b>Морская платформа</b> — 45.000 монет
🛳 
</blockquote>
✅ <b>Для покупки яхты напишите</b> «Купить яхту [номер]»
"""

    await update.message.reply_text(
        yachts_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def phones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>' if not user.username else f'@{user.username}'

    phones_text = f"""
🔅 {user_mention}, доступные телефоны:

<blockquote>
☎ ➊ <b>Nokia 3310</b> — 1.000 монет
☎ ➋ <b>Realme Note 50</b> — 1.500 монет
☎ ➌ <b>Xiaomi Redmi A3</b> — 2.500 монет
☎ ➍ <b>Huawei P40</b> — 3.500 монет
☎ ➎ <b>Samsung Galaxy A35</b> — 5.000 монет
☎ ➏ <b>iPhone 11 Pro Max</b> — 6.500 монет
☎ ➐ <b>Honor Magic6 Pro</b> — 8.500 монет
☎ ➑ <b>Realme GT 7 Pro</b> — 11.000 монет
☎ ➒ <b>Samsung Galaxy S25 Ultra</b> — 14.000 монет
☎ ➓ <b>Apple iPhone 16 Pro Max</b> — 15.000 монет
</blockquote>
✅️ <b>Для покупки телефона напишите</b> «Купить телефон [номер]»
"""

    await update.message.reply_text(
        phones_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def planes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>' if not user.username else f'@{user.username}'

    planes_text = f"""
🔅 {user_mention}, доступные самолёты:

<blockquote>
✈ ➊ <b>Ан-2</b> — 5.000 монет
✈ ➋ <b>Boeing 737 MAX</b> — 6.000 монет
✈ ➌ <b>Ту-154</b> — 7.000 монет
✈ ➍ <b>McDonnell Douglas DC-10</b> — 8.500 монет
✈ ➎ <b>Ил-76</b> — 10.000 монет
✈ ➏ <b>Airbus A320neo</b> — 11.500 монет
✈ ➐ <b>Boeing 777</b> — 13.500 монет
✈ ➑ <b>Lockheed Martin F-35 Lightning II</b> — 15.500 монет
✈ ➒ <b>Airbus A350</b> — 18.000 монет
✈ ➓ <b>Boeing 747</b> — 25.000 монет
</blockquote>
✅️ <b>Для покупки самолёта напишите</b> «Купить самолёт [номер]» 
"""

    await update.message.reply_text(
        planes_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def cars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>' if not user.username else f'@{user.username}'

    cars_text = f"""
🔅 {user_mention}, доступные машины:

<blockquote>
🚗 ➊ <b>Самокат</b> — 1.000 монет
🚗 ➋ <b>Велосипед</b> — 1.500 монет
🚗 ➌ <b>Гироскутер</b> — 2.000 монет
🚗 ➍ <b>Мопед</b> — 3.000 монет
🚗 ➎ <b>Мотоцикл</b> — 4.000 монет
🚗 ➏ <b>ВАЗ 2109</b> — 5.000 монет
🚗 ➐ <b>Квадроцикл</b> — 6.000 монет
🚗 ➑ <b>Вездеход</b> — 7.000 монет
🚗 ➒ <b>Лада Xray</b> — 12.000 монет
🚗 ➓ <b>Audi Q7</b> — 15.000 монет
🚗 ➊➊ <b>BMW X6</b> — 18.000 монет
🚗 ➊➋ <b>Toyota FT-HS</b> — 21.000 монет
🚗 ➊➌ <b>BMW Z4 M</b> — 24.000 монет
🚗 ➊➍ <b>Subaru WRX STI</b> — 27.000 монет
🚗 ➊➎ <b>Lamborghini Veneno</b> — 30.000 монет
🚗 ➊➏ <b>Tesla Roadster</b> — 33.000 монет
🚗 ➊➐ <b>Yamaha YZF R6</b> — 36.000 монет
🚗 ➊➑ <b>Bugatti Chiron</b> — 39.000 монет
🚗 ➊➒ <b>Thrust SSC</b> — 42.000 монет
🚗 ➋⓿ <b>Ferrari LaFerrari</b> — 45.000 монет
🚗 ➋➊ <b>Koenigsegg Regear</b> — 48.000 монет
🚗 ➋➋ <b>Tesla Semi</b> — 51.500 монет
🚗 ➋➌ <b>Venom GT</b> — 55.000 монет
🚗 ➋➍ <b>Rolls-Royce</b> — 60.000 монет
</blockquote>
✅️ <b>Для покупки машины напишите</b> «Купить машину [номер]»

"""

    await update.message.reply_text(
        cars_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def fix_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # 1. Создаем временный столбец
        cursor.execute("ALTER TABLE users ADD COLUMN clicks_temp INTEGER DEFAULT 0")

        # 2. Копируем только числовые значения
        cursor.execute("""
            UPDATE users 
            SET clicks_temp = CAST(clicks AS INTEGER) 
            WHERE typeof(clicks) = 'integer'
        """)

        # 3. Для некорректных значений ставим 0
        cursor.execute("""
            UPDATE users 
            SET clicks_temp = 0 
            WHERE typeof(clicks) != 'integer'
        """)

        # 4. Удаляем старый столбец
        cursor.execute("ALTER TABLE users DROP COLUMN clicks")

        # 5. Переименовываем временный столбец
        cursor.execute("ALTER TABLE users RENAME COLUMN clicks_temp TO clicks")

        conn.commit()
        await update.message.reply_text("✅ База данных успешно исправлена!")

    except Exception as e:
        conn.rollback()
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        conn.close()


async def bank_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if not user:
            await update.message.reply_text("❌ Пользователь не найден.")
            return

        # Формируем обращение
        user_mention = f"@{user.username}" if user.username else user.first_name
        bold_mention = f"*{user_mention}*"

        conn = None
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Проверяем наличие всех необходимых столбцов
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'coins' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 100")
            if 'clicks' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN clicks INTEGER DEFAULT 0")
            if 'bank_coins' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN bank_coins INTEGER DEFAULT 0")
            if 'bank_clicks' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN bank_clicks INTEGER DEFAULT 0")
            conn.commit()

            # Получаем текущий баланс
            cursor.execute(
                "SELECT coins, clicks, bank_coins, bank_clicks FROM users WHERE user_id = ?",
                (user.id,)
            )
            result = cursor.fetchone()

            if not result:
                # Создаем нового пользователя
                cursor.execute(
                    "INSERT INTO users (user_id, username, coins, clicks, bank_coins, bank_clicks) "
                    "VALUES (?, ?, 100, 0, 0, 0)",
                    (user.id, user.username)
                )
                conn.commit()
                coins, clicks, bank_coins, bank_clicks = 100, 0, 0, 0
            else:
                coins, clicks, bank_coins, bank_clicks = result

            # Определяем тип валюты
            text = update.message.text.lower().strip()
            currency_type = "clicks" if "клики" in text or "кликов" in text else "coins"

            # Обработка команды "положить всё"
            if "положить всё" in text or "всё" in text:
                amount = clicks if currency_type == "clicks" else coins
                if amount <= 0:
                    await update.message.reply_text(
                        f"💸 {bold_mention}, *у вас нет {'кликов' if currency_type == 'clicks' else 'монет'} для перевода!* 💸",
                        parse_mode="Markdown"
                    )
                    return
            else:
                # Обычная обработка числа
                try:
                    amount = int(next(word for word in text.split() if word.isdigit()))
                except (ValueError, StopIteration):
                    await update.message.reply_text(
                        f"{bold_mention}, *укажите точную сумму или напишите «всё»*\n\n"
                        f"*Примеры:*\n"
                        f"«банк положить 500» - для монет\n"
                        f"«банк положить 50 кликов» - для кликов\n"
                        f"«банк положить всё» - все монеты\n"
                        f"«банк положить все клики» - все клики",
                        parse_mode="Markdown"
                    )
                    return

            # Проверяем баланс
            current_balance = clicks if currency_type == "clicks" else coins
            if current_balance < amount:
                await update.message.reply_text(
                    f"❌ {bold_mention}, *недостаточно {'кликов' if currency_type == 'clicks' else 'монет'}!* ❌\n\n"
                    f"💵 *Ваш баланс:* {current_balance} "
                    f"{'кликов' if currency_type == 'clicks' else 'монет'}\n",
                    parse_mode="Markdown"
                )
                return
# Обновляем баланс
            if currency_type == "clicks":
                cursor.execute(
                    "UPDATE users SET clicks = clicks - ?, bank_clicks = bank_clicks + ? "
                    "WHERE user_id = ?",
                    (amount, amount, user.id)
                )
            else:
                cursor.execute(
                    "UPDATE users SET coins = coins - ?, bank_coins = bank_coins + ? "
                    "WHERE user_id = ?",
                    (amount, amount, user.id)
                )
            conn.commit()

            # Получаем новый баланс
            cursor.execute(
                "SELECT coins, clicks, bank_coins, bank_clicks FROM users WHERE user_id = ?",
                (user.id,)
            )
            new_coins, new_clicks, new_bank_coins, new_bank_clicks = cursor.fetchone()

            await update.message.reply_text(
                f"✅ {bold_mention}, *вы успешно положили в банк:*\n"
                f"🔹 *Сумма:* {amount} {'кликов' if currency_type == 'clicks' else 'монет'}\n\n"
                f"📊 *Новые балансы:*\n"
                f"💵 Монеты: {new_coins} (в банке: {new_bank_coins})\n"
                f"🖱 Клики: {new_clicks} (в банке: {new_bank_clicks})",
                parse_mode="Markdown"
            )

        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            await update.message.reply_text(
                f"⚠️ {bold_mention}, *ошибка базы данных*\n"
                f"Попробуйте позже или сообщите администратору",
                parse_mode="Markdown"
            )
            print(f"SQL Error: {e}")
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ {bold_mention}, *произошла ошибка*\n"
                f"Попробуйте позже или сообщите администратору",
                parse_mode="Markdown"
            )
            print(f"Error in bank_deposit: {e}")
        finally:
            if conn:
                conn.close()

    except Exception as e:
        print(f"Unexpected error: {e}")


async def bank_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = None
    try:
        user = update.effective_user
        if not user:
            await update.message.reply_text("❌ Пользователь не найден.")
            return

        # Формируем обращение
        user_mention = f"@{user.username}" if user.username else user.first_name
        bold_mention = f"<b>{user_mention}</b>"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Получаем текущие балансы
        cursor.execute(
            "SELECT coins, clicks, bank_coins, bank_clicks FROM users WHERE user_id = ?", 
            (user.id,)
        )
        coins, clicks, bank_coins, bank_clicks = cursor.fetchone() or (0, 0, 0, 0)

        # Анализируем команду
        text = update.message.text.lower()

        # Определяем тип операции (монеты или клики)
        if "клик" in text or "кликов" in text:
            # Операция с кликами
            if "всё" in text or "все" in text:
                amount = bank_clicks
                if amount <= 0:
                    await update.message.reply_text(
                        f"💸 {bold_mention}, у вас нет кликов в банке!",
                        parse_mode="HTML"
                    )
                    return
            else:
                try:
                    amount = int(text.split()[2])
                except (IndexError, ValueError):
                    await update.message.reply_text(
                        f"📌 {bold_mention}, укажите сумму или напишите «снять все клики»\n"
                        f"Пример: «банк снять 50 кликов»",
                        parse_mode="HTML"
                    )
                    return

            # Проверяем достаточно ли кликов в банке
            if bank_clicks < amount:
                await update.message.reply_text(
                    f"❌ {bold_mention}, недостаточно кликов в банке!\n"
                    f"Доступно: {bank_clicks} кликов",
                    parse_mode="HTML"
                )
                return

            # Обновляем балансы
            cursor.execute(
                "UPDATE users SET clicks = clicks + ?, bank_clicks = bank_clicks - ? "
                "WHERE user_id = ?",
                (amount, amount, user.id)
            )
            new_clicks = clicks + amount
            new_bank_clicks = bank_clicks - amount

            await update.message.reply_text(
                f"✅ {bold_mention}, вы сняли {amount} кликов из банка!\n"
                f"💳 На руках: {new_clicks} кликов\n"
                f"🏦 В банке осталось: {new_bank_clicks} кликов",
                parse_mode="HTML"
            )

        else:
            # Операция с монетами
            if "всё" in text or "все" in text:
                amount = bank_coins
                if amount <= 0:
                    await update.message.reply_text(
                        f"💸 {bold_mention}, у вас нет монет в банке!",
                        parse_mode="HTML"
                    )
                    return
            else:
                try:
                    amount = int(text.split()[2])
                except (IndexError, ValueError):
                    await update.message.reply_text(
                        f"📌 {bold_mention}, укажите сумму или напишите «снять всё»\n"
                        f"Пример: «банк снять 500»",
                        parse_mode="HTML"
                    )
                    return

            # Проверяем достаточно ли монет в банке
            if bank_coins < amount:
                await update.message.reply_text(
                    f"❌ {bold_mention}, недостаточно монет в банке!\n"
                    f"Доступно: {bank_coins} монет",
                    parse_mode="HTML"
                )
                return
# Обновляем балансы
            cursor.execute(
                "UPDATE users SET coins = coins + ?, bank_coins = bank_coins - ? "
                "WHERE user_id = ?",
                (amount, amount, user.id)
            )
            new_coins = coins + amount
            new_bank_coins = bank_coins - amount

            await update.message.reply_text(
                f"✅ {bold_mention}, вы сняли {amount} монет из банка!\n"
                f"💳 На руках: {new_coins} монет\n"
                f"🏦 В банке осталось: {new_bank_coins} монет",
                parse_mode="HTML"
            )

        conn.commit()

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        await update.message.reply_text(
            "⚠️ Ошибка базы данных. Попробуйте позже.",
            parse_mode="HTML"
        )
        print(f"SQL Error: {e}")
    except Exception as e:
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте еще раз.",
            parse_mode="HTML"
        )
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()



async def bank_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = None
    try:
        user = update.effective_user
        if not user:
            await update.message.reply_text("❌ Пользователь не найден.")
            return

        # Формируем обращение
        user_mention = f"@{user.username}" if user.username else user.first_name
        bold_mention = f"<b>{user_mention}</b>"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Получаем все балансы
        cursor.execute(
            "SELECT coins, clicks, bank_coins, bank_clicks FROM users WHERE user_id = ?",
            (user.id,)
        )
        result = cursor.fetchone()

        if not result:
            await update.message.reply_text(
                f"{bold_mention}, сначала зарегистрируйтесь через /start",
                parse_mode="HTML"
            )
            return

        coins, clicks, bank_coins, bank_clicks = result

        await update.message.reply_text(
            f"🏦 <u>Банковский счет {bold_mention}</u>\n\n"
            f"💵 <b>Монеты:</b>\n"
            f"▸ На руках: {coins}\n"
            f"▸ В банке: {bank_coins}\n\n"
            f"🖱 <b>Клики:</b>\n"
            f"▸ На руках: {clicks}\n"
            f"▸ В банке: {bank_clicks}",
            parse_mode="HTML"
        )

    except sqlite3.Error as e:
        await update.message.reply_text(
            "⚠️ Ошибка базы данных. Попробуйте позже.",
            parse_mode="HTML"
        )
        print(f"SQL Error in bank_balance: {e}")
    except Exception as e:
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте еще раз.",
            parse_mode="HTML"
        )
        print(f"Error in bank_balance: {e}")
    finally:
        if conn:
            conn.close()

async def bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_user(user.id):
        save_user({'user_id': user.id, 'username': user.username})
    # Создаем ссылку на профиль пользователя
    user_mention = user.mention_markdown() if user.username else f"{user.first_name}"

    await update.message.reply_text(
        f"*На месте* ✅\n",
        parse_mode="Markdown"
    )

async def dildos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_mention = f"@{user.username}" if user.username else user.first_name
    bold_mention = f"{user_mention}"

    dildos_text = f"""
🔅 {bold_mention}, доступные дилдо:

<blockquote>
➊ <b>Дилдо из говна</b> — 1.000 монет
➋ <b>Дилдо супры</b> — 2.000 монет
➌ <b>Дилдо глиста</b> — 3.000 монет
➍ <b>Дилдо Ромы</b> — 4.000 монет
➎ <b>Дилдо миноса</b> — 5.000 монет
➏ <b>Дилдо алмазный</b> — 6.000 монет
➐ <b>Дилдо изумрудный</b> — 7.000 монет
➑ <b>Дилдо из урана</b> — 8.000 монет
➒ <b>Дилдо нано частиц</b> — 9.000 монет
➓ <b>Дилдо из дилдоков</b> — 10.000 монет
</blockquote>
✅ <b>Для покупки напишите</b> «Купить дилдо [номер]»
"""

    await update.message.reply_text(
        dildos_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )






async def cases_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        if not user:
            return

        # Формируем упоминание с @username
        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        cases_info = (
            f"💲 {mention}, <b>доступные кейсы:</b> 💲\n\n"
            "🎁 ❶ <b>Обычный</b> - 100 <b>монет</b>\n"
            "🎁 ❷ <b>Золотой</b> - 50 <b>кликов</b> <b>монет</b>\n\n"
            "🏮 <b>Для открытия напишите:</b> «Открыть кейс [1/2] [кол-во]»\n\n"
            "💰 <b>Для покупки напишите:</b> «Купить кейс [1/2] [кол-во]»\n\n"
        )

        await update.message.reply_text(
            cases_info,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка в cases_handler: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка при отображении кейсов")

async def buy_case(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальная рабочая версия покупки кейсов"""
    user = update.effective_user
    if not user:
        return

    try:
        # Проверяем команду
        if not any(cmd in update.message.text.lower() for cmd in ["купить кейс", "открыть кейс"]):
            return

        # Парсим аргументы
        try:
            args = update.message.text.split()
            case_type = int(args[2])
            quantity = int(args[3]) if len(args) > 3 else 1
            if quantity <= 0:
                raise ValueError
        except:
            await update.message.reply_text("ℹ️ Формат: «купить кейс 1 [кол-во]»")
            return

        # Получаем данные из БД
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Проверяем существование пользователя
        cursor.execute('SELECT coins, clicks FROM users WHERE user_id = ?', (user.id,))
        user_data = cursor.fetchone()

        if not user_data:
            # Создаем нового пользователя
            cursor.execute('INSERT INTO users (user_id, coins, clicks) VALUES (?, 100, 50)', (user.id,))
            conn.commit()
            coins, clicks = 100, 50
        else:
            coins, clicks = user_data

        # Обработка покупки
        if case_type == 1:  # Обычный кейс
            total_price = 100 * quantity
            if coins < total_price:
                await update.message.reply_text(f"❌ Недостаточно монет! Нужно: {total_price}")
                return
            new_coins = coins - total_price
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (new_coins, user.id))
            cursor.execute('''
                INSERT INTO inventory (user_id, regular_cases) 
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET regular_cases = regular_cases + ?
            ''', (user.id, quantity, quantity))

        elif case_type == 2:  # Золотой кейс
            total_price = 50 * quantity
            if clicks < total_price:
                await update.message.reply_text(f"❌ Недостаточно кликов! Нужно: {total_price}")
                return
            new_clicks = clicks - total_price
            cursor.execute('UPDATE users SET clicks = ? WHERE user_id = ?', (new_clicks, user.id))
            cursor.execute('''
                INSERT INTO inventory (user_id, golden_cases) 
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET golden_cases = golden_cases + ?
            ''', (user.id, quantity, quantity))

        else:
            await update.message.reply_text("❌ Доступны только кейсы 1 и 2")
            return

        conn.commit()
        await update.message.reply_text(
            f"✅ Успешно куплено {quantity} {['обычных', 'золотых'][case_type-1]} кейсов!\n"
            f"▸ Списано: {total_price} {'монет' if case_type == 1 else 'кликов'}\n"
            f"▸ Остаток: {new_coins if case_type == 1 else new_clicks}"
        )

    except Exception as e:
        print(f"🚨 Critical error in buy_case: {e}")
        await update.message.reply_text("🔧 Произошла ошибка. Попробуйте позже.")
    finally:
        conn.close()

def admin_only(func):
    """Декоратор для проверки прав администратора"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Проверяем ID пользователя
            if update.effective_user.id not in ADMINS:
                await update.message.reply_text("🚫 Команда только для администраторов!")
                return
            return await func(update, context)
        except Exception as e:
            print(f"ADMIN_CHECK ERROR: {traceback.format_exc()}")
            await update.message.reply_text("⚠️ Ошибка проверки прав")
    return wrapper

@admin_only
async def manage_cases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-команда для управления кейсами с проверкой прав"""
    conn = None
    try:
        # Проверка аргументов
        if len(context.args) < 3:
            help_text = (
                "ℹ️ Формат команды:\n"
                "/manage_cases <действие> <тип_кейса> <количество> [ID_пользователя]\n\n"
                "Действия:\n"
                "add - добавить кейсы\n"
                "remove - забрать кейсы\n"
                "set - установить точное количество\n\n"
                "Типы кейсов:\n"
                "1 - обычные\n"
                "2 - золотые\n\n"
                "Примеры:\n"
                "/manage_cases add 1 100 123456 - выдать 100 обычных\n"
                "/manage_cases remove 2 50 - забрать 50 золотых у всех"
            )
            await update.message.reply_text(help_text)
            return

        action = context.args[0].lower()
        case_type = int(context.args[1])
        amount = int(context.args[2])
        user_id = int(context.args[3]) if len(context.args) > 3 else None

        # Валидация параметров
        if case_type not in (1, 2):
            await update.message.reply_text("❌ Тип кейса должен быть 1 (обычные) или 2 (золотые)")
            return

        if amount <= 0:
            await update.message.reply_text("❌ Количество должно быть положительным числом")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        case_column = 'regular_cases' if case_type == 1 else 'golden_cases'

        # Обработка действий
        if action == 'add':
            if user_id:
                # Выдача конкретному пользователю
                cursor.execute(f'''
                INSERT INTO inventory (user_id, {case_column})
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    {case_column} = {case_column} + excluded.{case_column}
                ''', (user_id, amount))
            else:
                # Выдача всем
                cursor.execute(f'''
                UPDATE inventory SET {case_column} = {case_column} + ?
                ''', (amount,))

        elif action == 'remove':
            if user_id:
                # Проверка баланса перед списанием
                cursor.execute(f'''
                SELECT {case_column} FROM inventory WHERE user_id = ?
                ''', (user_id,))
                current = cursor.fetchone()
                if not current or current[0] < amount:
                    await update.message.reply_text(f"❌ Недостаточно кейсов у пользователя {user_id}")
                    return

                cursor.execute(f'''
                UPDATE inventory SET {case_column} = {case_column} - ?
                WHERE user_id = ?
                ''', (amount, user_id))
            else:
                # Списание у всех (не ниже 0)
                cursor.execute(f'''
                UPDATE inventory SET {case_column} = MAX(0, {case_column} - ?)
                ''', (amount,))

        elif action == 'set':
            if user_id:
                cursor.execute(f'''
                INSERT INTO inventory (user_id, {case_column})
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    {case_column} = excluded.{case_column}
                ''', (user_id, amount))
            else:
                cursor.execute(f'''
                UPDATE inventory SET {case_column} = ?
                ''', (amount,))

        else:
            await update.message.reply_text("❌ Неизвестное действие. Используйте add/remove/set")
            return

        conn.commit()

        # Логирование действия
        admin_id = update.effective_user.id
        target = f"user {user_id}" if user_id else "all users"
        print(f"ADMIN ACTION: {admin_id} {action} {amount} cases (type {case_type}) to {target}")
# Формируем отчет
        case_name = "обычных" if case_type == 1 else "золотых"
        action_name = {
            'add': 'Выдано',
            'remove': 'Списано',
            'set': 'Установлено'
        }[action]

        await update.message.reply_text(
            f"✅ {action_name} {amount} {case_name} кейсов\n"
            f"👤 {'Для пользователя ' + str(user_id) if user_id else 'Для всех пользователей'}"
        )

    except ValueError:
        await update.message.reply_text("❌ Некорректные числовые параметры")
    except Exception as e:
        print(f"MANAGE_CASES ERROR: {traceback.format_exc()}")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке команды")
    finally:
        if conn is not None:
            conn.close()





async def inventory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик просмотра инвентаря"""
    user = update.effective_user
    if not user:
        return

    try:
        user_data = get_user(user.id)
        if not user_data:
            await update.message.reply_text("❌ Ваш аккаунт не найден")
            return

        username = f"@{user.username}" if user.username else user.first_name
        mention = f'<a href="tg://user?id={user.id}">{username}</a>'

        inventory_msg = (
            f"🎒 {mention}, ваш инвентарь:\n\n"
            f"📦 Кейсы:\n"
            f"▫️ Обычные: {user_data['regular_cases']} шт.\n"
            f"▫️ Золотые: {user_data['golden_cases']} шт.\n\n"
            
        )

        await update.message.reply_text(inventory_msg, parse_mode="HTML")

    except Exception as e:
        print(f"Ошибка в inventory_handler: {e}")
        await update.message.reply_text("❌ Ошибка при просмотре инвентаря")
        




async def my_dildo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        if not user:
            return

        mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

        # Получаем баланс пользователя из БД
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT coins FROM users WHERE user_id=?", (user.id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await update.message.reply_text(
                f"❌ {mention}, ваш профиль не найден! Напишите /start",
                parse_mode="HTML"
            )
            return

        balance = row[0]

        # Определяем уровень дилдо на основе баланса
        dildos = [
            {"name": "Дилдо из говна", "price": 1000, "emoji": "💩"},
            {"name": "Дилдо супры", "price": 2000, "emoji": "🍜"},
            {"name": "Дилдо глиста", "price": 3000, "emoji": "🪱"},
            {"name": "Дилдо Ромы", "price": 4000, "emoji": "👨"},
            {"name": "Дилдо миноса", "price": 5000, "emoji": "🐂"},
            {"name": "Дилдо алмазный", "price": 6000, "emoji": "💎"},
            {"name": "Дилдо изумрудный", "price": 7000, "emoji": "🟢"},
            {"name": "Дилдо из урана", "price": 8000, "emoji": "☢️"},
            {"name": "Дилдо нано частиц", "price": 9000, "emoji": "⚛️"},
            {"name": "Дилдо из дилдоков", "price": 10000, "emoji": "🍆🍆🍆"}
        ]

        current_dildo = None
        for dildo in reversed(dildos):
            if balance >= dildo["price"]:
                current_dildo = dildo
                break

        if not current_dildo:
            current_dildo = {"name": "У вас нет дилдо", "emoji": "❌"}
            next_dildo = dildos[0]
            progress = f"\n\nДля получения первого дилдо нужно: {next_dildo['price'] - balance} монет"
        else:
            dildo_index = dildos.index(current_dildo)
            if dildo_index < len(dildos) - 1:
                next_dildo = dildos[dildo_index + 1]
                progress = f"\n\nДо следующего дилдо ({next_dildo['name']}): {next_dildo['price'] - balance} монет"
            else:
                progress = "\n\n🎉 У вас лучший дилдо!"

        await update.message.reply_text(
            f"🍆 {mention}, ваш текущий дилдо:\n\n"
            f"{current_dildo['emoji']} <b>{current_dildo['name']}</b>\n"
            f"💰 Ваш баланс: {balance} монет"
            f"{progress}",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"Error in my_dildo_handler: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при проверке дилдо",
            parse_mode="HTML"
        )

async def check_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Проверяем существует ли переменная
        db_name = globals().get('DB_NAME', 'Не определена')

        # Проверяем доступность файла базы данных
        db_exists = os.path.exists(DB_NAME) if 'DB_NAME' in globals() else False

        await update.message.reply_text(
            f"🔍 Проверка базы данных:\n"
            f"• DB_NAME: {db_name}\n"
            f"• Файл существует: {'✅' if db_exists else '❌'}\n"
            f"• Путь: {os.path.abspath(DB_NAME) if 'DB_NAME' in globals() else ''}"
        )

        # Дополнительная проверка подключения
        if db_exists:
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                await update.message.reply_text(
                    f"📊 Таблицы в базе:\n" + "\n".join([t[0] for t in tables])
                )
                conn.close()
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка подключения: {str(e)}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка проверки: {str(e)}")





async def buy_dildo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_data = get_user(user.id)
        if not user_data:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start")
            return

        # Формируем обращение
        user_mention = f"@{user.username}" if user.username else user.first_name
        bold_mention = f"*{user_mention}*"

        # Получаем номер дилдо из сообщения
        text = update.message.text.lower().strip()
        try:
            dildo_num = int(text.split()[2])  # "купить дилдо 1"
        except (IndexError, ValueError):
            await update.message.reply_text(
                f"{bold_mention}, укажите номер дилдо. Пример: «Купить дилдо 1»",
                parse_mode="Markdown"
            )
            return

        # Словарь с ценами дилдо
        dildo_prices = {
            1: 1000,
            2: 2000,
            3: 3000,
            4: 4000,
            5: 5000,
            6: 6000,
            7: 7000,
            8: 8000,
            9: 9000,
            10: 10000
        }

        # Проверяем существование дилдо
        if dildo_num not in dildo_prices:
            await update.message.reply_text(
                f"❌ {bold_mention}, дилдо с таким номером не существует!",
                parse_mode="Markdown"
            )
            return

        price = dildo_prices[dildo_num]

        # Проверяем баланс
        if user_data['coins'] < price:
            await update.message.reply_text(
                f"❌ {bold_mention}, недостаточно монет!\n"
                f"💵 Ваш баланс: {user_data['coins']} монет\n"
                f"💰 Стоимость: {price} монет",
                parse_mode="Markdown"
            )
            return

        # Обновляем баланс
        conn = sqlite3.connect(DB_NAME)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET coins = coins - ? WHERE user_id = ?",
                (price, user.id)
            )
            conn.commit()

            # Здесь можно добавить запись о покупке в отдельную таблицу,
            # если нужно вести инвентарь пользователя

            dildo_names = [
                "Дилдо из говна",
                "Дилдо супры",
                "Дилдо глиста",
                "Дилдо Ромы",
                "Дилдо миноса",
                "Дилдо алмазный",
                "Дилдо изумрудный",
                "Дилдо из урана",
                "Дилдо нано частиц",
                "Дилдо из дилдоков"
            ]

            await update.message.reply_text(
                f"🎉 {bold_mention}, поздравляем с покупкой!\n"
                f"🛒 Вы приобрели: *{dildo_names[dildo_num-1]}*\n"
                f"💵 Списанно: *{price}* монет\n\n"
                f"💰 Остаток: *{user_data['coins'] - price}* монет",
                parse_mode="Markdown"
)
        except sqlite3.Error as e:
            conn.rollback()
            await update.message.reply_text(
                f"⚠️ {bold_mention}, ошибка при обработке покупки",
                parse_mode="Markdown"
            )
            print(f"SQL Error: {e}")
        finally:
            conn.close()

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Произошла ошибка. Попробуйте позже",
            parse_mode="Markdown"
        )
        print(f"Error in buy_dildo: {e}")

    
TOKEN = "7810592518:AAEk2sbprah37xVzqNdA2wuuxtuWWHW9PLk"

async def universal_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    
    if any(word in text for word in ['банк положить', 'положить в банк', 'в банк']):
        return await bank_deposit(update, context)

    if text in ['б', 'баланс']:
        return await balance(update, context)
    elif text in ['бонус', 'ежедневный бонус']:
        return await daily(update, context)
    elif text in ['топ', 'топы']:
        return await tops_command(update, context)
    
    elif text.startswith('боулинг '):
        bet_text = text.split()[2] if len(text.split()) > 2 else None
        context.args = [bet_text] if bet_text else []
        return await bowling_bet_handler(update, context)
    elif (text.startswith('передать ') or text.startswith('дать ')) and update.message.reply_to_message:
        return await transfer_coins(update, context)
    elif text in ['дома', 'дом']:
        return await houses(update, context)
    elif text in ['яхта', 'яхты']:
        return await yachts(update, context)
    elif text in ['телефон', 'телефоны']:
        return await phones(update, context)
    elif text in ['самолет', 'самолеты','самолёт', 'самолёты']:
        return await planes(update, context)
    elif text in ['машина', 'машины','машына', 'машыны']:
        return await cars(update, context)
    elif text in ['банк', 'банковский счет','мой банк', 'банковский счёт']:
        return await bank_balance(update, context)
    elif text.startswith(('банк снять', 'снять')):
        return await bank_withdraw(update, context)
    elif text.startswith(('дилдо', 'дилда')):
        return await dildos(update, context)
    elif text.startswith(('купить дилдо', 'купить дилда')):
        return await buy_dildo(update, context)
    elif text.startswith(('мой дилдо', 'мой дилда')):
        return await my_dildo_handler(update, context)
    elif text.startswith(('кейсы', 'кейсики')):
        return await cases_handler(update, context)
    elif text.startswith(('тапалка', 'тапать')):
        return await tapalka(update, context)
    elif text.startswith(('вывести', 'вывести клики')):
        return await handle_withdraw(update, context)
    elif text.startswith(('купить кейс', 'купить кейсы')):
        return await buy_case(update, context)
    elif text.startswith(('инвентарь', 'мой инвентарь')):
        return await inventory_handler(update, context)
    elif text.startswith(('открыть кейс', 'открыть кейсы')):
        return await open_case(update, context)
    elif text.startswith(('контакты', 'связь')):
        return await contacts(update, context)
    elif text.startswith(('банк казино', 'казино банк')):
        return await bank_command(update, context)
    elif text.startswith(('ограбить банк казино', ' ограбить казино банк', 'ограбить банк')):
        return await rob_bank(update, context)
        
        
    
                          

    
    
    elif text.startswith(('футбол', 'фудбол')):
        return await football_handler(update, context)
    elif text.startswith(('баскетбол', 'боскетбол')):
        return await basketball_handler(update, context)
    elif text.startswith(('бот', 'ботик')):
        return await bot(update, context)
    elif text.startswith(('валейбол', 'волейбол')):
        return await volleyball_bet_handler(update, context)
    elif text.startswith(('дартс', 'дарс')):
        return await darts_bet_handler(update, context)
    elif text.startswith(('кубик', 'кубек')):
        return await dice_handler(update, context)
    elif text.startswith(('орел', 'решка')):
        return await coin_flip_handler(update, context)
    elif text.startswith(('казино', 'козино')):
        return await  casino_handler(update, context)
        
    elif text.startswith(('ограбить казну', 'казна ограбить')):
        return await rob_treasury(update, context)
    elif text.startswith(('купить дом', 'дом купить')):
        return await  buy_house_text(update, context)
    elif text.startswith(('продать дом', 'дом продать')):
        return await sell_house_text(update, context)
    elif text.startswith(('мой дом', 'мой домик')):
        return await my_house_text(update, context)
        
        
        
         
    
        
        
    
        
        



    
   

def main():
    # Создаем Application
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("fix_clicks", fix_clicks))
    application.add_handler(CommandHandler("checkdb", check_db))
    application.add_handler(CommandHandler("add_coins", add_coins))
    application.add_handler(CommandHandler("manage_clicks", add_clicks))
    application.add_handler(CommandHandler("manage_cases", manage_cases))
    application.add_handler(CommandHandler("contacts", contacts))
    
    

    application.add_handler(CommandHandler("tops", tops_command))
    application.add_handler(CallbackQueryHandler(tops_coins_handler, pattern="^tops_coins_"))
    application.add_handler(CallbackQueryHandler(tops_clicks_handler, pattern="^tops_clicks_"))
    application.add_handler(CallbackQueryHandler(tops_back_handler, pattern="^tops_back_"))
    # В функции main() добавьте обработчик callback'ов:
    application.add_handler(CallbackQueryHandler(upgrade_house_callback, pattern="^upgrade_house_"))

   
       
    

    

    
    
    
    
    # Обработчики кнопок
   
    application.add_handler(CallbackQueryHandler(tapalka_button_handler))
    
    # Текстовый обработчик
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler))
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
  
    





 
            
        
