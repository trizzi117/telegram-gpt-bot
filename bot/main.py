import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import BOT_TOKEN, NOTIFY_BEFORE_EXPIRATION
from bot.handlers import user, admin
from bot.database import models
from bot.services.memory_service import set_system_prompt
from bot.database.crud import get_expiring_subscriptions
from loguru import logger
import datetime

# Настройка логирования
logger.add("bot.log", rotation="10 MB", level="INFO")

async def load_default_prompt():
    """Загружает системный промпт из файла при первом запуске"""
    try:
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "default_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as file:
                prompt = file.read().strip()
                if prompt:
                    await set_system_prompt(prompt)
                    logger.info("Default system prompt loaded")
    except Exception as e:
        logger.error(f"Error loading default prompt: {e}")

async def check_expiring_subscriptions(bot):
    """
    Проверяет подписки, которые скоро истекут, и отправляет уведомления пользователям
    """
    try:
        # Получаем подписки, которые истекают в ближайшие дни
        expiring_subs = await get_expiring_subscriptions(NOTIFY_BEFORE_EXPIRATION)
        
        for sub in expiring_subs:
            # Форматируем дату окончания подписки
            expires_at = sub.expires_at.strftime("%d.%m.%Y")
            
            # Отправляем уведомление
            try:
                await bot.send_message(
                    sub.user_id,
                    f"⚠️ <b>Внимание!</b>\n\n"
                    f"Твоя подписка истекает {expires_at}.\n"
                    f"Чтобы продолжить пользоваться всеми преимуществами, "
                    f"не забудь продлить подписку командой /subscribe.",
                    parse_mode="HTML"
                )
                logger.info(f"Sent expiration notification to user {sub.user_id}")
            except Exception as e:
                logger.error(f"Failed to send expiration notification to user {sub.user_id}: {e}")
    except Exception as e:
        logger.error(f"Error checking expiring subscriptions: {e}")

async def scheduled_tasks(bot):
    """Выполняет регулярные задачи по расписанию"""
    while True:
        try:
            # Проверяем подписки раз в день в 10:00
            now = datetime.datetime.now()
            if now.hour == 10 and now.minute < 5:  # Выполняем между 10:00 и 10:05
                await check_expiring_subscriptions(bot)
                # Ждем час после выполнения, чтобы не запускать задачу повторно
                await asyncio.sleep(3600)
            else:
                # Проверяем каждые 5 минут
                await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Error in scheduled tasks: {e}")
            await asyncio.sleep(300)

async def main():
    try:
        # Инициализация базы данных
        logger.info("Initializing database...")
        await models.init_db()
        
        # Загрузка системного промпта
        await load_default_prompt()
        
        # Запуск бота
        logger.info("Starting bot...")
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(user.router)
        dp.include_router(admin.router)
        
        # Запускаем фоновые задачи
        asyncio.create_task(scheduled_tasks(bot))
        
        # Запуск поллинга
        logger.info("Bot started")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main()) 