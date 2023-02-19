import typing
import logging
from contextlib import suppress

from aiogram import types, Dispatcher
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher import FSMContext, filters
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from inlinekeyboard import (
    show_ikeyboard_preferences,
    show_type_preference_ikeyboard,
    cbd_poll,
    cbd_choice,
)
from decorators import add_message_id_in_db_for_group
from handlers.states import PreferenceStates, LinksStates, HomeworkStates
from bookclasses import Book, Links, Homework


async def query_set_user_preferences(
    query: types.CallbackQuery, state: FSMContext, **kwargs
):
    await query.answer()
    await state.finish()
    text, markup = show_ikeyboard_preferences()
    await query.bot.edit_message_text(
        text=text,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=markup,
    )


@add_message_id_in_db_for_group
async def query_wait_user_time_preferences(
    query: types.CallbackQuery, state: FSMContext, **kwargs
):
    answer = (
        "Укажите за сколько минут Вас уведомлять о начале пары \n"
        "(от 0 до 60 минут)\n"
    )
    await query.answer()
    await PreferenceStates.add_time_preference.set()

    return await query.bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


async def query_wait_user_type_preferences(query: types.CallbackQuery, **kwargs):
    await query.answer()
    text, markup = show_type_preference_ikeyboard()
    await query.bot.edit_message_text(
        text=text,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=markup,
    )


async def query_set_user_type_preferences(
    query: types.CallbackQuery, callback_data: typing.Dict[str, str], **kwargs
):
    db_session = query.bot.get("db")
    async with db_session() as session:
        user: User = await session.get(User, query.message.chat.id)
        user.notification_type = callback_data["result"]
        await session.commit()
    await query.answer("Успешно!")


@add_message_id_in_db_for_group
async def query_wait_user_subgroup_preferences(
    query: types.CallbackQuery, state: FSMContext, **kwargs
):
    await query.answer()
    answer = "Укажите Вашу подгруппу от (0 до 9)\n"
    await PreferenceStates.add_subgroup_preference.set()
    return await query.bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


@add_message_id_in_db_for_group
async def query_wait_user_language_preferences(
    query: types.CallbackQuery, state: FSMContext, **kwargs
):
    answer = (
        "Напишите язык, который Вам преподается на паре типа:\n"
        "<b>Иностранный язык в профессиональной сфере (ваш язык)</b>\n\n"
        "Например можно указать (в любом регистре):\n"
        "<b><em>Английский</em></b> или <b><em>Русский</em></b>\n"
        "Если желаете убрать язык напишите одиночное тире: <b><em>-</em></b>"
    )
    await query.answer()
    await PreferenceStates.add_language_preference.set()

    return await query.bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


async def query_show_book_prev_next_page(
    query: types.CallbackQuery, callback_data: typing.Dict[str, str], **kwargs
):
    cur_page = int(callback_data["page_num"])
    if callback_data["name"] == "homework":
        pass
        user_book = Homework(query.message.chat.id, query.bot.get("db"))
    else:
        user_book = Links(query.message.chat.id, query.bot.get("db"))
    text, markup = await user_book.show_page(cur_page)
    await query.message.edit_text(
        text=text,
        reply_markup=markup,
    )
    await query.answer()


async def query_show_link_info(
    query: types.CallbackQuery, callback_data: typing.Dict[str, str], **kwargs
):
    cur_page = int(callback_data["page_num"])
    ind = int(callback_data["id"]) - 1
    user_book = Links(query.message.chat.id, query.bot.get("db"))
    data_element = user_book.parse_msg(query.message.text)[ind % user_book.WIDTH][1:]
    new_ind = await user_book.check_existing_data(data_element, ind)

    if new_ind == -1:
        await query.answer("Такого номера не существует!")
        text, markup = await user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return
    elif new_ind != ind:
        ind = new_ind
        cur_page = ind // user_book.WIDTH

    try:
        text, markup = await user_book.view_data_element(cur_page, ind)
        with suppress(MessageNotModified):
            await query.message.edit_text(text, reply_markup=markup)
        await query.answer()
    except:
        logging.exception(
            "Something went wrong with showing link"
            f"user ID:[{query.message.chat.id}]"
        )
        await query.answer("Произошла непредвиденная ошибка.")


@add_message_id_in_db_for_group
async def query_add_data(
    query: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext,
    **kwargs,
):
    async with state.proxy() as data:
        data["main"] = query.message.message_id
        data["page_num"] = int(callback_data["page_num"])
        data["name"] = callback_data["name"]

    if callback_data["name"] == "homework":
        answer = (
            "Для добавления домашнего задания, укажите название предмета, "
            "далее на следующих строчках Ваше Д/З (до 5-ти строчек)\n"
            "Например: \n"
            "<b>БЖД \n"
            "Подготовить первую практику на некст пару \n"
            "Сделать 1, 2 лабы \n"
            "Выучить термины. \n"
            "*Возможная домашка №4* \n"
            "*Возможная домашка №5* \n"
            "</b>"
        )
        await HomeworkStates.input_data.set()
    else:
        answer = (
            "Для добавления ссылки на пару, укажите "
            "преподавателя/предмет (в точности как в расписании), "
            "который желаете добавить и на следующей строке "
            "ссылку на занятие (BBB, zoom и т.п.)\n"
            "Например: \n"
            "<b>Иностранный язык в профессиональной сфере "
            "(английский язык)\n"
            "'Ссылка на занятие'</b>\n"
            "или\n"
            "<b>Иванов Иван Иванович\n"
            "'Cсылка на занятие'</b>"
        )
        await LinksStates.input_data.set()
    await query.answer()

    return await query.bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


@add_message_id_in_db_for_group
async def query_edit_data(
    query: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext,
    **kwargs,
):

    if callback_data["name"] == "homework":
        user_book = Homework(query.message.chat.id, query.bot.get("db"))
        additional = ""
        await HomeworkStates.edit_data.set()
    else:
        user_book = Links(query.message.chat.id, query.bot.get("db"))
        additional = "/преподавателя"
        await LinksStates.edit_data.set()
    data = user_book.parse_msg(query.message.text)[0]
    ind = int(data[0]) - 1
    page_data = data[1:]
    cur_page = int(callback_data["page_num"])
    res = await user_book.check_existing_data(page_data, ind)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие" "/измененные данные!")
        text, markup = await user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        await state.finish()
        return

    variant = callback_data["id"]
    answer = "Введите "
    if variant == "1":
        additional = f"новый предмет{additional}"
    elif variant == "2":
        additional = "новую ссылку"
    else:
        additional = "новую информацию"
    answer += additional
    await query.answer(answer)

    async with state.proxy() as data:
        data["main"] = query.message.message_id
        data["page_num"] = cur_page
        data["var"] = variant
        data["ind"] = ind

    return await query.bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


async def query_delete_data(
    query: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext,
    **kwargs,
):
    await state.finish()
    if callback_data["name"] == "homework":
        user_book = Homework(query.message.chat.id, query.tbot.get("db"))
        information = "Предмет"
        data_element = user_book.parse_msg(query.message.text)[0][1:]
    else:
        user_book = Links(query.message.chat.id, query.bot.get("db"))
        information = "Ссылка"
        data_element = user_book.parse_msg(query.message.text)[0][1:]
    try:
        result = await user_book.delete_data_element_by_info(data_element)
        if result == 0:
            await query.answer(f"Данные успешно удалены!")
        elif result == -1:
            await query.answer(f"{information} отсутствует.")
    except:
        logging.exception(
            "Something went wrong with deleting link"
            f"user ID:[{query.message.chat.id}]"
        )
        await query.answer("Произошла непредвиденная ошибка.")

    cur_page = int(callback_data["page_num"])
    text, markup = await user_book.show_page(cur_page)
    await query.message.edit_text(
        text=text,
        reply_markup=markup,
    )


async def query_show_homework_info(
    query: types.CallbackQuery, callback_data: typing.Dict[str, str], **kwargs
):
    cur_page = int(callback_data["page_num"])
    ind = int(callback_data["id"]) - 1
    user_book = Homework(query.message.chat.id, query.bot.get("db"))
    data_element = user_book.parse_msg(query.message.text)
    try:
        data_element = data_element[ind % user_book.WIDTH][1:]
    except IndexError:
        data_element = data_element[0][1:]
    finally:
        new_ind = await user_book.check_existing_data(data_element, ind)

    if new_ind == -1:
        await query.answer("Такого номера не существует!")
        text, markup = await user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return
    elif new_ind != ind:
        ind = new_ind
        cur_page = ind // user_book.WIDTH

    try:
        text, markup = await user_book.view_data_element(cur_page, ind)
        with suppress(MessageNotModified):
            await query.message.edit_text(text, reply_markup=markup)
        await query.answer()
    except:
        logging.exception(
            "Something went wrong with showing link"
            f"user ID:[{query.message.chat.id}]"
        )
        await query.answer("Произошла непредвиденная ошибка.")


async def query_show_homework_detail_info(
    query: types.CallbackQuery, callback_data: typing.Dict[str, str], **kwargs
):
    ind_sub = int(callback_data["page_num"])
    ind_hmw = int(callback_data["id"]) - 1
    user_book = Homework(query.message.chat.id, query.bot.get("db"))
    page_data = user_book.parse_msg(query.message.text)[0][1:]
    new_ind = await user_book.check_existing_data(page_data, ind_sub)
    if new_ind == -1:
        await query.answer("Такого номера не существует!")
        text, markup = await user_book.show_page()
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return

    ind_sub = new_ind
    cur_page = ind_sub // user_book.WIDTH
    user_pages = (await user_book.pages)[ind_sub][1]
    if len(user_pages) - 1 < ind_hmw or user_pages[ind_hmw] != page_data[1][ind_hmw]:
        ind_hmw = user_pages.index(page_data[1][ind_hmw])
    try:
        text, markup = await user_book.view2_data_element(ind_sub, ind_hmw)
        with suppress(MessageNotModified):
            await query.message.edit_text(text, reply_markup=markup)
        await query.answer()
    except:
        logging.exception(
            "Something went wrong with showing link"
            f"user ID:[{query.message.chat.id}]"
        )
        await query.answer("Произошла непредвиденная ошибка.")


@add_message_id_in_db_for_group
async def query_additional_data(
    query: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext,
    **kwargs,
):
    user_book = Homework(query.message.chat.id, query.bot.get("db"))
    data = user_book.parse_msg(query.message.text)[0]
    ind = int(data[0]) - 1
    page_data = data[1:]
    cur_page = int(callback_data["page_num"])
    res = await user_book.check_existing_data(page_data, ind)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие" "/измененные данные!")
        text, markup = await user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        await state.finish()
        return
    elif (await user_book.pages)[res] != page_data:
        text, markup = await user_book.view_data_element(cur_page, ind)
        try:
            await query.bot.edit_message_text(
                text=text,
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                reply_markup=markup,
            )
        except MessageNotModified:
            # Информация в домашке не изменилась
            pass

    await query.answer()
    async with state.proxy() as data:
        data["main"] = query.message.message_id
        data["page_num"] = int(callback_data["page_num"])
        data["ind"] = int(callback_data["id"])
        data["name"] = callback_data["name"]

    answer = "Введите данные для добавления новой домашки"
    await HomeworkStates.input_homework.set()

    return await query.bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


@add_message_id_in_db_for_group
async def query_edit_detail_info(
    query: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext,
    **kwargs,
):

    user_book = Homework(query.message.chat.id, query.bot.get("db"))
    data = user_book.parse_msg(query.message.text)[0]
    page_data = data[1:]
    res = await user_book.check_existing_data(page_data, int(data[0]) - 1)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие" "/измененные данные!")
        text, markup = await user_book.show_page()
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        await state.finish()
        return
    ind_sub = res
    ind_hmw = int(callback_data["page_num"]) - 1
    user_pages = await user_book.pages
    user_pages = user_pages[ind_sub][1]
    if len(user_pages) - 1 < ind_hmw or user_pages[ind_hmw] != page_data[1][0]:
        ind_hmw = user_pages.index(page_data[1][0])
        text, markup = await user_book.view2_data_element(ind_sub, ind_hmw)
        try:
            await query.bot.edit_message_text(
                text=text,
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                reply_markup=markup,
            )
        except MessageNotModified:
            # Информация в домашке не изменилась
            pass

    await query.answer()
    async with state.proxy() as data:
        data["main"] = query.message.message_id
        data["ind_sub"] = ind_sub
        data["ind_hmw"] = ind_hmw

    answer = "Введите новые данные для домашки"
    await HomeworkStates.edit_homework.set()

    return await query.bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
        parse_mode="HTML",
    )


async def query_delete_homework(
    query: types.CallbackQuery,
    callback_data: typing.Dict[str, str],
    state: FSMContext,
    **kwargs,
):
    await state.finish()

    user_book = Homework(query.message.chat.id, query.bot.get("db"))
    data = user_book.parse_msg(query.message.text)[0]
    page_data = data[1:]
    res = await user_book.check_existing_data(page_data, int(data[0]) - 1)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие" "/измененные данные!")
        text, markup = await user_book.show_page()
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        await state.finish()
        return
    ind_sub = res
    ind_hmw = int(callback_data["page_num"]) - 1
    cur_page = ind_sub + 1 // user_book.WIDTH
    user_pages = (await user_book.pages)[ind_sub][1]

    if len(user_pages) - 1 < ind_hmw or user_pages[ind_hmw] != page_data[1][0]:
        ind_hmw = user_pages.index(page_data[1][0])
    information = "Домашка"
    result = await user_book.delete_homework_by_ind(ind_sub, ind_hmw)
    if result == 0:
        await query.answer(f"Данные успешно удалены!")
    elif result == -1:
        await query.answer(f"{information} отсутствует.")
    try:
        pass
    except:
        logging.exception(
            "Something went wrong with deleting link"
            f"user ID:[{query.message.chat.id}]"
        )
        await query.answer("Произошла непредвиденная ошибка.")

    text, markup = await user_book.view_data_element(cur_page, ind_sub)
    try:
        await query.bot.edit_message_text(
            text=text,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            reply_markup=markup,
        )
    except MessageNotModified:
        # Информация в домашке не изменилась
        pass


def register_callbacks(dp: Dispatcher):
    dp.register_callback_query_handler(
        query_set_user_preferences, cbd_poll.filter(id="0"), state="*"
    )
    dp.register_callback_query_handler(
        query_wait_user_time_preferences, cbd_poll.filter(id="1"), state="*"
    )
    dp.register_callback_query_handler(
        query_wait_user_type_preferences, cbd_poll.filter(id="2"), state="*"
    )
    dp.register_callback_query_handler(
        query_set_user_type_preferences, cbd_choice.filter(action="choose"), state="*"
    )
    dp.register_callback_query_handler(
        query_wait_user_subgroup_preferences, cbd_poll.filter(id="3"), state="*"
    )
    dp.register_callback_query_handler(
        query_wait_user_language_preferences, cbd_poll.filter(id="4"), state="*"
    )
    dp.register_callback_query_handler(
        query_show_book_prev_next_page,
        Book.list.filter(action=["main", "prev", "next"]),
        state="*",
    )
    dp.register_callback_query_handler(
        query_show_link_info, Book.list.filter(action="view", name="links"), state="*"
    )
    dp.register_callback_query_handler(query_add_data, Book.list.filter(action="add"))
    dp.register_callback_query_handler(
        query_edit_data, Book.list.filter(action="edit"), state="*"
    )
    dp.register_callback_query_handler(
        query_delete_data, Book.list.filter(action="delete"), state="*"
    )
    dp.register_callback_query_handler(
        query_show_homework_info,
        Book.list.filter(action="view", name="homework"),
        state="*",
    )
    dp.register_callback_query_handler(
        query_show_homework_detail_info,
        Book.list.filter(action="view2", name="homework"),
        state="*",
    )
    dp.register_callback_query_handler(
        query_additional_data, Book.list.filter(action="add2")
    )
    dp.register_callback_query_handler(
        query_edit_detail_info, Book.list.filter(action="edit2", name="homework")
    )
    dp.register_callback_query_handler(
        query_delete_homework,
        Book.list.filter(action="delete2", name="homework"),
        state="*",
    )
