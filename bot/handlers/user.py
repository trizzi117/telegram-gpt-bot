from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.utils.markdown import hbold
from bot.services.openai_service import ask_gpt, generate_image, is_prompt_safe
from bot.services.memory_service import save_message, get_short_memory, save_summary, get_last_summary
from bot.services.payment_service import check_subscription, get_user_limits, generate_payment_link
from bot.config import FREE_USER_LIMIT
import asyncio
import datetime
from loguru import logger

router = Router()

# Клавиатура с основными кнопками
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❓ Помощь"), KeyboardButton(text="💳 Подписка")],
        [KeyboardButton(text="🔄 Новый диалог"), KeyboardButton(text="📊 Мой лимит")],
        [KeyboardButton(text="🖼 Создать изображение")]
    ],
    resize_keyboard=True
)

# Кнопка для подписки
subscribe_button = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="💳 Оформить подписку")]],
    resize_keyboard=True
)

# Состояние для генерации изображений
image_generation_state = {}

@router.message(CommandStart())
async def cmd_start(message: Message):
    summary = await get_last_summary(message.from_user.id)
    greeting = "Привет! Я твой помощник. Готов выслушать и помочь 💬"
    if summary:
        greeting += f"\n\n{hbold('Краткое резюме прошлой сессии:')} {summary}"
    await message.answer(greeting, reply_markup=main_keyboard)

@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Что я умею:</b>\n\n"
        "✅ Отвечаю на вопросы и поддерживаю диалог\n"
        "✅ Помню контекст нашего разговора\n"
        "✅ Могу быть эмпатичным собеседником\n"
        "✅ Генерирую изображения по описанию (для подписчиков)\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать диалог\n"
        "/help - Показать эту справку\n"
        "/subscribe - Оформить подписку\n"
        "/new - Начать новый диалог\n"
        "/limit - Проверить лимит сообщений\n"
        "/image - Сгенерировать изображение\n\n"
        "<b>Подписка даёт:</b>\n"
        "• Доступ к GPT-4o (самая мощная модель)\n"
        "• Неограниченное количество сообщений\n"
        "• Генерация изображений через DALL-E\n"
        "• Приоритетную обработку запросов"
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("new"))
@router.message(F.text == "🔄 Новый диалог")
async def cmd_new_dialog(message: Message):
    # Не удаляем историю из БД, но сбрасываем контекст для нового диалога
    await message.answer("Начинаем новый диалог! О чём хочешь поговорить?", reply_markup=main_keyboard)

@router.message(Command("limit"))
@router.message(F.text == "📊 Мой лимит")
async def cmd_limit(message: Message):
    user_id = message.from_user.id
    is_premium = await check_subscription(user_id)
    
    if is_premium:
        await message.answer("У тебя активна подписка! Ты можешь отправлять неограниченное количество сообщений 🎉")
        return
        
    used, limit = await get_user_limits(user_id)
    remaining = max(0, limit - used)
    
    await message.answer(
        f"📊 <b>Твой лимит на сегодня:</b>\n\n"
        f"✅ Использовано: {used} из {limit}\n"
        f"✅ Осталось: {remaining} сообщений\n\n"
        f"Для снятия ограничений оформи подписку!",
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

@router.message(Command("subscribe"))
@router.message(F.text == "💳 Подписка")
@router.message(F.text == "💳 Оформить подписку")
async def cmd_subscribe(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, есть ли уже подписка
    if await check_subscription(user_id):
        await message.answer("У тебя уже есть активная подписка! Наслаждайся общением с GPT-4o без ограничений.", reply_markup=main_keyboard)
        return
    
    # Генерируем ссылки на оплату разных тарифов
    payment_link_1 = await generate_payment_link(user_id, days=30, amount=299)
    payment_link_3 = await generate_payment_link(user_id, days=90, amount=799)
    payment_link_12 = await generate_payment_link(user_id, days=365, amount=2990)
    
    # Создаем инлайн-клавиатуру с тарифами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц - 299₽", url=payment_link_1)],
        [InlineKeyboardButton(text="3 месяца - 799₽", url=payment_link_3)],
        [InlineKeyboardButton(text="12 месяцев - 2990₽", url=payment_link_12)]
    ])
    
    await message.answer(
        "Выбери подписку для доступа к GPT-4o без ограничений:\n\n"
        "✅ Без лимита на количество сообщений\n"
        "✅ Доступ к самой мощной модели GPT-4o\n"
        "✅ Генерация изображений через DALL-E\n"
        "✅ Приоритетная обработка запросов\n"
        "✅ Долгосрочная память для более глубоких диалогов",
        reply_markup=keyboard
    )

@router.message(Command("image"))
@router.message(F.text == "🖼 Создать изображение")
async def cmd_image(message: Message):
    """Обрабатывает запрос на генерацию изображения"""
    user_id = message.from_user.id
    
    # Проверяем подписку
    if not await check_subscription(user_id):
        await message.answer(
            "Генерация изображений доступна только для пользователей с подпиской.\n"
            "Оформи подписку, чтобы создавать изображения!",
            reply_markup=subscribe_button
        )
        return
    
    # Устанавливаем состояние ожидания промпта для изображения
    image_generation_state[user_id] = True
    
    await message.answer(
        "Опиши изображение, которое хочешь создать. Будь максимально конкретным.\n\n"
        "Например: 'Космонавт на лошади в стиле акварели'",
        reply_markup=main_keyboard
    )

@router.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    
    # Проверяем тип сообщения
    if not message.text:
        await message.answer("Я понимаю только текстовые сообщения. Пожалуйста, напиши текст.", reply_markup=main_keyboard)
        return
    
    # Проверяем, ожидаем ли мы промпт для генерации изображения
    if user_id in image_generation_state and image_generation_state[user_id]:
        # Удаляем состояние
        image_generation_state.pop(user_id)
        
        # Проверяем промпт на безопасность
        is_safe = await is_prompt_safe(message.text)
        if not is_safe:
            await message.answer(
                "Извини, но этот запрос нарушает правила безопасности. "
                "Пожалуйста, попробуй другой запрос без неприемлемого содержания.",
                reply_markup=main_keyboard
            )
            return
        
        # Отправляем сообщение о начале генерации
        await message.answer("Генерирую изображение, это может занять до 30 секунд...")
        
        # Показываем, что бот печатает
        await message.bot.send_chat_action(chat_id=user_id, action="upload_photo")
        
        # Генерируем изображение
        success, result = await generate_image(user_id, message.text)
        
        if success:
            # Отправляем изображение
            await message.answer_photo(
                result,
                caption=f"Изображение по запросу: {message.text}",
                reply_markup=main_keyboard
            )
        else:
            # Отправляем сообщение об ошибке
            await message.answer(f"Не удалось создать изображение: {result}", reply_markup=main_keyboard)
        
        return
    
    # Проверяем подписку и лимиты для обычных сообщений
    if not await check_subscription(user_id):
        used, limit = await get_user_limits(user_id)
        if used >= limit:
            await message.answer(
                "Подожди немного… Ты исчерпал лимит на сегодня.\n\n"
                "Оформи подписку, чтобы продолжить общение без ограничений!", 
                reply_markup=subscribe_button
            )
            return
    
    # Сохраняем сообщение пользователя
    await save_message(user_id, 'user', message.text)
    
    # Получаем контекст
    short_mem = await get_short_memory(user_id)
    summary = await get_last_summary(user_id)
    
    # Имитация набора текста
    await message.bot.send_chat_action(chat_id=user_id, action="typing")
    
    # Расчет времени "обдумывания" в зависимости от длины сообщения
    thinking_time = min(1.5, 0.5 + len(message.text) / 500)
    await asyncio.sleep(thinking_time)
    
    # Получаем ответ от GPT
    try:
        reply = await ask_gpt(user_id, message.text, short_mem, summary)
        
        # Сохраняем ответ ассистента
        await save_message(user_id, 'assistant', reply)
        
        # Отправляем ответ
        await message.answer(reply, reply_markup=main_keyboard)
        
        # Создаем summary после каждых 10 сообщений
        messages_count = len(short_mem)
        if messages_count % 10 == 0 and messages_count > 0:
            try:
                # Создаем summary на основе последних сообщений
                summary_prompt = f"Создай краткое резюме этого диалога в 1-2 предложениях:\n"
                for msg in short_mem:
                    summary_prompt += f"{msg['role']}: {msg['content']}\n"
                
                summary_text = await ask_gpt(user_id, summary_prompt, [], None)
                await save_summary(user_id, summary_text)
            except Exception as e:
                logger.error(f"Error creating summary: {e}")
    except Exception as e:
        await message.answer("Извини, произошла ошибка. Попробуй еще раз через минуту.", reply_markup=main_keyboard)
        logger.error(f"Error in message handler: {e}") 