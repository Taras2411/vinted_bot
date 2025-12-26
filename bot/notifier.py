from db.repositories import *
import asyncio
from .bot_logic import *
from .config import NOTIFIER_INTERVAL_MINUTES as M
from .config import TELEGRAM_NOTIFICATIONS_INTRVAL_MS as T


async def notifier_loop(db, shutdown_event: asyncio.Event):
    while not shutdown_event.is_set():
        try:
            searches = await get_active_searches(db)

            for search in searches:
                unsent_items = await get_unsent_items_for_search(db, search["id"])

                for item in unsent_items:
                    tg_id = await get_tg_id_by_user_id(db, search["user_id"])
                    
                    if not tg_id:
                        continue

                    # Формируем текст сообщения без ошибок
                    message_parts = [
                        f"<b>{item['title'] or 'Товар'}</b>",
                        f"Цена: {item['price'] or 'не указана'}",
                        f"Бренд: {item['brand'] or 'не указан'}",
                        f"Ссылка: {item['url']}"
                    ]
                    # Соединяем только существующие строки
                    text = "\n".join(message_parts)

                    await send_notification(
                        tg_id,
                        text,
                        item["image_url"]
                    )

                    await mark_item_as_sent(db, search["id"], item["id"])

                    # ЗАДЕРЖКА МЕЖДУ СООБЩЕНИЯМИ
                    await asyncio.sleep(T / 1000)

            await asyncio.wait_for(shutdown_event.wait(), timeout=M * 60)

        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"Error in notifier_loop: {e}")
            await asyncio.sleep(60)