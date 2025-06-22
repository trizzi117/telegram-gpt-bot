import openai
from openai import AsyncOpenAI
from bot.config import (
    OPENAI_API_KEY, DEFAULT_MODEL, PREMIUM_MODEL, MAX_TOKENS, TEMPERATURE, TOP_P,
    IMAGE_MODEL, IMAGE_SIZE, IMAGE_QUALITY
)
from bot.services.payment_service import check_subscription
from bot.services.memory_service import get_system_prompt
import os
import tempfile
import uuid
from loguru import logger

# Создаем клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def ask_gpt(user_id, user_message, short_mem, summary):
    """
    Отправляет запрос к модели GPT и возвращает ответ
    
    Args:
        user_id: ID пользователя
        user_message: Текст сообщения пользователя
        short_mem: Краткосрочная память (последние сообщения)
        summary: Резюме предыдущих диалогов
        
    Returns:
        str: Ответ модели
    """
    is_premium = await check_subscription(user_id)
    model = PREMIUM_MODEL if is_premium else DEFAULT_MODEL
    system_prompt = await get_system_prompt()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if summary:
        messages.append({"role": "system", "content": f"Summary: {summary}"})
    messages += short_mem
    messages.append({"role": "user", "content": user_message})
    try:
        for attempt in range(3):  # Пробуем 3 раза
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                )
                return response.choices[0].message.content.strip()
            except openai.RateLimitError:
                if attempt == 2:  # Если это была последняя попытка
                    raise
                await asyncio.sleep(20 * (attempt + 1))  # Увеличиваем время ожидания с каждой попыткой
    except openai.RateLimitError:
        logger.error(f"OpenAI API rate limit exceeded for user {user_id} after 3 attempts")
        return "Извини, сервер OpenAI сильно перегружен. Попробуй еще раз через пару минут."
    except openai.APIConnectionError:
        logger.error(f"OpenAI API connection error for user {user_id}")
        return "Извини, возникла проблема с подключением к OpenAI. Проверь соединение с интернетом."
    except openai.APITimeoutError:
        logger.error(f"OpenAI API timeout for user {user_id}")
        return "Извини, запрос к OpenAI занял слишком много времени. Попробуй еще раз."
    except Exception as e:
        logger.error(f"Error in OpenAI API: {e}")
        return "Извини, у меня возникла проблема с ответом. Попробуй еще раз через минуту."

async def generate_image(user_id, prompt, size=None):
    """
    Генерирует изображение по текстовому описанию
    
    Args:
        user_id: ID пользователя
        prompt: Текстовое описание изображения
        size: Размер изображения (если не указан, берется из конфига)
        
    Returns:
        tuple: (success, result)
            success (bool): Успешно ли сгенерировано изображение
            result (str): URL изображения или сообщение об ошибке
    """
    # Проверяем подписку - генерация изображений только для премиум пользователей
    is_premium = await check_subscription(user_id)
    if not is_premium:
        return False, "Генерация изображений доступна только для пользователей с подпиской. Оформи подписку!"
    
    # Используем размер из параметра или из конфига
    image_size = size or IMAGE_SIZE
    
    # Улучшаем промпт для лучших результатов
    enhanced_prompt = enhance_image_prompt(prompt)
    
    try:
        # Генерируем изображение
        logger.info(f"Generating image for user {user_id} with prompt: {prompt}")
        response = await client.images.generate(
            model=IMAGE_MODEL,
            prompt=enhanced_prompt,
            size=image_size,
            quality=IMAGE_QUALITY,
            n=1,
        )
        
        # Получаем URL изображения
        image_url = response.data[0].url
        logger.info(f"Image generated successfully for user {user_id}")
        
        # Возвращаем URL изображения
        return True, image_url
        
    except openai.RateLimitError:
        logger.error(f"Image generation rate limit exceeded for user {user_id}")
        return False, "Превышен лимит запросов на генерацию изображений. Попробуй позже."
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return False, f"Ошибка при генерации изображения: {str(e)}"

def enhance_image_prompt(prompt):
    """
    Улучшает промпт для генерации изображений, добавляя детали для лучшего результата
    
    Args:
        prompt: Исходный промпт
        
    Returns:
        str: Улучшенный промпт
    """
    # Если промпт короткий, добавляем детали для лучшего результата
    if len(prompt) < 20:
        return f"{prompt}, high quality, detailed, 4k, realistic"
    
    # Если в промпте нет упоминания качества, добавляем его
    quality_terms = ["quality", "detailed", "4k", "hd", "высокое качество", "детализированное"]
    has_quality = any(term in prompt.lower() for term in quality_terms)
    
    if not has_quality:
        return f"{prompt}, high quality"
    
    return prompt

async def is_prompt_safe(prompt):
    """
    Проверяет промпт на безопасность с помощью модерации OpenAI
    
    Args:
        prompt: Текст для проверки
        
    Returns:
        bool: True если промпт безопасен, False если нарушает правила
    """
    try:
        response = await client.moderations.create(input=prompt)
        
        # Получаем результат модерации
        is_flagged = response.results[0].flagged
        
        # Если промпт помечен как небезопасный, логируем категории нарушений
        if is_flagged:
            categories = response.results[0].categories
            flagged_categories = [cat for cat, flagged in categories.items() if flagged]
            logger.warning(f"Unsafe prompt detected. Categories: {flagged_categories}. Prompt: {prompt}")
            
        return not is_flagged
    except Exception as e:
        logger.error(f"Error in moderation API: {e}")
        # В случае ошибки возвращаем True, чтобы не блокировать пользователя
        return True