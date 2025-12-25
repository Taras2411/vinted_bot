import aiosqlite
from pathlib import Path

# путь до базы данных
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "vinted.db"

# глобальное соединение (одно на приложение)
_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """
    Возвращает активное соединение с БД.
    Создаёт его при первом вызове.
    """
    global _db

    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        await _db.execute("PRAGMA foreign_keys = ON;")
        _db.row_factory = aiosqlite.Row

    return _db


async def init_db() -> None:
    """
    Инициализация базы данных:
    - создаёт папку data/
    - применяет schema.sql
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    db = await get_db()

    schema_path = BASE_DIR / "db" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        await db.executescript(f.read())

    await db.commit()


async def close_db() -> None:
    """
    Корректно закрывает соединение с БД
    (вызывать при shutdown бота)
    """
    global _db

    if _db is not None:
        await _db.close()
        _db = None

if __name__ == "__main__":
    import asyncio

    async def main():
        await init_db()
        print("Database initialized.")
        # stop code here
        await close_db()

    asyncio.run(main())