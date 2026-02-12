import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from app.db import init_db
from app.handlers import group, parent


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Please configure .env")

    logging.basicConfig(level=logging.INFO)
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(group.router)
    dp.include_router(parent.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
