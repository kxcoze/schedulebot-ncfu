import re
import logging
from typing import List

from sqlalchemy import select, delete
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import MessageToDeleteNotFound

from db.models import User, Group, Chat, Message
from scraping.scraper import get_formatted_schedule
from inlinekeyboard import show_ikeyboard_preferences, cbd_poll, cbd_choice
from handlers.states import SetGroupStates, PreferenceStates
from helpers import (
    _get_meaning_of_preferences,
    get_every_aliases_days_week,
    get_formatted_schedule_bell,
)
from decorators import check_existing_user, add_message_id_in_db_for_group
from bookclasses import Links, Homework


@add_message_id_in_db_for_group
async def cmd_start(message: types.Message, **kwargs):
    """Приветствие от бота по команде /start"""
    return await message.answer(
        "Привет! \n"
        "Я бот для расписаний СКФУ! \n"
        "Для начала загрузите расписание с помощью команды /setgroup \n"
        "Подпишитесь на уведомления об начале пары с помощью /notifyme \n"
        "Потом добавьте ссылки, которые будут использоваться при "
        "оповещении, на ВКС-пары, используя интерфейс /links \n"
        "Настройте предпочтения с помощью команды /setpreferences \n"
        "И добавьте домашние задания c помощью /homework \n"
        "Чтобы увидеть все свои настройки воспользуйтесь командой /settings \n"
        "Для просмотра всех команд наберите \n /help \n"
        "<em>P.S. Для корректной работы в группах, следует обращаться "
        "к боту используя reply.</em> \n\n"
        "<b><em>Powered by aiogram</em></b>"
    )


@add_message_id_in_db_for_group
async def cmd_help(message: types.Message, **kwargs):
    """Вывод всех возможных команд бота"""
    state = kwargs["state"]

    await state.finish()
    return await message.answer(
        "<b><em>Список всех команд:</em></b> \n"
        "<em>Команды для настройки бота:</em> \n"
        "/setgroup - Ввод группы для показа расписания \n"
        "/links - Интерфейс для работы со ссылками \n"
        "/homework - Интерфейс для записи домашних заданий \n"
        "/notifyme - Подписаться на уведомления о начале пары \n"
        "/stopnotifyme - Отписаться от уведомлений \n"
        "/setpreferences - Настройка предпочтений по уведомлениям \n\n"
        "<em>Команды для просмотра расписания:</em> \n"
        "/today - Посмотреть расписание на сегодня \n"
        "/tommorow или /tom - Посмотреть расписание на завтра \n"
        "<em>Последующие команды поддерживают наличие префикса "
        "<b>next-</b> для просмотра расписания на следующую неделю</em> \n"
        "/week - Посмотреть расписание на неделю \n"
        "/monday или /mon - Просмотр расписания на понедельник \n"
        "/tuesday или /tue - Просмотр расписания на вторник \n"
        "/wednesday или /wed - Просмотр расписания на среду \n"
        "/thursday или /thu - Просмотр расписания на четверг \n"
        "/friday или /fri - Просмотр расписания на пятницу \n"
        "/saturday или /sat - Просмотр расписания на субботу \n\n"
        "<em>Опциональные команды: </em> \n"
        "/settings - Посмотреть текущие настройки \n"
        "/bell - Посмотреть расписание звонков \n\n"
    )


@check_existing_user
@add_message_id_in_db_for_group
async def cmd_settings(message: types.Message, **kwargs):
    state = kwargs["state"]

    await state.finish()
    db_session = message.bot.get("db")
    async with db_session() as session:
        user: User = await session.get(User, message.chat.id)
        if user.group_id:
            group: Group = await session.get(Group, user.group_id)
            group_name = group.name[0:3].upper() + group.name[3:]
        else:
            group_name = "Группа не определена"

    subgroup = user.subgroup if user.subgroup else "Отсутствует"
    notifications = "Да" if user.is_notified else "Нет"
    pref_time = user.pref_time
    notification_type = _get_meaning_of_preferences()[user.notification_type]
    foreign_lan = user.foreign_lan.capitalize() if user.foreign_lan else "Отсутствует"
    return await message.answer(
        "<em><b>Ваши настройки</b></em>\n"
        f"Название группы: <b>{group_name}</b>\n"
        f"Номер подгруппы: <b>{subgroup}</b>\n"
        f"Иностранный язык: <b>{foreign_lan}</b>\n"
        f"Подписаны на уведомления: <b>{notifications}</b>\n"
        "За сколько минут Вас оповещать: "
        f"<b>{pref_time} мин.</b>\n"
        "Какой тип пар уведомляется: "
        f"<b>{notification_type}</b>\n",
    )


@add_message_id_in_db_for_group
async def cmd_wait_user_group(message: types.Message, **kwargs):
    await SetGroupStates.waiting_for_group_name.set()

    return await message.reply(
        "Введите название группы (в любом регистре) и укажите "
        "номер подгруппы (можно оставить пустым), например:\n"
        "<em>ЭКП-б-о-19-1</em> \n"
        "<em>КГИ-б-о-20-1(1)</em> \n"
        "<em>тбо-б-о-21-1 2</em> \n"
    )


@check_existing_user
@add_message_id_in_db_for_group
async def cmd_show_schedule(message: types.Message, **kwargs):
    regexp_command = kwargs.get("regexp_command")
    week = "cur"
    if regexp_command is not None:
        command = regexp_command.groups()[0]
        if (
            command
            not in main_commands_viewing_schedule + optional_commands_viewing_schedule
        ):
            return
        week = "next"
    else:
        command = re.compile(".(\\w+)").search(message.text).group()[1:]

    db_session = message.bot.get("db")
    async with db_session() as session:
        user: User = await session.get(User, message.chat.id)

    if user.group_id:
        async with db_session() as session:
            sql = select(Group).where(user.group_id == Group.id)
            res = await session.execute(sql)
            group = res.fetchone()[0]
        if group.schedule_cur_week:
            schedule = await get_formatted_schedule(user, group, command, week)
            msg = await message.answer(schedule, parse_mode="HTML")
        else:
            msg = await message.answer("Расписания нет, загрузите командой /setgroup")
    else:
        msg = await message.reply(
            "Похоже что Вы не выбрали группу перед тем как "
            "посмотреть расписание, пожалуйста, воспользуйтесь "
            "командой /setgroup и укажите Вашу группу"
        )
    return msg


@check_existing_user
@add_message_id_in_db_for_group
async def cmd_notify_user(message: types.Message, **kwargs):
    db_session = message.bot.get("db")
    async with db_session() as session:
        user: User = await session.get(User, message.chat.id)
        user.is_notified = True
        await session.commit()

    pref_time = user.pref_time
    pref_type_lesson = _get_meaning_of_preferences()[user.notification_type]
    return await message.reply(
        "Вы успешно подписались на уведомления о начале пары! \n\n"
        f"Время за которое Вас уведомлять о начале пары: <b>{pref_time}</b> мин.\n"
        f"Уведомляемый тип пар: <b>{pref_type_lesson}</b> \n"
        "Для настройки уведомлений воспользуйтесь командой: \n/setpreferences",
    )


@check_existing_user
@add_message_id_in_db_for_group
async def cmd_stop_notify_user(message: types.Message, **kwargs):
    db_session = message.bot.get("db")
    async with db_session() as session:
        user: User = await session.get(User, message.chat.id)
        user.is_notified = False
        await session.commit()
    return await message.reply("Вы отписались от уведомлений о начале пары!")


@add_message_id_in_db_for_group
async def cmd_send_ncfu_bells(message: types.Message, **kwargs):
    return await message.answer(get_formatted_schedule_bell())


@check_existing_user
@add_message_id_in_db_for_group
async def cmd_set_user_preferences(message: types.Message, **kwargs):
    state = kwargs["state"]
    text, markup = show_ikeyboard_preferences()
    await state.finish()
    return await message.answer(
        text,
        reply_markup=markup,
    )


@check_existing_user
@add_message_id_in_db_for_group
async def cmd_show_interface_links(message: types.Message, **kwargs):
    state = kwargs["state"]
    user_book = Links(message.chat.id, message.bot.get("db"))
    text, markup = await user_book.show_page()
    await state.finish()
    return await message.answer(
        text=text,
        reply_markup=markup,
    )


@check_existing_user
@add_message_id_in_db_for_group
async def cmd_show_interface_homework(message: types.Message, **kwargs):
    state = kwargs["state"]
    user_book = Homework(message.chat.id, message.bot.get("db"))
    text, markup = await user_book.show_page()
    await state.finish()
    return await message.answer(
        text=text,
        reply_markup=markup,
    )


async def cmd_clear_bot_messages_from_group(message: types.Message, **kwargs):
    db_session = message.bot.get("db")
    async with db_session() as session:
        stmt = select(Message).join(Chat).filter(Chat.id == message.chat.id)
        messages: List[Message] = await session.scalars(stmt)
        msgs = [msg.id for msg in messages]
        for msg_id in msgs:
            try:
                await message.bot.delete_message(message.chat.id, msg_id)
            except MessageToDeleteNotFound:
                logging.info(f"{msg_id} is already deleted!")

        stmt = delete(Message).where(Message.id.in_(msgs))
        await session.execute(stmt)
        await session.commit()


(
    main_commands_viewing_schedule,
    optional_commands_viewing_schedule,
) = get_every_aliases_days_week()


def register_commands(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands="start")
    dp.register_message_handler(cmd_help, commands="help", state="*")
    dp.register_message_handler(cmd_settings, commands="settings", state="*")
    dp.register_message_handler(cmd_wait_user_group, commands="setgroup", state=None)
    dp.register_message_handler(
        cmd_show_schedule, filters.RegexpCommandsFilter(regexp_commands=["next(.*)"])
    )
    dp.register_message_handler(
        cmd_show_schedule,
        commands=["today", "tomorrow", "tom"] + main_commands_viewing_schedule,
    )
    dp.register_message_handler(cmd_notify_user, commands=["notifyme"])
    dp.register_message_handler(cmd_stop_notify_user, commands=["stopnotifyme"])
    dp.register_message_handler(cmd_send_ncfu_bells, commands=["bell"])
    dp.register_message_handler(cmd_set_user_preferences, commands=["setpreferences"])
    dp.register_message_handler(cmd_show_interface_links, commands=["links"], state="*")
    dp.register_message_handler(
        cmd_show_interface_homework, commands=["homework"], state="*"
    )
    dp.register_message_handler(cmd_clear_bot_messages_from_group, commands=["clear"])
