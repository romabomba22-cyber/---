import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(name)

class Database:
    def init(self, db_name='bot.db'):
        self.db_name = db_name
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Инициализация всех таблиц базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                coins INTEGER DEFAULT 100,
                clicks INTEGER DEFAULT 50,
                balance INTEGER DEFAULT 0,
                bank INTEGER DEFAULT 0,
                last_daily TEXT,
                casino_wins INTEGER DEFAULT 0,
                casino_losses INTEGER DEFAULT 0,
                registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Таблица инвентаря
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_type TEXT CHECK(item_type IN ('case_regular', 'case_golden')),
                quantity INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            ''')
            
            # Таблица бизнесов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('shop', 'cafe', 'factory', 'complex')),
                level INTEGER DEFAULT 1,
                income INTEGER DEFAULT 0,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')
            
            # Таблица транзакций
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT CHECK(type IN ('daily', 'click', 'casino_win', 'casino_loss', 'case_open', 'business_income')),
                amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')
            
            conn.commit()
            logger.info("✅ База данных инициализирована")
    
    def get_user(self, user_id):
        """Получить данные пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем пользователя
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users (user_id, coins, clicks) 
                    VALUES (?, 100, 50)
                ''', (user_id,))
                conn.commit()
                
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()
            
            # Получаем инвентарь
            cursor.execute('''
SELECT 
                    SUM(CASE WHEN item_type = 'case_regular' THEN quantity ELSE 0 END) as regular_cases,
                    SUM(CASE WHEN item_type = 'case_golden' THEN quantity ELSE 0 END) as golden_cases
                FROM inventory 
                WHERE user_id = ?
            ''', (user_id,))
            inventory = cursor.fetchone()
            
            # Получаем бизнесы
            cursor.execute('SELECT COUNT(*) as business_count FROM businesses WHERE user_id = ?', (user_id,))
            business_count = cursor.fetchone()['business_count']
            
            return dict(user), dict(inventory) if inventory else {'regular_cases': 0, 'golden_cases': 0}, business_count
    
    def update_user(self, user_id, **kwargs):
        """Обновить данные пользователя"""
        if not kwargs:
            return False
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
            conn.commit()
            return cursor.rowcount > 0
    
    def add_coins(self, user_id, amount, transaction_type='other'):
        """Добавить монеты пользователю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Обновляем баланс
            cursor.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
            
            # Записываем транзакцию
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount) 
                VALUES (?, ?, ?)
            ''', (user_id, transaction_type, amount))
            
            conn.commit()
            return True
    
    def add_to_inventory(self, user_id, item_type, quantity=1):
        """Добавить предмет в инвентарь"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже такой предмет
            cursor.execute('''
                SELECT id, quantity FROM inventory 
                WHERE user_id = ? AND item_type = ?
            ''', (user_id, item_type))
            
            item = cursor.fetchone()
            
            if item:
                # Обновляем количество
                cursor.execute('''
                    UPDATE inventory SET quantity = quantity + ? 
                    WHERE id = ?
                ''', (quantity, item['id']))
            else:
                # Создаем новую запись
                cursor.execute('''
                    INSERT INTO inventory (user_id, item_type, quantity) 
                    VALUES (?, ?, ?)
                ''', (user_id, item_type, quantity))
            
            conn.commit()
            return True
    
    def get_top_users(self, limit=10):
        """Получить топ пользователей по монетам"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, first_name, coins 
                FROM users 
                ORDER BY coins DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Глобальный объект базы данных
db = Database()
