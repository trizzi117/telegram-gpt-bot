from bot.database.crud import get_user_subscription, get_user_message_count, add_subscription
from bot.config import FREE_USER_LIMIT
import datetime
import uuid
from loguru import logger

async def check_subscription(user_id):
    """Проверяет наличие активной подписки у пользователя"""
    sub = await get_user_subscription(user_id)
    return sub and sub.is_active

async def get_user_limits(user_id):
    """Возвращает количество использованных запросов и лимит для пользователя"""
    used = await get_user_message_count(user_id)
    limit = 9999 if await check_subscription(user_id) else FREE_USER_LIMIT
    return used, limit

async def generate_payment_link(user_id, days=30, amount=299):
    """
    Генерирует ссылку для оплаты подписки через СБП
    
    В реальной интеграции здесь будет вызов API платежной системы
    и получение ссылки на оплату
    """
    # Заглушка - в реальности здесь будет обращение к платежному API
    payment_id = str(uuid.uuid4())
    logger.info(f"Сгенерирована ссылка на оплату для пользователя {user_id}: {payment_id}")
    
    # В реальной интеграции здесь будет URL для оплаты
    return f"https://payment-system.example/pay/{payment_id}?amount={amount}&days={days}"

async def process_successful_payment(payment_id, user_id, days=30):
    """
    Обрабатывает успешный платеж
    
    В реальной интеграции эта функция будет вызываться 
    через вебхук от платежной системы
    """
    try:
        # Вычисляем дату окончания подписки
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        
        # Добавляем или обновляем подписку
        subscription = await add_subscription(user_id, expires_at)
        
        logger.info(f"Активирована подписка для пользователя {user_id} до {expires_at}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при обработке платежа {payment_id}: {e}")
        return False 