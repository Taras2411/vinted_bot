import asyncio
import signal
import sys

from core.shutdown import shutdown_event
from parser.parser_service import scheduler_loop
from bot import start_bot
from bot.notifier import notifier_loop
from db import init_db, close_db, get_db


def request_shutdown():
    if not shutdown_event.is_set():
        print("Shutdown signal received")
        shutdown_event.set()


def setup_signal_handlers():
    """
    Кроссплатформенная установка обработчиков сигналов
    """
    try:
        loop = asyncio.get_running_loop()

        # Linux / macOS (systemd)
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, request_shutdown)

    except (NotImplementedError, RuntimeError):
        # Windows fallback
        signal.signal(signal.SIGINT, lambda s, f: request_shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: request_shutdown())


async def main():
    await init_db()
    print("Database initialized.")
    db = await get_db()

    setup_signal_handlers()

    tasks = [
        asyncio.create_task(start_bot(db, shutdown_event)),
        asyncio.create_task(scheduler_loop(db, shutdown_event)),
        asyncio.create_task(notifier_loop(db, shutdown_event)),
    ]

    try:
        # ждём пока кто-то выставит shutdown_event
        await shutdown_event.wait()

    finally:
        print("Shutting down...")

        for task in tasks:
            task.cancel()

        # корректно дожидаемся отмены
        await asyncio.gather(*tasks, return_exceptions=True)

        await close_db()
        print("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
