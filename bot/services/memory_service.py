from bot.database.crud import (
    save_message_db, get_last_messages, save_summary_db, get_last_summary_db, get_system_prompt_db, set_system_prompt_db
)

async def save_message(user_id, role, content):
    await save_message_db(user_id, role, content)

async def get_short_memory(user_id, limit=10):
    messages = await get_last_messages(user_id, limit)
    return [{"role": m.role, "content": m.content} for m in messages]

async def save_summary(user_id, summary):
    await save_summary_db(user_id, summary)

async def get_last_summary(user_id):
    return await get_last_summary_db(user_id)

async def get_system_prompt():
    return await get_system_prompt_db()

async def set_system_prompt(prompt):
    await set_system_prompt_db(prompt) 