import os

# Конфигурация бота
class Config:
    # Токен из переменных окружения bothost.ru
    TOKEN = os.getenv('API_TOKEN', '7810592518:AAEk2sbprah37xVzqNdA2wuuxtuWWHW9PLk')
    
    # Администраторы бота
    ADMINS = [6956241293]
    
    # Настройки базы данных
    DB_NAME = 'bot.db'
    
    # Настройки игры
    START_COINS = 100
    START_CLICKS = 50
    DAILY_BONUS = 1000
    CLICK_REWARD = 1
    
    # Цены
    REGULAR_CASE_PRICE = 100
    GOLDEN_CASE_PRICE = 1000
    
    # Версия бота
    VERSION = "2.0"

config = Config()
