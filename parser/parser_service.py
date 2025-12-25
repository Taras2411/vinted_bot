import asyncio
from aiosqlite import Connection
import signal
from typing import List
from db import get_db
from db.repositories import (
    get_active_searches,
    add_item,
    link_item_to_search,
    get_unsent_items_for_search,
)
from parser import parse_vinted  # твоя функция парсинга
from bot.config import PARSER_INTERVAL_MINUTES as N
# Флаг для остановки
shutdown_event = asyncio.Event()


async def process_search(search: dict):
    """
    Обработка одного поиска:
    1) парсим Vinted
    2) добавляем новые айтемы в БД
    3) создаём связь search_items
    """
    db = await get_db()

    try:
        items = await parse_vinted(search["vinted_url"])
    except Exception as e:
        print(f"[ERROR] Ошибка парсинга {search['vinted_url']}: {e}")
        return

    for item in items:
        # Добавляем в таблицу items
        item_id = await add_item(
            db,
            vinted_id=item.vinted_id,
            title=item.parsed_title.name if item.parsed_title else None,
            price=item.parsed_title.price if item.parsed_title else None,
            url=item.url,
            image_url=item.image_src,
            brand=item.parsed_title.brand if item.parsed_title else None,
            created_at=None,
        )

        # Создаём связь с поиском
        await link_item_to_search(db, search["id"], item_id)



async def scheduler_loop(db: Connection):
    """
    Запускает основной цикл парсинга с заданным интервалом
    """
    while not shutdown_event.is_set():
        try:
            searches = await get_active_searches(db)
            if not searches:
                print("[INFO] Нет активных поисков.")
            else:
                print(f"[INFO] Найдено {len(searches)} активных поисков.")

            # Асинхронно обрабатываем все поиски
            await asyncio.gather(*(process_search(search) for search in searches))

        except Exception as e:
            print(f"[ERROR] Ошибка в основном цикле: {e}")

        print(f"[INFO] Ожидание {N} минут до следующего цикла...")
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=N * 60)
        except asyncio.TimeoutError:
            continue  # Таймаут истек, продолжаем цикл