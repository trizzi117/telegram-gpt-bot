import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Принудительная перезагрузка переменных окружения из .env файла
load_dotenv(override=True)

# Настройка логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
logger.add(LOG_FILE, rotation="10 MB", level=LOG_LEVEL, backtrace=True, diagnose=True)

# Проверка наличия обязательных токенов
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения. Создайте файл .env с BOT_TOKEN=ваш_токен")
    sys.exit(1)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY не найден в переменных окружения. Создайте файл .env с OPENAI_API_KEY=ваш_ключ")
    sys.exit(1)

# Список ID администраторов бота (разделенных запятыми)
try:
    # Принудительно читаем значение из файла .env
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('ADMIN_IDS='):
                admin_ids_str = line.strip().split('=', 1)[1]
                ADMIN_IDS = [int(x) for x in admin_ids_str.split(',')]
                break
        else:
            # Если ADMIN_IDS не найден в файле, используем значение по умолчанию
            ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '1023515995').split(',')]
    logger.info(f"Администраторы бота: {ADMIN_IDS}")
except Exception as e:
    logger.error(f"Ошибка при чтении ADMIN_IDS: {e}")
    # Используем значение по умолчанию в случае ошибки
    ADMIN_IDS = [1023515995]
    logger.info(f"Используем значение администратора по умолчанию: {ADMIN_IDS}")

# Путь к файлу базы данных SQLite
DB_PATH = os.getenv('DB_PATH', 'bot.db')

# Настройки моделей OpenAI для текста
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-3.5-turbo')  # Модель для бесплатных пользователей
PREMIUM_MODEL = os.getenv('PREMIUM_MODEL', 'gpt-4o')  # Модель для платных пользователей

# Настройки моделей OpenAI для изображений
IMAGE_MODEL = os.getenv('IMAGE_MODEL', 'dall-e-3')  # Модель для генерации изображений
IMAGE_SIZE = os.getenv('IMAGE_SIZE', '1024x1024')  # Размер изображений
IMAGE_QUALITY = os.getenv('IMAGE_QUALITY', 'standard')  # Качество изображений (standard/hd)

# Параметры генерации текста
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '1024'))  # Максимальная длина ответа
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))  # Температура (креативность) от 0 до 1
TOP_P = float(os.getenv('TOP_P', '1.0'))  # Параметр top_p для семплирования

# Ограничения для бесплатных пользователей
FREE_USER_LIMIT = int(os.getenv('FREE_USER_LIMIT', '20'))  # Запросов в день

# Настройки для подписок
SUBSCRIPTION_PRICES = {
    30: int(os.getenv('PRICE_30_DAYS', '299')),  # Цена за 30 дней подписки
    90: int(os.getenv('PRICE_90_DAYS', '799')),  # Цена за 90 дней подписки
    365: int(os.getenv('PRICE_365_DAYS', '2990')),  # Цена за 365 дней подписки
}

# Настройки для уведомлений
NOTIFY_BEFORE_EXPIRATION = int(os.getenv('NOTIFY_BEFORE_EXPIRATION', '3'))  # За сколько дней уведомлять о конце подписки

# Версия бота
BOT_VERSION = "1.0.0"

# Приветственное сообщение
WELCOME_MESSAGE = os.getenv('WELCOME_MESSAGE', "Привет! Я твой помощник. Готов выслушать и помочь 💬")

logger.info(f"Бот версии {BOT_VERSION} успешно сконфигурирован")