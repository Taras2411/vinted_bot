import asyncio
import time
from aiosqlite import Connection
from db.repositories import (
    get_active_searches,
    add_item,
    link_item_to_search,
)
from parser.parser import parse_vinted
from bot.config import PARSER_INTERVAL_MINUTES as N

# Ограничиваем количество ОДНОВРЕМЕННО открытых браузеров (чтобы не съело RAM)
MAX_CONCURRENT_PARSERS = 5
browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PARSERS)

# Блокировка для базы данных (предотвращает "SQL statements in progress")
db_lock = asyncio.Lock()

async def process_search(db: Connection, search: dict):
    start_time = time.perf_counter()
    search_id = search['id']
    
    try:
        # 1. ПАРАЛЛЕЛЬНЫЙ ПАРСИНГ
        async with browser_semaphore:
            print(f"[INFO] Начинаю парсинг: {search['title']} (ID {search_id})")
            items = await parse_vinted(search["vinted_url"])
        
        if not items:
            print(f"[INFO] Ничего не найдено для ID {search_id}")
            return

        # 2. ПОСЛЕДОВАТЕЛЬНАЯ ЗАПИСЬ В БД (под защитой Lock)
        async with db_lock:
            for item in items:
                # ВАЖНО: В обновленных репозиториях commit убран для скорости
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
                await link_item_to_search(db, search_id, item_id)
            
            # Один коммит на весь список товаров — это ОЧЕНЬ быстро
            await db.commit()
            
        execution_time = time.perf_counter() - start_time
        print(f"[SUCCESS] Поиск ID {search_id} обработан. Найдено: {len(items)}. Время: {execution_time:.2f}с")

    except Exception as e:
        print(f"[ERROR] Ошибка в поиске {search_id}: {e}")

async def scheduler_loop(db: Connection, shutdown_event: asyncio.Event):
    print(f"[INFO] Цикл парсинга запущен. Интервал: {N} мин.")
    
    while not shutdown_event.is_set():
        try:
            searches = await get_active_searches(db)
            
            if not searches:
                print("[INFO] Активных поисков нет.")
            else:
                print(f"[INFO] Запускаю {len(searches)} поисков...")
                # Запускаем все поиски параллельно
                tasks = [process_search(db, search) for search in searches]
                await asyncio.gather(*tasks)

        except Exception as e:
            print(f"[ERROR] Ошибка в scheduler_loop: {e}")

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=N * 60)
        except asyncio.TimeoutError:
            continue

    print("[INFO] Цикл парсинга остановлен.")