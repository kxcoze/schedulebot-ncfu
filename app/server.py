import os
import logging
import logging.config
import asyncio
import typing
import json
import re
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext, filters
from aiogram.utils.exceptions import MessageNotModified

import db
import schedulecreator as SC
import taskmanager as tasks
import linkmanager as lm
import inlinekeyboard as ik
from settings import logging_dict

API_TOKEN = os.getenv('API_TOKEN')

main_commands_viewing_schedule, optional_commands_viewing_schedule = \
    SC.get_every_aliases_days_week()

ex = ThreadPoolExecutor(max_workers=2)

logging.config.dictConfig(logging_dict)
log = logging.getLogger('app_logger')

bot = Bot(token=API_TOKEN)

# Возможно стоит изменить storage
dp = Dispatcher(bot, storage=MemoryStorage())


class MainStates(StatesGroup):
    waiting_for_group_name = State()
    add_time_preference = State()
    add_subgroup_preference = State()
    add_language_preference = State()


class LinkStates(StatesGroup):
    input_link = State()
    edit_link = State()
    del_link = State()


@dp.message_handler(commands=['start'])
async def initializebot(message: types.Message):
    """Добавить клавиатуру"""
    """Приветствие от бота по команде /start"""
    await message.answer(
            "Привет! \n"
            "Я бот для расписаний СКФУ! \n"
            "Для просмотра всех команд наберите /help \n\n"
            "<em>Powered by aiogram</em>",
            parse_mode='HTML',
    )


@dp.message_handler(commands=['help'], state='*')
async def send_help_commands(message: types.Message, state: FSMContext):
    """Вывод всех возможных команд бота"""
    await state.finish()
    await message.answer(
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
            "/bell - Посмотреть расписание звонков \n\n",
            parse_mode='HTML',
    )


@dp.message_handler(commands=['settings'], state='*')
async def show_user_settings(message: types.Message, state: FSMContext):
    await state.finish()
    # Добавить обработку отсутствия пользователя в БД
    db.check_user(message.chat.id)

    data_dict = db.fetchall(
        'users',
        ('group_code', 'subgroup', 'notifications', 'preferences'),
        f"WHERE user_id={message.chat.id}"
    )[0]
    group_name = db.get(
        'univer_code', 'group_name', 'group_code', f"{data_dict['group_code']}"
    )
    if not group_name == -1:
        group_code = group_name[0:3].upper() + group_name[3:]
    else:
        group_code = 'Группа не определена'

    subgroup = data_dict['subgroup'].replace('0', 'Отсутствует')
    notifications = "Да" if data_dict['notifications'] == 1 else "Нет"
    meaning = SC._get_meaning_of_preferences()
    preferences = json.loads(data_dict['preferences'])
    if preferences['foreign_lan'] == '':
        foreign_lan = 'Отсутствует'
    else:
        foreign_lan = preferences['foreign_lan'].capitalize()
    await message.answer(
        "<em><b>Ваши настройки</b></em>\n"
        f"Название группы: <b>{group_code}</b>\n"
        f"Номер подгруппы: <b>{subgroup}</b>\n"
        f"Иностранный язык: <b>{foreign_lan}</b>\n"
        f"Подписаны на уведомления: <b>{notifications}</b>\n"
        "За сколько минут Вас оповещать: "
        f"<b>{preferences['pref_time']} мин.</b>\n"
        "Какой тип пар уведомляется: "
        f"<b>{meaning[preferences['notification_type']]}</b>\n",
        parse_mode='HTML'
    )


@dp.message_handler(commands=['setgroup'], state=None)
async def set_user_group(message: types.Message):
    await message.reply(
            "Введите название группы (в любом регистре) и укажите "
            "номер подгруппы (можно оставить пустым), например:\n"
            "<em>ЭКП-б-о-19-1</em> \n"
            "<em>КГИ-б-о-18-1(1)</em> \n"
            "<em>тбо-б-о-19-1 2</em> \n",
            parse_mode='HTML',
    )

    await MainStates.waiting_for_group_name.set()


@dp.message_handler(state=MainStates.waiting_for_group_name)
async def wait_for_group_name(message: types.Message, state: FSMContext):
    msg = message.text.split('\n')
    # Регулярное выражение для поиска группы
    regroup = re.compile(
        '(([а-яА-я]-[а-яА-Я]{3}|[а-яА-Я]{3})-[а-я]+?-[а-я]+?-\\d{1,3}'
        '(-[0-9а-яА-Я.]+|-\\d|))|([а-яА-я]-[а-яА-Я]{1,3}-\\d+)')

    # Регулярное выражение для поиска подгруппы
    resubgroup = re.compile('[^-\\d]([0-9]{1})([^-\\d]|\\Z)')

    try:
        group_name = regroup.search(message.text).group().lower()
    except AttributeError:
        await message.reply("Введен неверный формат группы!")
        return

    try:
        # Поиск подгруппы в сообщении пользователя
        group_subnum = resubgroup.search(message.text).groups()[0]
    except AttributeError:
        group_subnum = 0

    group_code = db.get('univer_code', 'group_code', 'group_name', group_name)
    # Возможно есть реализация получше! Может быть перенести в другой скрипт?
    if not group_code == -1:
        answer_success = await message.answer("Группа найдена, пробуем загрузить Ваше расписание...")
        try:
            await asyncio.get_running_loop().run_in_executor(
                ex, SC.update_schedule_user,
                message.chat.id, group_code, group_subnum
            )
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=answer_success.message_id,
                text="Расписание на неделю загружено!\n"
                     "Вы можете просмотреть его используя команду /week"
            )
        except:
            log.exception('Something wents wrong with updating user schedule'
                          f'ID:[{message.chat.id}] request')
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=answer_success.message_id,
                text="Произошла непредвиденная ошибка!\n"
                     "Пожалуйста, попробуйте позже.")
        finally:
            await state.finish()
    else:
        await message.reply("Введенная группа не существует, попробуйте снова")


@dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=['next(.*)']))
@dp.message_handler(commands=['today', 'tommorow', 'tom']+main_commands_viewing_schedule)
async def show_user_schedule_cur_week(message: types.Message, regexp_command=None):
    week = 'cur'
    if regexp_command is not None:
        command = regexp_command.groups()[0]
        if command not in main_commands_viewing_schedule + optional_commands_viewing_schedule:
            return
        week = 'next'
    else:
        command = re.compile('.(\\w+)').search(message.text).group()[1:]

    group_code = db.get('users', 'group_code', 'user_id', message.chat.id)
    if not group_code == -1:
        schedule = SC.get_formatted_schedule(message.chat.id, command, week)
        await message.answer(schedule, parse_mode='HTML')
    else:
        await message.reply(
            "Похоже что Вы не выбрали группу перед тем как "
            "посмотреть расписание, пожалуйста, воспользуйтесь "
            "командой /setgroup и укажите Вашу группу")


@dp.message_handler(commands=['notifyme'])
async def set_user_notification(message: types.Message):
    db.check_user(message.chat.id)

    db.update('users', (('notifications', 1), ), 'user_id', message.chat.id)
    pref_time = json.loads(db.get(
        'users', 'preferences', 'user_id', message.chat.id))['pref_time']
    await message.reply(
        "Вы успешно подписались на уведомления о начале пары!\n\n"
        f"Время за которое Вас уведомлять о начале пары: {pref_time} мин.\n"
        "Желаете ли определить время за которое Вас оповещать?\n"
        "Если да, нажмите/введите /setpreferences"
    )


@dp.message_handler(commands=['stopnotifyme'])
async def stop_user_notification(message: types.Message):
    # Добавить обработку отсутствия пользователя в БД
    db.check_user(message.chat.id)

    db.update('users', (('notifications', 0), ), 'user_id', message.chat.id)
    await message.reply("Вы отписались от уведомлений о начале пары!")


@dp.message_handler(commands=['bell'])
async def print_commands(message: types.Message):
    await message.answer(SC.get_formatted_schedule_bell(), parse_mode='HTML')


@dp.message_handler(commands=['setpreferences'])
async def command_set_user_preferences(message: types.Message, state: FSMContext):
    await state.finish()
    text, markup = ik.show_optional_ikeyboard()
    await message.answer(
        text,
        reply_markup=markup,
        parse_mode='HTML',
    )


@dp.callback_query_handler(ik.cbd_poll.filter(id='0'), state='*')
async def query_set_user_preferences(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    await state.finish()
    text, markup = ik.show_optional_ikeyboard()
    await bot.edit_message_text(
        text=text,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


@dp.callback_query_handler(ik.cbd_poll.filter(id='1'), state='*')
async def wait_user_time_preferences(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    answer = (
        "Укажите за сколько минут Вас уведомлять о начале пары \n"
        "(от 0 до 60 минут)\n"
    )
    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
        parse_mode='HTML',
    )

    await MainStates.add_time_preference.set()


@dp.message_handler(state=MainStates.add_time_preference)
async def set_user_time_preferences(message: types.Message, state: FSMContext):
    if message.text.isdigit() and 0 <= int(message.text) <= 60:
        # Добавить обработку отсутствия пользователя в БД
        db.check_user(message.chat.id)

        preferences = json.loads(
            db.get('users', 'preferences', 'user_id', message.chat.id))
        preferences['pref_time'] = message.text
        db.update(
            'users',
            (('preferences', json.dumps(preferences, ensure_ascii=False)), ),
            'user_id', message.chat.id
        )
        await message.answer(
            "Время успешно установлено!\n"
            "Текущие настройки можно посмотреть с помощью команды /settings"
        )
        await state.finish()
    else:
        await message.answer("Вы ввели не подходящее число!")


@dp.callback_query_handler(ik.cbd_poll.filter(id='2'), state='*')
async def wait_user_type_preferences(query: types.CallbackQuery):
    await query.answer()
    text, markup = ik.show_type_preference_ikeyboard()
    await bot.edit_message_text(
        text=text,
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


@dp.callback_query_handler(ik.cbd_choice.filter(action='choose'), state='*')
async def set_user_type_preferences(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    await query.answer('Успешно!')
    # Добавить обработку отсутствия пользователя в БД
    db.check_user(query.message.chat.id)

    preferences = json.loads(
        db.get('users', 'preferences', 'user_id', query.message.chat.id))
    preferences['notification_type'] = callback_data['result']
    db.update(
        'users',
        (('preferences', json.dumps(preferences, ensure_ascii=False)), ),
        'user_id', query.message.chat.id
    )


@dp.callback_query_handler(ik.cbd_poll.filter(id='3'), state='*')
async def wait_user_subgroup_preferences(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    answer = (
        "Укажите Вашу подгруппу от (0 до 9)\n"
    )
    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
        parse_mode='HTML',
    )

    await MainStates.add_subgroup_preference.set()


@dp.message_handler(state=MainStates.add_subgroup_preference)
async def set_user_subgroup_preferences(message: types.Message, state: FSMContext):
    if message.text.isdigit() and 0 <= int(message.text) <= 9:
        # Добавить обработку отсутствия пользователя в БД
        db.check_user(message.chat.id)

        db.update(
            'users',
            (('subgroup', message.text), ),
            'user_id', message.chat.id
        )
        await message.answer(
            "Подгруппа успешно установлена!\n"
            "Текущие настройки можно посмотреть с помощью команды /settings"
        )
        await state.finish()
    else:
        await message.answer("Вы ввели не подходящее число!")


@dp.callback_query_handler(ik.cbd_poll.filter(id='4'), state='*')
async def wait_user_language_preferences(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    answer = (
        'Напишите язык, который Вам преподается на паре типа:\n'
        '<b>Иностранный язык в профессиональной сфере (ваш язык)</b>\n\n'
        'Например можно указать (в любом регистре):\n'
        '<em>Английский</em> или <em>Русский</em>'
    )
    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
        parse_mode='HTML',
    )

    await MainStates.add_language_preference.set()


@dp.message_handler(state=MainStates.add_language_preference)
async def set_user_language_preferences(message: types.Message, state: FSMContext):
    # Добавить обработку отсутствия пользователя в БД
    db.check_user(message.chat.id)

    preferences = json.loads(
        db.get('users', 'preferences', 'user_id', message.chat.id))
    preferences['foreign_lan'] = message.text.split('\n')[0].lower()
    db.update(
        'users',
        (('preferences', json.dumps(preferences, ensure_ascii=False)), ),
        'user_id', message.chat.id
    )
    await message.answer(
        "Язык успешно установлен!\n"
        "Текущие настройки можно посмотреть с помощью команды /settings"
    )
    await state.finish()


@dp.message_handler(commands=['links'], state='*')
async def links_show_interface(message: types.Message, state: FSMContext):
    await state.finish()
    # Добавить обработку отсутствия пользователя в БД
    db.check_user(message.chat.id)
    text, markup = lm.show_page(message.chat.id)
    await message.answer(
        text=text,
        reply_markup=markup,
        parse_mode='HTML',
    )


@dp.callback_query_handler(lm.list.filter(action=['main', 'prev', 'next']),
                           state='*')
async def query_show_prev_next_page(query: types.CallbackQuery,
                                    callback_data: typing.Dict[str, str]):
    await query.answer()
    cur_page = int(callback_data['page_num'])
    text, markup = lm.show_page(query.message.chat.id, cur_page)
    await query.message.edit_text(
        text=text,
        reply_markup=markup,
        parse_mode='HTML',
    )


@dp.callback_query_handler(lm.list.filter(action='view'), state='*')
async def query_show_link_info(query: types.CallbackQuery,
                               callback_data: typing.Dict[str, str]):
    cur_page = int(callback_data['page_num'])
    ind = int(callback_data['id']) - 1

    regex = ".(.?)\n\\D+: (.*)\n\\D+: (.*)"
    message_text = query.message.text
    data = re.findall(regex, message_text)
    link = data[ind % lm.WIDTH][1:]

    new_ind = lm.check_existing_link(query.message.chat.id, link, ind)
    if new_ind == -1:
        await query.answer('Такого номера не существует!')
        text, markup = lm.show_page(query.message.chat.id, cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
            parse_mode='HTML')
        return
    elif new_ind != ind:
        ind = new_ind
        cur_page = ind // lm.WIDTH

    try:
        await query.answer()
        text, markup = lm.view_link_data(query.message.chat.id, cur_page, ind)
        await query.message.edit_text(text, reply_markup=markup)
    except:
        log.exception('Something went wrong with showing link'
                      f'user ID:[{query.message.chat.id}]')
        await query.answer('Произошла непредвиденная ошибка.')


@dp.callback_query_handler(lm.list.filter(action=['edit']), state='*')
async def query_edit_info(query: types.CallbackQuery,
                          callback_data: typing.Dict[str, str],
                          state: FSMContext):
    text = query.message.text
    regex = re.compile(".(.?)\n\\D+: (.*)\n\\D+: (.*)")
    data = regex.search(text).groups()
    ind = int(data[0])-1
    link = data[1:]

    cur_page = int(callback_data['page_num'])
    ind = lm.check_existing_link(query.message.chat.id, link, ind)
    if ind == -1:
        await query.answer("Вы пытаетесь изменить несуществующую"
                           "/измененную ссылку!")
        text, markup = lm.show_page(query.message.chat.id, cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
            parse_mode='HTML',
        )
        return

    variant = callback_data['id']
    answer = 'Введите '
    if variant == '1':
        additional = 'новый предмет/преподавателя'
    elif variant == '2':
        additional = 'новую ссылку'
    else:
        additional = 'новую информацию'
    answer += additional
    await query.answer(answer)

    async with state.proxy() as data:
        data['main'] = query.message.message_id
        data['page_num'] = cur_page
        data['var'] = variant
        data['ind'] = int(ind)

    await bot.send_message(
            text=answer,
            chat_id=query.message.chat.id,
            parse_mode='HTML',
    )
    await LinkStates.edit_link.set()


@dp.message_handler(state=LinkStates.edit_link)
async def state_edit_link(message: types.Message, state: FSMContext):
    message_text = message.text.split('\n')[0]
    async with state.proxy() as data:
        cur_page = data['page_num']
        ind = data['ind']
        variant = data['var']
        if variant == '1':
            lm.update_link_lesson(message.chat.id, ind, message_text)
        elif variant == '2':
            lm.update_link_url(message.chat.id, ind, message_text)

        text, markup = lm.view_link_data(message.chat.id, cur_page, ind)
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=data['main'],
                reply_markup=markup,
                parse_mode='HTML',
            )
        except MessageNotModified:
            # Информация в ссылке не изменилась
            pass
        await state.finish()


@dp.callback_query_handler(lm.list.filter(action='delete_link'), state='*')
async def query_delete_link(query: types.CallbackQuery,
                            callback_data: typing.Dict[str, str],
                            state: FSMContext):
    await state.finish()
    text = query.message.text
    regex = re.compile(".(.?)\n\\D+: (.*)\n\\D+: (.*)")
    data = regex.search(text).groups()
    ind = int(data[0])-1
    link = data[1:]
    try:
        result = lm.delete_link_by_info(query.message.chat.id, link, ind)
        if result == 0:
            await query.answer('Ссылка успешно удалена!')
        elif result == -1:
            await query.answer('Ссылка отсутствует.')
    except:
        log.exception('Something went wrong with deleting link'
                      f'user ID:[{query.message.chat.id}]')
        await query.answer('Произошла непредвиденная ошибка.')

    cur_page = int(callback_data['page_num'])
    text, markup = lm.show_page(query.message.chat.id, cur_page)
    await query.message.edit_text(
        text=text,
        reply_markup=markup,
        parse_mode='HTML',
    )


# Возможно стоит добавить ограничитель нажатий
@dp.callback_query_handler(lm.list.filter(action='add'))
async def query_add_link(query: types.CallbackQuery,
                         callback_data: typing.Dict[str, str],
                         state: FSMContext):
    await query.answer()
    answer = ("Для добавления ссылки на пару, укажите "
              "преподавателя/предмет (в точности как в расписании), "
              "который желаете добавить и на следующей строке "
              "ссылку на занятие (BBB, zoom и т.п.)\n"
              "Например: \n"
              "<b>Иностранный язык в профессиональной сфере "
              "(английский язык)\n"
              "'Ссылка на занятие'</b>\n"
              "или\n"
              "<b>Иванов Иван Иванович\n"
              "'Cсылка на занятие'</b>")

    async with state.proxy() as data:
        data['main'] = query.message.message_id
        data['page_num'] = int(callback_data['page_num'])

    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
        parse_mode='HTML',
    )

    await LinkStates.input_link.set()


@dp.message_handler(state=LinkStates.input_link)
async def process_link(message: types.Message, state: FSMContext):
    message_text = message.text.split('\n')
    searched_data = []
    for text in message_text:
        if len(searched_data) >= 2:
            break
        if text != '':
            searched_data.append(text)

    if len(searched_data) < 2:
        await bot.send_message(
            text='Введенных данных недостаточно для добавления ссылки!',
            chat_id=message.chat.id,
        )
        return

    async with state.proxy() as data:
        cur_page = data['page_num']
        result = lm.append_link(message.chat.id,
                                *searched_data,
                                cur_page*lm.WIDTH)
        if result == 0:
            await bot.send_message(
                text='Ссылка успешно добавлена!',
                chat_id=message.chat.id,
                reply_markup=lm.back_to_main(cur_page),
            )
            text, markup = lm.show_page(message.chat.id, cur_page)
            try:
                await bot.edit_message_text(
                    text=text,
                    chat_id=message.chat.id,
                    message_id=data['main'],
                    reply_markup=markup,
                    parse_mode='HTML',
                )
            except MessageNotModified:
                # Информация на странице не изменилась
                pass
            await state.finish()
        elif result == -1:
            await bot.send_message(
                text=('Ваших ссылок стало слишком много,'
                      'удалите лишние с помощью кнопки '
                      '<b>Удалить ссылку</b>'),
                chat_id=message.chat.id,
                parse_mode='HTML',
            )
            await state.finish()
        else:
            await bot.send_message(
                text='Что-то пошло не так, попробуйте снова!',
                chat_id=message.chat.id
            )


# @dp.callback_query_handler(lm.list.filter(action='del'))
# async def query_delete_link_by_num(
#         query: types.CallbackQuery,
#         callback_data: typing.Dict[str, str],
#         state: FSMContext):
#
#     await query.answer('Для удаления ссылки из списка напишите его номер')
#
#     if len(lm.get_links(query.message.chat.id)) == 0:
#         await bot.send_message(
#             text="Ваш список ссылок пуст!",
#             chat_id=query.message.chat.id,
#             parse_mode='HTML',
#         )
#         return await state.finish()
#
#     async with state.proxy() as data:
#         data['main'] = query.message.message_id
#         data['page_num'] = int(callback_data['page_num'])
#
#     await bot.send_message(
#         text='Для удаления ссылки из списка напишите его номер',
#         chat_id=query.message.chat.id,
#         parse_mode='HTML',
#     )
#
#     await LinkStates.del_link.set()


def main():
    """
    Фоновый поток для выполнения сторонних задач, таких как:
    1) обновление кодов универа в БД,
    2) обновление текущего расписания в БД для всех пользователей,
    3) отправка уведомлений о начале пары.
    """
    tasks.init_taskmanager()

    # Основной поток для бота
    # executor.start_polling(dp, skip_updates=True, on_startup=db.insert_codes())
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
