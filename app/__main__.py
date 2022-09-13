import json
import asyncio
import logging
import logging.config

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.types.bot_command_scope import BotCommandScopeDefault
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import aiolog

from db.models import Base, Group
from handlers.commands import register_commands
from handlers.callbacks import register_callbacks
from handlers.states import register_states
from config import Config, load_config, logging_dict
from scraping.scraper import get_codes
from taskmanager import init_taskmanager

logging.config.dictConfig(logging_dict)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="help", description="Просмотр всех команд"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def main():
    config: Config = load_config()
    engine = create_async_engine(
        f"postgresql+asyncpg://{config.db.user}@{config.db.host}/{config.db.db_name}",
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
        )

    async_sessionmaker = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    if config.update_group_codes:
        groups = await get_codes()
        async with async_sessionmaker() as session:
            for group in groups:
                try:
                    await session.merge(
                        Group(
                            id=group[1],
                            name=group[0],
                        )
                    )
                    await session.commit()
                    logging.info(f"NEW DATA -> {group[0]} with id:{group[1]}")
                except:
                    logging.error("Something went wrong when insert codes")

    bot = Bot(config.bot.token, parse_mode="HTML")
    bot["db"] = async_sessionmaker
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_commands(dp)
    register_callbacks(dp)
    register_states(dp)
    await set_bot_commands(bot)

    aiolog.start()
    try:
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()
        asyncio.ensure_future(aiolog.stop(), loop=asyncio.get_event_loop())


if __name__ == "__main__":
    try:
        init_taskmanager()
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")