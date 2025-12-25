from parser.parser_service import scheduler_loop
from db import *
from typing import Optional
from db.repositories import *
import asyncio
from datetime import datetime
from bot import start_bot
from bot.notifier import notifier_loop, shutdown_event

async def main():
    await init_db()
    print("Database initialized.")
    db = await get_db()
    try:
        await asyncio.gather(
            start_bot(db),
            scheduler_loop(db),
            notifier_loop(db),
        )
    finally:
        shutdown_event.set()
        await close_db()

if __name__ == "__main__":
    asyncio.run(main())