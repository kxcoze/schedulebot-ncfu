from aiogram import Bot
from db.models import User, Chat, Message


def check_existing_user(func):
    async def wrapped(*args, **kwargs):
        message = args[0]
        db_session = message.bot.get("db")
        async with db_session() as session:
            user: User = await session.get(User, message.chat.id)
            if not user:
                await session.merge(User(id=message.chat.id))
                await session.commit()
        return await func(*args, **kwargs)

    return wrapped


def add_message_id_in_db_for_group(func):
    async def wrapped(*args, **kwargs):
        message = await func(*args, **kwargs)
        bot = Bot.get_current()
        if message is not None and message.chat.type in {"group", "channel"}:
            db_session = bot.get("db")
            async with db_session() as session:
                chat: Chat = await session.get(Chat, message.chat.id)
                if not chat:
                    chat = await session.merge(Chat(id=message.chat.id))
                    await session.commit()
                await session.merge(Message(id=message.message_id, chat=chat))
                await session.commit()
        return message

    return wrapped
