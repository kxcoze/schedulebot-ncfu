import re
import logging

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import MessageNotModified
from sqlalchemy import select

from db.models import User, Group
from scraping.scraper import get_data_from_getschedule
from helpers import check_existing_user, LANGUAGES
from bookclasses import Links, Homework


class SetGroupStates(StatesGroup):
    waiting_for_group_name = State()


class PreferenceStates(StatesGroup):
    add_time_preference = State()
    add_subgroup_preference = State()
    add_language_preference = State()


class LinksStates(StatesGroup):
    input_data = State()
    edit_data = State()
    del_data = State()


class HomeworkStates(StatesGroup):
    input_data = State()
    input_homework = State()
    edit_data = State()
    edit_homework = State()
    del_data = State()


@check_existing_user
async def state_set_user_group(message: types.Message, **kwargs):
    state = kwargs["state"]

    msg = message.text.split("\n")
    # Регулярное выражение для поиска группы
    regroup = re.compile(r"(.+?)[\s|\(]")
    try:
        group_name = regroup.search(f"{message.text} ").groups()[0].lower().strip()
    except AttributeError:
        await message.reply("Введен неверный формат группы!")
        return

    # Регулярное выражение для поиска подгруппы
    resubgroup = re.compile(".*[\s|(](\d)")
    try:
        # Поиск подгруппы в сообщении пользователя
        group_subnum = resubgroup.search(message.text).groups()[0]
    except AttributeError:
        group_subnum = 0

    db_session = message.bot.get("db")
    async with db_session() as session:
        res = (
            await session.execute(select(Group).where(Group.name == group_name))
        ).fetchone()
        if res:
            group: Group = res[0]
        else:
            group = None

    if group:
        answer_success = await message.answer(
            "Группа найдена, пробуем загрузить Ваше расписание..."
        )
        await state.finish()
        try:
            async with db_session() as session:
                if group.schedule_cur_week is None or group.schedule_next_week is None:
                    logging.info(f"loading schedule for {group.name} group")
                    (
                        group.schedule_cur_week,
                        group.schedule_next_week,
                    ) = await get_data_from_getschedule(group.id)
                    async with session.begin():
                        session.add(group)
                    await session.commit()
                    logging.info(f"loaded schedule for {group.name} group")

                user: User = await session.get(User, message.chat.id)
                user.group_id = group.id
                user.subgroup = int(group_subnum)
                await session.commit()

                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=answer_success.message_id,
                    text="Расписание на неделю загружено!\n"
                    "Вы можете просмотреть его используя команду /week",
                )
        except:
            logging.exception(
                "Something wents wrong with updating user schedule"
                f"ID:[{message.chat.id}] request"
            )
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=answer_success.message_id,
                text="Произошла непредвиденная ошибка!\n"
                "Пожалуйста, попробуйте позже.",
            )
    else:
        await message.reply("Введенная группа не существует, попробуйте снова")


@check_existing_user
async def state_set_time_preferences(message: types.Message, **kwargs):
    state = kwargs["state"]
    if message.text.isdigit() and 0 <= int(message.text) <= 60:
        db_session = message.bot.get("db")
        async with db_session() as session:
            user: User = await session.get(User, message.chat.id)
            user.pref_time = int(message.text)
            await session.commit()
        await message.answer(
            "Время успешно установлено!\n"
            "Текущие настройки можно посмотреть с помощью команды /settings"
        )
        await state.finish()
    else:
        await message.answer("Вы ввели не подходящее число!")


@check_existing_user
async def state_set_user_subgroup_preferences(message: types.Message, **kwargs):
    state = kwargs["state"]
    if message.text.isdigit() and 0 <= int(message.text) <= 9:
        db_session = message.bot.get("db")
        async with db_session() as session:
            user: User = await session.get(User, message.chat.id)
            user.subgroup = int(message.text)
            await session.commit()
        await message.answer(
            "Подгруппа успешно установлена!\n"
            "Текущие настройки можно посмотреть с помощью команды /settings"
        )
        await state.finish()
    else:
        await message.answer("Вы ввели не подходящее число!")


@check_existing_user
async def state_set_user_language_preferences(message: types.Message, **kwargs):
    state = kwargs["state"]
    # Добавить обработку отсутствия пользователя в БД
    msg = message.text.split()[0]
    if not msg.isalpha() and msg != "-":
        await message.answer("Вы ввели не строку! Попробуйте ещё раз.")
        return
    elif len(msg) > 30:
        await message.answer("Такое кол-во символов недопустимо! Попробуйте ещё раз.")
        return
    elif msg.capitalize() not in LANGUAGES:
        await message.answer("Данный язык отсутствует. Введите другой язык")
        return
    elif msg == "-":
        msg = ""

    db_session = message.bot.get("db")
    async with db_session() as session:
        user: User = await session.get(User, message.chat.id)
        user.foreign_lan = msg.capitalize()
        await session.commit()

    await message.answer(
        "Язык успешно установлен!\n"
        "Текущие настройки можно посмотреть с помощью команды /settings"
    )
    await state.finish()


async def state_process_user_message_link(message: types.Message, state: FSMContext):
    message_text = message.text.split("\n")
    searched_data = []
    for text in message_text:
        if len(searched_data) >= 2:
            break
        if text != "":
            searched_data.append(text)

    if len(searched_data) < 2:
        await message.bot.send_message(
            text="Введенных данных недостаточно для добавления ссылки!",
            chat_id=message.chat.id,
        )
        return

    async with state.proxy() as data:
        user_book = Links(message.chat.id, message.bot.get("db"))
        cur_page = data["page_num"]
        result = await user_book.append_data(*searched_data, cur_page * user_book.WIDTH)
        if result == 0:
            await message.bot.send_message(
                text="Ссылка успешно добавлена!",
                chat_id=message.chat.id,
                reply_markup=user_book.back_to_main(cur_page, "links"),
            )
            text, markup = await user_book.show_page(cur_page)
            try:
                await message.bot.edit_message_text(
                    text=text,
                    chat_id=message.chat.id,
                    message_id=data["main"],
                    reply_markup=markup,
                )
            except MessageNotModified:
                # Информация на странице не изменилась
                pass
            await state.finish()
        elif result == -1:
            await message.bot.send_message(
                text=(
                    "Ваших ссылок стало слишком много, "
                    "удалите лишние с помощью кнопки "
                    "<b>Удалить ссылку</b>"
                ),
                chat_id=message.chat.id,
            )
            await state.finish()
        else:
            await message.bot.send_message(
                text="Что-то пошло не так, попробуйте снова!", chat_id=message.chat.id
            )


async def state_edit_link(message: types.Message, state: FSMContext):
    message_text = message.text.split("\n")[0]
    user_book = Links(message.chat.id, message.bot.get("db"))
    async with state.proxy() as data:
        cur_page = data["page_num"]
        ind = data["ind"]
        variant = data["var"]
        if variant == "1":
            await user_book.update_data_element_first_pos(message_text, ind)
        elif variant == "2":
            await user_book.update_data_element_second_pos(message_text, ind)
        text, markup = await user_book.view_data_element(cur_page, ind)
        try:
            await message.bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=data["main"],
                reply_markup=markup,
            )
        except MessageNotModified:
            # Информация в ссылке не изменилась
            pass
        await state.finish()


async def state_process_user_message_homework(
    message: types.Message, state: FSMContext
):
    message_text = message.text.split("\n")
    searched_data = []
    for text in message_text[:6]:
        if text != "":
            searched_data.append(text)

    if not searched_data:
        await message.bot.send_message(
            text="Введенных данных недостаточно для добавления домашки!",
            chat_id=message.chat.id,
        )
        return

    async with state.proxy() as data:
        cur_page = data["page_num"]
        message_id = data["main"]
        name = data["name"]

    user_book = Homework(message.chat.id, message.bot.get("db"))
    result = await user_book.append_data(
        subject=searched_data[0],
        homework=searched_data[1:],
        pos=cur_page * user_book.WIDTH,
    )
    if result == 0:
        await message.bot.send_message(
            text="Предмет успешно добавлен!",
            chat_id=message.chat.id,
            reply_markup=user_book.back_to_main(cur_page, "homework"),
        )
        text, markup = await user_book.show_page(cur_page)
        try:
            await message.bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=message_id,
                reply_markup=markup,
            )
        except MessageNotModified:
            # Информация на странице не изменилась
            pass
        await state.finish()
    elif result == -1:
        await message.bot.send_message(
            text=(
                "Ваших предметов стало слишком много,"
                "удалите лишние с помощью кнопки "
                "<b>Удалить предмет</b>"
            ),
            chat_id=message.chat.id,
        )
        await state.finish()
    else:
        await message.bot.send_message(
            text="Что-то пошло не так, попробуйте снова!", chat_id=message.chat.id
        )


async def state_process_user_homework_detail_info(
    message: types.Message, state: FSMContext
):
    message_text = message.text.split("\n")[0]

    async with state.proxy() as data:
        ind = data["ind"]
        cur_page = data["page_num"]
        message_id = data["main"]
        name = data["name"]
    user_book = Homework(message.chat.id, message.bot.get("db"))
    result = await user_book.append_data(
        homework=message_text,
        ind=ind,
    )
    if result == 0:
        await message.bot.send_message(
            text="Домашка успешно добавлена!",
            chat_id=message.chat.id,
        )
        text, markup = await user_book.view_data_element(cur_page, ind)
        try:
            await message.bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=message_id,
                reply_markup=markup,
            )
        except MessageNotModified:
            # Информация на странице не изменилась
            pass
        await state.finish()
    elif result == -1:
        await message.bot.send_message(
            text=(
                "Ваших домашек стало слишком много, "
                "удалите лишние с помощью кнопки "
                "<b>Удалить домашку</b>"
            ),
            chat_id=message.chat.id,
            parse_mode="HTML",
        )
        await state.finish()
    else:
        await message.bot.send_message(
            text="Что-то пошло не так, попробуйте снова!", chat_id=message.chat.id
        )


async def state_edit_homework(message: types.Message, state: FSMContext):
    message_text = message.text.split("\n")[0]
    user_book = Homework(message.chat.id, message.bot.get("db"))
    async with state.proxy() as data:
        cur_page = data["page_num"]
        ind = data["ind"]
        variant = data["var"]
        message_id = data["main"]
    if variant == "1":
        await user_book.update_data_element_first_pos(message_text, ind)
    text, markup = await user_book.view_data_element(cur_page, ind)
    try:
        await message.bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=markup,
        )
    except MessageNotModified:
        # Информация в домашке не изменилась
        pass
    await state.finish()


async def state_edit_homework_detail_info(message: types.Message, state: FSMContext):
    message_text = message.text.split("\n")[0]
    user_book = Homework(message.chat.id, message.bot.get("db"))
    async with state.proxy() as data:
        message_id = data["main"]
        ind_sub = data["ind_sub"]
        ind_hmw = data["ind_hmw"]
    await user_book.update_data_element_second_pos(message_text, ind_sub, ind_hmw)
    text, markup = await user_book.view2_data_element(ind_sub, ind_hmw)
    try:
        await message.bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=markup,
        )
    except MessageNotModified:
        # Информация в домашке не изменилась
        pass
    await state.finish()


def register_states(dp: Dispatcher):
    dp.register_message_handler(
        state_set_user_group, state=SetGroupStates.waiting_for_group_name
    )
    dp.register_message_handler(
        state_set_time_preferences, state=PreferenceStates.add_time_preference
    )
    dp.register_message_handler(
        state_set_user_subgroup_preferences,
        state=PreferenceStates.add_subgroup_preference,
    )
    dp.register_message_handler(
        state_set_user_language_preferences,
        state=PreferenceStates.add_language_preference,
    )
    dp.register_message_handler(
        state_process_user_message_link, state=LinksStates.input_data
    )
    dp.register_message_handler(state_edit_link, state=LinksStates.edit_data)
    dp.register_message_handler(
        state_process_user_message_homework, state=HomeworkStates.input_data
    )
    dp.register_message_handler(
        state_process_user_homework_detail_info, state=HomeworkStates.input_homework
    )
    dp.register_message_handler(
        state_edit_homework_detail_info, state=HomeworkStates.edit_homework
    )
    dp.register_message_handler(state_edit_homework, state=HomeworkStates.edit_data)
