from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.config import ADMIN_IDS
from bot.database.crud import get_all_users, get_stats, add_subscription, delete_old_messages
from bot.services.memory_service import set_system_prompt
from aiogram.exceptions import TelegramForbiddenError
import datetime
import os
from loguru import logger

router = Router()

def admin_only(func):
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("Доступ запрещён.")
            return
        return await func(message, *args, **kwargs)
    return wrapper

@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message):
    """Показывает админ-панель с доступными командами"""
    admin_commands = (
        "🔑 <b>Админ-панель</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/stats - Статистика использования\n"
        "/users - Список пользователей\n"
        "/broadcast - Отправить сообщение всем\n\n"
        "<b>Настройки бота:</b>\n"
        "/set_prompt - Изменить системный промпт\n"
        "/show_prompt - Показать текущий промпт\n"
        "/clean_db - Очистить старые сообщения\n\n"
        "<b>Управление подписками:</b>\n"
        "/add_subscription ID DAYS - Выдать подписку\n"
        "/check_sub ID - Проверить подписку пользователя"
    )
    await message.answer(admin_commands, parse_mode="HTML")

@router.message(Command("broadcast"))
@admin_only
async def broadcast(message: Message):
    text = message.text.partition(' ')[2]
    if not text:
        await message.answer("Укажите текст для рассылки после команды.")
        return
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"broadcast_confirm_{message.message_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel")]
    ])
    
    await message.answer(
        f"<b>Предпросмотр сообщения:</b>\n\n{text}\n\n"
        f"Сообщение будет отправлено всем пользователям. Подтвердите действие.",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith("broadcast_confirm_"))
async def broadcast_confirm(callback_query):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("Доступ запрещён.")
        return
    
    message_id = int(callback_query.data.split("_")[2])
    original_message = await callback_query.bot.get_message(
        callback_query.message.chat.id, 
        message_id
    )
    
    text = original_message.text.partition(' ')[2]
    users = await get_all_users()
    count = 0
    failed = 0
    
    # Показываем статус отправки
    status_message = await callback_query.message.edit_text(
        "Отправка сообщений...\nОбработано: 0 из {total}".format(total=len(users)),
        reply_markup=None
    )
    
    for i, user in enumerate(users):
        try:
            await callback_query.bot.send_message(user.user_id, text)
            count += 1
        except TelegramForbiddenError:
            failed += 1
        except Exception as e:
            logger.error(f"Error sending broadcast to {user.user_id}: {e}")
            failed += 1
            
        # Обновляем статус каждые 10 пользователей
        if i % 10 == 0:
            await status_message.edit_text(
                f"Отправка сообщений...\nОбработано: {i+1} из {len(users)}"
            )
    
    await status_message.edit_text(
        f"✅ Рассылка завершена.\n"
        f"Доставлено: {count}\n"
        f"Не доставлено: {failed}"
    )

@router.callback_query(lambda c: c.data == "broadcast_cancel")
async def broadcast_cancel(callback_query):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("Доступ запрещён.")
        return
    
    await callback_query.message.edit_text("❌ Рассылка отменена.", reply_markup=None)
    await callback_query.answer()

@router.message(Command("users"))
@admin_only
async def users_list(message: Message):
    users = await get_all_users()
    if not users:
        await message.answer("Пользователей пока нет.")
        return
    
    # Ограничиваем вывод 20 пользователями
    users = users[:20]
    text = '\n'.join([f"ID: {u.user_id} — Активность: {u.last_active.strftime('%d.%m %H:%M')}" for u in users])
    
    await message.answer(
        f"👥 <b>Последние {len(users)} пользователей:</b>\n\n{text}\n\n"
        f"Всего пользователей: {len(await get_all_users())}",
        parse_mode="HTML"
    )

@router.message(Command("set_prompt"))
@admin_only
async def set_prompt_cmd(message: Message):
    prompt = message.text.partition(' ')[2]
    if not prompt:
        await message.answer(
            "Укажите текст промпта после команды.\n"
            "Пример: /set_prompt Ты — дружелюбный ассистент. Отвечай коротко и по делу."
        )
        return
        
    await set_system_prompt(prompt)
    await message.answer("✅ Промпт обновлён.")

@router.message(Command("show_prompt"))
@admin_only
async def show_prompt_cmd(message: Message):
    from bot.services.memory_service import get_system_prompt
    prompt = await get_system_prompt()
    
    if not prompt:
        await message.answer("Системный промпт не задан.")
        return
        
    await message.answer(f"📝 <b>Текущий системный промпт:</b>\n\n{prompt}", parse_mode="HTML")

@router.message(Command("stats"))
@admin_only
async def stats(message: Message):
    stats_data = await get_stats()
    
    # Форматируем дату для красивого вывода
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")
    
    stats_text = (
        f"📊 <b>Статистика на {current_date}</b>\n\n"
        f"👥 Пользователей: {stats_data['users']}\n"
        f"💳 Активных подписчиков: {stats_data['subscribers']}\n"
        f"💬 Сообщений за день: {stats_data['messages_today']}\n\n"
        f"Коэффициент конверсии: {round(stats_data['subscribers']/max(1, stats_data['users'])*100, 1)}%"
    )
    
    await message.answer(stats_text, parse_mode="HTML")

@router.message(Command("add_subscription"))
@admin_only
async def add_subscription_cmd(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "ℹ️ <b>Использование:</b>\n"
            "/add_subscription USER_ID DAYS\n\n"
            "<b>Пример:</b> /add_subscription 123456789 30",
            parse_mode="HTML"
        )
        return
        
    try:
        user_id = int(parts[1])
        days = int(parts[2])
        
        if days <= 0:
            await message.answer("❌ Количество дней должно быть положительным числом.")
            return
            
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        await add_subscription(user_id, expires_at)
        
        # Форматируем дату окончания подписки
        expires_formatted = expires_at.strftime("%d.%m.%Y %H:%M")
        
        await message.answer(
            f"✅ Подписка для пользователя {user_id} добавлена!\n"
            f"Действует до: {expires_formatted}"
        )
        
        # Уведомляем пользователя
        try:
            await message.bot.send_message(
                user_id, 
                f"🎉 Поздравляем! Тебе активирована подписка на {days} дней.\n"
                f"Теперь у тебя доступ к GPT-4o без ограничений!"
            )
        except TelegramForbiddenError:
            await message.answer("⚠️ Не удалось отправить уведомление пользователю.")
            
    except ValueError:
        await message.answer("❌ Неверный формат. USER_ID и DAYS должны быть числами.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("check_sub"))
@admin_only
async def check_subscription_cmd(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Укажите ID пользователя: /check_sub USER_ID")
        return
        
    try:
        user_id = int(parts[1])
        from bot.services.payment_service import check_subscription
        
        is_subscribed = await check_subscription(user_id)
        if is_subscribed:
            # Получаем информацию о подписке
            from bot.database.crud import get_user_subscription
            sub = await get_user_subscription(user_id)
            expires_at = sub.expires_at.strftime("%d.%m.%Y %H:%M")
            
            await message.answer(
                f"✅ У пользователя {user_id} есть активная подписка\n"
                f"Действует до: {expires_at}"
            )
        else:
            await message.answer(f"❌ У пользователя {user_id} нет активной подписки")
            
    except ValueError:
        await message.answer("❌ Неверный формат ID пользователя")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("clean_db"))
@admin_only
async def clean_db_cmd(message: Message):
    parts = message.text.split()
    days = 30  # По умолчанию удаляем сообщения старше 30 дней
    
    if len(parts) > 1:
        try:
            days = int(parts[1])
        except ValueError:
            await message.answer("❌ Неверный формат. Укажите количество дней числом.")
            return
    
    # Создаем клавиатуру для подтверждения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"clean_confirm_{days}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="clean_cancel")]
    ])
    
    await message.answer(
        f"⚠️ <b>Внимание!</b>\n\n"
        f"Вы собираетесь удалить все сообщения старше {days} дней.\n"
        f"Эта операция необратима. Подтвердите действие.",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith("clean_confirm_"))
async def clean_confirm(callback_query):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("Доступ запрещён.")
        return
    
    days = int(callback_query.data.split("_")[2])
    
    # Показываем статус
    status_message = await callback_query.message.edit_text(
        "🔄 Удаление старых сообщений...",
        reply_markup=None
    )
    
    # Удаляем старые сообщения
    deleted_count = await delete_old_messages(days)
    
    await status_message.edit_text(
        f"✅ Очистка завершена.\n"
        f"Удалено {deleted_count} сообщений старше {days} дней."
    )

@router.callback_query(lambda c: c.data == "clean_cancel")
async def clean_cancel(callback_query):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("Доступ запрещён.")
        return
    
    await callback_query.message.edit_text("❌ Операция отменена.", reply_markup=None)
    await callback_query.answer() 