"""
Точка входа для запуска Telegram-бота с GPT-4o, памятью и подписками.
Просто импортирует и запускает основной модуль.
"""

import asyncio
from bot.main import main

if __name__ == '__main__':
    asyncio.run(main()) 