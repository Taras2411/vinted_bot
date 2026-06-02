from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio
from db import (get_db, close_db)

from db.repositories import *
from bot.config import BOT_TOKEN as TOKEN
from parser.regions import (
    GROUP_REPRESENTATIVES,
    group_of,
    param_signature,
    make_region_twin,
)
from parser.locales import resolve as resolve_locale

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
    print("Help command invoked")
    await message.answer(
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/add_search vinted_url title - Add a new search\n"
        "/auto_region [search_id] - Mirror existing search(es) across both region groups\n"
        "/remove_search id - Remove a search by ID\n"
        "/list_searches - List all your searches\n"
        "\n"
        "auto_region scope: default (fr+cz), 1 (western group), 2 (eastern group), all"
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



@dp.message(Command("auto_region"))
async def cmd_auto_region(message: Message):
    """Ensure existing searches are mirrored across both Vinted region groups.

    Each unique search (combination of filters) needs at most two copies: one
    anywhere in the "fr group" and one anywhere in the "cz group". For every
    target search we create the missing group's copy (using fr / cz as the
    representative domain) and skip a group that already has the search in any
    of its domains.

    Usage: /auto_region [search_id]
      search_id (optional): mirror only that search; omit to mirror all of yours.
    """
    db = dp["db"]

    # Optional numeric search id.
    search_id = None
    for tok in message.text.split()[1:]:
        if tok.isdigit():
            search_id = int(tok)
        else:
            await message.answer("Usage: /auto_region [search_id]")
            return

    try:
        user = await get_user_by_tg_id(db, message.from_user.id)
        if not user:
            await message.answer("You are not registered yet. Use /start to register.")
            return
        user_id = user['id']

        searches = await get_user_searches(db, user_id)
        if search_id is not None:
            targets = [s for s in searches if s['id'] == search_id]
            if not targets:
                await message.answer(f"❌ No active search with ID {search_id}.")
                return
        else:
            targets = list(searches)
            if not targets:
                await message.answer("You have no active searches yet. Use /add_search first.")
                return

        # (group index, filter signature) already covered by an existing search.
        # Any domain inside a group counts as covering that group.
        covered = set()
        for s in searches:
            g = group_of(resolve_locale(s['vinted_url']).domain)
            if g is not None:
                covered.add((g, param_signature(s['vinted_url'])))

        added = []
        for s in targets:
            sig = param_signature(s['vinted_url'])
            base_title = s['title'] or "search"
            for group_index, rep_domain in enumerate(GROUP_REPRESENTATIVES):
                if (group_index, sig) in covered:
                    continue
                twin = await make_region_twin(s['vinted_url'], rep_domain)
                if twin is None:
                    continue
                covered.add((group_index, sig))
                new = await add_search(db, user_id, f"{base_title} [{rep_domain}]", twin)
                added.append((rep_domain, new['id']))

        if not added:
            await message.answer("Nothing to add — every search already covers both region groups.")
            return

        lines = "\n".join(f"  • {domain} (ID {sid})" for domain, sid in added)
        await message.answer(f"✅ Added {len(added)} region searches:\n{lines}")
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
        
        # Split message if it exceeds Telegram's limit (4096 characters)
        max_length = 4096
        if len(response) <= max_length:
            await message.answer(response)
        else:
            messages = [response[i:i+max_length] for i in range(0, len(response), max_length)]
            for msg in messages:
                await message.answer(msg)
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