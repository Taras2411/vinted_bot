from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio
from db import (get_db, close_db)

from db.repositories import *
from bot.config import BOT_TOKEN as TOKEN

# Initialize bot and dispatcher
bot = Bot(
    token=TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

async def start_bot(db, shutdown_event):
    print("Starting bot...")
    dp["db"] = db

    # FIX: handle_signals=False prevents aiogram from hijacking Ctrl+C
    polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))

    await shutdown_event.wait()

    print("Stopping bot...")
    polling_task.cancel()
    
    # Cleanly wait for the polling task to finish
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
        
    await bot.session.close()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Welcome to Vinted Bot! 🤖\n"
        "Use /help to see available commands."
    )
    # add user to database
    await get_or_create_user(dp["db"], message.from_user.id, message.from_user.username)




@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/add_search <vinted_url> <title> - Add a new search\n"
        "/remove_search <id> - Remove a search by ID\n"
        "/list_searches - List all your searches"
    )


@dp.message(Command("add_search"))
async def cmd_add_search(message: Message):
    db = dp["db"]
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /add_search <vinted_url> <title>")
        return
    vinted_url = args[1]
    title = args[2]
    try:
        user = await get_user_by_tg_id(db, message.from_user.id)
        if not user:
            await message.answer("You are not registered yet. Use /start to register.")
            return
        user_id = user['id']
        search = await add_search(db, user_id, title, vinted_url)
        await message.answer(f"✅ Search added with ID: {search['id']}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")



@dp.message(Command("remove_search"))
async def cmd_remove_search(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /remove_search <id>")
        return
    
    try:
        search_id = int(args[1])
        await remove_search(dp["db"], search_id)
        await message.answer(f"✅ Search removed!")
    except ValueError:
        await message.answer("Invalid search ID")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")


@dp.message(Command("list_searches"))
async def cmd_list_searches(message: Message):
    try:
        user_id = await get_user_by_tg_id(dp["db"], message.from_user.id)
        if not user_id:
            await message.answer("You are not registered yet. Use /start to register.")
            return
        searches = await get_user_searches(dp["db"], user_id['id'])
        if not searches:
            await message.answer("No searches yet")
            return
        
        response = "📋 Your searches:\n\n"
        for search in searches:
            response += f"ID: {search['id']} - {search['title']} - {search['vinted_url']}\n"
        await message.answer(response)
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")


# send notification function

async def send_notification(user_id: int, text: str, image_url: str = None):
    try:
        if image_url:
            # Явно добавляем parse_mode=ParseMode.HTML
            await bot.send_photo(
                chat_id=user_id, 
                photo=image_url, 
                caption=text, 
                parse_mode=ParseMode.HTML
            )
        else:
            # Явно добавляем parse_mode=ParseMode.HTML
            await bot.send_message(
                chat_id=user_id, 
                text=text, 
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"Failed to send message to {user_id}: {e}")