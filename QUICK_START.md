# 🚀 Быстрый старт Telegram-бота с GPT-4o

Это краткая инструкция по быстрому запуску бота. Для подробной информации смотрите [полную инструкцию](INSTRUCTION.md).

## 📋 Шаги по запуску

### 1️⃣ Подготовка

1. **Получите токен бота в Telegram**:
   - Напишите [@BotFather](https://t.me/BotFather) в Telegram
   - Отправьте команду `/newbot`
   - Следуйте инструкциям и сохраните полученный токен

2. **Получите API-ключ OpenAI**:
   - Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)
   - Создайте API-ключ в разделе API Keys

### 2️⃣ Установка

1. **Скачайте код бота**:
   ```bash
    git clone https://github.com/trizzi117/telegram-gpt-bot.git

   cd telegram-gpt-bot
   ```

2. **Создайте виртуальное окружение и установите зависимости**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Создайте файл `.env` с настройками**:
   ```
   BOT_TOKEN=ваш_токен_бота
   OPENAI_API_KEY=ваш_ключ_openai
   ADMIN_IDS=ваш_id_в_telegram
   ```

### 3️⃣ Запуск

1. **Запустите бота**:
   ```bash
   python main.py
   ```

2. **Для постоянной работы** используйте screen или systemd:
   ```bash
   screen -S bot
   python main.py
   # Нажмите Ctrl+A, затем D для отключения от screen
   ```

## 📱 Основные команды бота

### Для пользователей:
- `/start` — начать диалог
- `/help` — показать справку
- `/subscribe` — оформить подписку
- `/image` — создать изображение (для подписчиков)

### Для администраторов:
- `/admin` — показать админ-панель
- `/stats` — статистика использования
- `/broadcast` — отправить сообщение всем пользователям

## ❓ Проблемы?

Если бот не работает:
1. Проверьте логи: `cat bot.log`
2. Убедитесь, что токены в `.env` указаны правильно
3. Проверьте соединение с интернетом

Подробная инструкция: [INSTRUCTION.md](INSTRUCTION.md) 