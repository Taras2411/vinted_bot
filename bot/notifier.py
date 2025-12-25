from db.repositories import *
import asyncio
from .bot_logic import *
from .config import NOTIFIER_INTERVAL_MINUTES as M

shutdown_event = asyncio.Event()

async def notifier_loop(db):
    while not shutdown_event.is_set():
        try:
            searches = await get_active_searches(db)
            for search in searches:
                unsent_items = await get_unsent_items_for_search(db, search["id"])
                for item in unsent_items:
                    tg_id = await get_tg_id_by_user_id(db, search["user_id"])
                    await send_notification(tg_id, item["title"] + "\n" + item["price"] + "\n" + item["url"] + "\n" + item["brand"], item["image_url"])
                    await mark_item_as_sent(db, search["id"], item["id"])
            await asyncio.wait_for(shutdown_event.wait(), timeout=M * 60)
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"Error in notifier_loop: {e}")
            await asyncio.sleep(60)