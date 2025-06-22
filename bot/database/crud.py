from bot.database.models import SessionLocal, User, Message, Subscription, Summary, SystemPrompt
from sqlalchemy import select, desc, func, delete, update
import datetime
from loguru import logger

async def save_message_db(user_id, role, content):
    """Сохраняет сообщение в базу данных и обновляет время активности пользователя"""
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(user_id=user_id, last_active=datetime.datetime.utcnow())
            session.add(user)
        else:
            user.last_active = datetime.datetime.utcnow()
        msg = Message(user_id=user_id, role=role, content=content)
        session.add(msg)
        await session.commit()

async def get_last_messages(user_id, limit=10):
    """Получает последние сообщения пользователя"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Message).where(Message.user_id==user_id).order_by(desc(Message.created_at)).limit(limit)
        )
        return list(reversed(result.scalars().all()))

async def save_summary_db(user_id, summary):
    """Сохраняет резюме диалога в базу данных"""
    async with SessionLocal() as session:
        # Проверяем, существует ли пользователь
        user = await session.get(User, user_id)
        if not user:
            user = User(user_id=user_id, last_active=datetime.datetime.utcnow())
            session.add(user)
            
        s = Summary(user_id=user_id, content=summary)
        session.add(s)
        await session.commit()
        logger.info(f"Сохранено новое резюме для пользователя {user_id}")

async def get_last_summary_db(user_id):
    """Получает последнее резюме диалога пользователя"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Summary).where(Summary.user_id==user_id).order_by(desc(Summary.created_at)).limit(1)
        )
        s = result.scalar()
        return s.content if s else None

async def get_user_subscription(user_id):
    """Проверяет наличие активной подписки у пользователя"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Subscription).where(Subscription.user_id==user_id, Subscription.is_active==True, Subscription.expires_at > datetime.datetime.utcnow())
        )
        return result.scalar()

async def add_subscription(user_id, expires_at):
    """Добавляет или обновляет подписку пользователя"""
    async with SessionLocal() as session:
        # Проверяем, существует ли пользователь
        user = await session.get(User, user_id)
        if not user:
            user = User(user_id=user_id, last_active=datetime.datetime.utcnow())
            session.add(user)
            await session.flush()
        
        # Проверяем, есть ли уже подписка
        result = await session.execute(
            select(Subscription).where(Subscription.user_id==user_id)
        )
        subscription = result.scalar()
        
        if subscription:
            # Обновляем существующую подписку
            subscription.is_active = True
            subscription.expires_at = expires_at
            logger.info(f"Обновлена подписка для пользователя {user_id} до {expires_at}")
        else:
            # Создаем новую подписку
            subscription = Subscription(user_id=user_id, is_active=True, expires_at=expires_at)
            session.add(subscription)
            logger.info(f"Создана новая подписка для пользователя {user_id} до {expires_at}")
            
        await session.commit()
        return subscription

async def get_expiring_subscriptions(days_before=3):
    """
    Получает список подписок, которые истекают в ближайшие дни
    
    Args:
        days_before: За сколько дней до истечения срока уведомлять
        
    Returns:
        list: Список подписок, которые скоро истекут
    """
    async with SessionLocal() as session:
        # Вычисляем даты для проверки
        now = datetime.datetime.utcnow()
        future = now + datetime.timedelta(days=days_before)
        
        # Получаем активные подписки, которые истекают в ближайшие дни
        result = await session.execute(
            select(Subscription).where(
                Subscription.is_active==True,
                Subscription.expires_at > now,
                Subscription.expires_at <= future
            )
        )
        
        return result.scalars().all()

async def get_user_message_count(user_id):
    """Получает количество сообщений пользователя за последние 24 часа"""
    async with SessionLocal() as session:
        result = await session.execute(
            select(func.count(Message.id)).where(Message.user_id==user_id, Message.created_at > datetime.datetime.utcnow() - datetime.timedelta(days=1))
        )
        return result.scalar() or 0

async def get_all_users():
    """Получает список всех пользователей, отсортированный по времени последней активности"""
    async with SessionLocal() as session:
        result = await session.execute(select(User).order_by(desc(User.last_active)))
        return result.scalars().all()

async def get_stats():
    """Получает статистику использования бота"""
    async with SessionLocal() as session:
        users = await session.execute(select(func.count(User.user_id)))
        subs = await session.execute(select(func.count(Subscription.id)).where(Subscription.is_active==True, Subscription.expires_at > datetime.datetime.utcnow()))
        msgs = await session.execute(select(func.count(Message.id)).where(Message.created_at > datetime.datetime.utcnow() - datetime.timedelta(days=1)))
        return {
            'users': users.scalar() or 0,
            'subscribers': subs.scalar() or 0,
            'messages_today': msgs.scalar() or 0
        }

async def get_system_prompt_db():
    """Получает текущий системный промпт"""
    async with SessionLocal() as session:
        result = await session.execute(select(SystemPrompt).order_by(desc(SystemPrompt.id)).limit(1))
        s = result.scalar()
        return s.content if s else None

async def set_system_prompt_db(prompt):
    """Устанавливает новый системный промпт"""
    async with SessionLocal() as session:
        s = SystemPrompt(content=prompt)
        session.add(s)
        await session.commit()
        logger.info("Установлен новый системный промпт")

async def delete_old_messages(days=30):
    """Удаляет сообщения старше указанного количества дней"""
    async with SessionLocal() as session:
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        
        # Получаем количество сообщений для удаления
        count_result = await session.execute(
            select(func.count(Message.id)).where(Message.created_at < cutoff_date)
        )
        count = count_result.scalar() or 0
        
        # Удаляем сообщения
        if count > 0:
            await session.execute(
                delete(Message).where(Message.created_at < cutoff_date)
            )
            await session.commit()
            logger.info(f"Удалено {count} сообщений старше {days} дней")
        
        return count 