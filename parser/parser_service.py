import asyncio
from aiosqlite import Connection
from db.repositories import (
    get_active_searches,
    add_item,
    link_item_to_search,
)
from parser.parser import parse_vinted  # Импортируем функцию парсинга
from bot.config import PARSER_INTERVAL_MINUTES as N



async def process_search(db: Connection, search: dict):
    """
    Обработка одного поиска:
    1) парсим Vinted
    2) добавляем новые айтемы в БД
    3) создаём связь search_items
    """
    try:
        print(f"[INFO] Начинаю парсинг для поиска ID {search['id']}: {search['title']}")
        items = await parse_vinted(search["vinted_url"])
        
        if not items:
            print(f"[INFO] По поиску {search['id']} ничего не найдено.")
            return

        for item in items:
            # Добавляем товар в таблицу items
            # Функция add_item сама делает commit внутри (в исправленной версии репозитория)
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

            # Создаём связь между поиском и товаром
            await link_item_to_search(db, search["id"], item_id)
            
        print(f"[SUCCESS] Поиск ID {search['id']} обработан. Найдено товаров: {len(items)}")

    except Exception as e:
        print(f"[ERROR] Ошибка при обработке поиска {search['id']}: {e}")

async def scheduler_loop(db: Connection, shutdown_event: asyncio.Event):
    """
    Запускает основной цикл парсинга с заданным интервалом
    """
    print(f"[INFO] Цикл парсинга запущен. Интервал: {N} мин.")
    
    while not shutdown_event.is_set():
        try:
            # Получаем актуальный список активных поисков
            searches = await get_active_searches(db)
            
            if not searches:
                print("[INFO] Активных поисков не обнаружено.")
            else:
                print(f"[INFO] Найдено {len(searches)} активных поисков. Начинаю обработку...")
                
                # ВАЖНО: Обрабатываем поиски ПО ОЧЕРЕДИ (последовательно),
                # чтобы избежать ошибки "SQL statements in progress" в SQLite.
                for search in searches:
                    if shutdown_event.is_set():
                        break
                    await process_search(db, search)

        except Exception as e:
            print(f"[ERROR] Критическая ошибка в основном цикле парсера: {e}")

        # Ожидание перед следующим кругом
        print(f"[INFO] Цикл завершен. Ожидание {N} минут до следующего запуска...")
        try:
            # Ждем либо установки события завершения, либо таймаута
            await asyncio.wait_for(shutdown_event.wait(), timeout=N * 60)
        except asyncio.TimeoutError:
            # Это нормальное поведение: таймаут вышел, продолжаем цикл
            continue
        except Exception as e:
            print(f"[ERROR] Ошибка при ожидании в парсере: {e}")
            await asyncio.sleep(10) # На случай странных ошибок

    print("[INFO] Цикл парсинга остановлен.")