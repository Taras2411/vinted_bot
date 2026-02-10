import asyncio
import time
from collections import defaultdict
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

async def process_url_group(db: Connection, url: str, search_ids: list[int]):
    """
    Обрабатывает один URL.
    1. Парсит данные (один раз).
    2. Добавляет товары в БД.
    3. Привязывает найденные товары ко всем search_id, которые ждут этот URL.
    """
    start_time = time.perf_counter()
    
    try:
        # 1. ПАРАЛЛЕЛЬНЫЙ ПАРСИНГ (под семафором)
        async with browser_semaphore:
            print(f"[INFO] Начинаю парсинг URL: {url} (для {len(search_ids)} поисков)")
            items = await parse_vinted(url)
        
        if not items:
            print(f"[INFO] Ничего не найдено для URL: {url}")
            return

        # 2. ПОСЛЕДОВАТЕЛЬНАЯ ЗАПИСЬ В БД (под защитой Lock)
        async with db_lock:
            # Сначала добавляем товары в таблицу items и собираем их ID
            added_item_ids = []
            
            for item in items:
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
                added_item_ids.append(item_id)
            
            # Теперь связываем эти товары с каждым search_id из группы
            for search_id in search_ids:
                for item_id in added_item_ids:
                    await link_item_to_search(db, search_id, item_id)
            
            # Фиксируем изменения
            await db.commit()
            
        execution_time = time.perf_counter() - start_time
        print(f"[SUCCESS] URL обработан. Найдено: {len(items)} товаров. Распределено по {len(search_ids)} поискам. Время: {execution_time:.2f}с")

    except Exception as e:
        print(f"[ERROR] Ошибка при обработке URL {url}: {e}")

async def scheduler_loop(db: Connection, shutdown_event: asyncio.Event):
    print(f"[INFO] Цикл парсинга запущен. Интервал: {N} мин.")
    
    while not shutdown_event.is_set():
        try:
            searches = await get_active_searches(db)
            
            if not searches:
                print("[INFO] Активных поисков нет.")
            else:
                # Группировка поисков по URL
                # url_groups = { "https://vinted...": [id1, id2, id5], ... }
                url_groups = defaultdict(list)
                for search in searches:
                    url_groups[search["vinted_url"]].append(search["id"])
                
                print(f"[INFO] Запускаю {len(url_groups)} задач парсинга (всего поисков: {len(searches)})...")
                
                # Создаем задачи для каждой уникальной ссылки
                tasks = [
                    process_url_group(db, url, ids) 
                    for url, ids in url_groups.items()
                ]
                
                await asyncio.gather(*tasks)

        except Exception as e:
            print(f"[ERROR] Ошибка в scheduler_loop: {e}")

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=N * 60)
        except asyncio.TimeoutError:
            continue

    print("[INFO] Цикл парсинга остановлен.")