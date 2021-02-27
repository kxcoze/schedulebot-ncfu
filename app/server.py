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
import inlinekeyboard as ik
from bookclasses import Book, Links, Homework
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


@dp.message_handler(commands=['start'])
async def initializebot(message: types.Message):
    """Добавить клавиатуру"""
    """Приветствие от бота по команде /start"""
    await message.answer(
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
            "<b><em>Powered by aiogram</em></b>",
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
    user_book = Links(message.chat.id)
    text, markup = user_book.show_page()
    await message.answer(
        text=text,
        reply_markup=markup,
    )


@dp.message_handler(commands=['homework'], state='*')
async def homework_show_interface(message: types.Message, state: FSMContext):
    await state.finish()
    # Добавить обработку отсутствия пользователя в БД
    db.check_user(message.chat.id)
    user_book = Homework(message.chat.id)
    text, markup = user_book.show_page()
    await message.answer(
        text=text,
        reply_markup=markup,
    )


@dp.callback_query_handler(Book.list.filter(action=['main', 'prev', 'next']),
                           state='*')
async def query_show_homework_prev_next_page(query: types.CallbackQuery,
                                    callback_data: typing.Dict[str, str]):
    await query.answer()
    cur_page = int(callback_data['page_num'])
    if callback_data['name'] == 'homework':
        user_book = Homework(query.message.chat.id)
    else:
        user_book = Links(query.message.chat.id)
    text, markup = user_book.show_page(cur_page)
    await query.message.edit_text(
        text=text,
        reply_markup=markup,
    )


@dp.callback_query_handler(Book.list.filter(action='view', name='links'), state='*')
async def query_show_link_info(query: types.CallbackQuery,
                               callback_data: typing.Dict[str, str]):
    cur_page = int(callback_data['page_num'])
    ind = int(callback_data['id']) - 1
    user_book = Links(query.message.chat.id)
    data_element = user_book.parse_msg(query.message.text)[ind % user_book.WIDTH][1:]
    new_ind = user_book.check_existing_data(data_element, ind)

    if new_ind == -1:
        await query.answer('Такого номера не существует!')
        text, markup = user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return
    elif new_ind != ind:
        ind = new_ind
        cur_page = ind // user_book.WIDTH

    try:
        text, markup = user_book.view_data_element(cur_page, ind)
        await query.answer()
        await query.message.edit_text(text, reply_markup=markup)
    except:
        log.exception('Something went wrong with showing link'
                      f'user ID:[{query.message.chat.id}]')
        await query.answer('Произошла непредвиденная ошибка.')


@dp.callback_query_handler(Book.list.filter(action='view', name='homework'), state='*')
async def query_show_homework_info(query: types.CallbackQuery,
                               callback_data: typing.Dict[str, str]):
    cur_page = int(callback_data['page_num'])
    ind = int(callback_data['id']) - 1
    user_book = Homework(query.message.chat.id)
    data_element = user_book.parse_msg(query.message.text)
    try:
        data_element = data_element[ind % user_book.WIDTH][1:]
    except IndexError:
        data_element = data_element[0][1:]
    finally:
        new_ind = user_book.check_existing_data(data_element, ind)

    if new_ind == -1:
        await query.answer('Такого номера не существует!')
        text, markup = user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return
    elif new_ind != ind:
        ind = new_ind
        cur_page = ind // user_book.WIDTH

    try:
        text, markup = user_book.view_data_element(cur_page, ind)
        await query.answer()
        await query.message.edit_text(text, reply_markup=markup)
    except:
        log.exception('Something went wrong with showing link'
                      f'user ID:[{query.message.chat.id}]')
        await query.answer('Произошла непредвиденная ошибка.')



@dp.callback_query_handler(Book.list.filter(action='view2', name='homework'), state='*')
async def query_show_homework_detail_info(query: types.CallbackQuery,
                               callback_data: typing.Dict[str, str]):
    ind_sub = int(callback_data['page_num'])
    ind_hmw = int(callback_data['id']) - 1
    user_book = Homework(query.message.chat.id)
    page_data = user_book.parse_msg(query.message.text)[0][1:]
    new_ind = user_book.check_existing_data(page_data, ind_sub)
    if new_ind == -1:
        await query.answer('Такого номера не существует!')
        text, markup = user_book.show_page()
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return

    ind_sub = new_ind
    cur_page = ind_sub // user_book.WIDTH
    user_pages = user_book.pages[ind_sub][1]
    if len(user_pages)-1 < ind_hmw or user_pages[ind_hmw] != page_data[1][ind_hmw]:
        ind_hmw = user_pages.index(page_data[1][ind_hmw])
    try:
        text, markup = user_book.view2_data_element(ind_sub, ind_hmw)
        await query.answer()
        await query.message.edit_text(text, reply_markup=markup)
    except:
        log.exception('Something went wrong with showing link'
                      f'user ID:[{query.message.chat.id}]')
        await query.answer('Произошла непредвиденная ошибка.')


@dp.callback_query_handler(Book.list.filter(action='add'))
async def query_add_data(query: types.CallbackQuery,
                         callback_data: typing.Dict[str, str],
                         state: FSMContext):
    await query.answer()

    async with state.proxy() as data:
        data['main'] = query.message.message_id
        data['page_num'] = int(callback_data['page_num'])
        data['name'] = callback_data['name']

    if callback_data['name'] == 'homework':
        answer = ("Для добавления домашнего задания, укажите название предмета, "
                  "далее на следующих строчках Ваше Д/З (до 5-ти строчек)\n"
                  "Например: \n"
                  "<b>БЖД \n"
                  "Подготовить первую практику на некст пару \n"
                  "Сделать 1, 2 лабы \n"
                  "Выучить термины. \n"
                  "*Возможная домашка №4* \n"
                  "*Возможная домашка №5* \n"
                  "</b>")
        await HomeworkStates.input_data.set()
    else:
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
        await LinksStates.input_data.set()

    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
        parse_mode='HTML',
    )


@dp.message_handler(state=HomeworkStates.input_data)
async def process_user_message_homework(message: types.Message, state: FSMContext):
    message_text = message.text.split('\n')
    searched_data = []
    for text in message_text[:6]:
        if text != '':
            searched_data.append(text)

    if not searched_data:
        await bot.send_message(
            text='Введенных данных недостаточно для добавления домашки!',
            chat_id=message.chat.id,
        )
        return


    async with state.proxy() as data:
        cur_page = data['page_num']
        message_id = data['main']
        name = data['name']

    user_book = Homework(message.chat.id)
    result = user_book.append_data(
        subject=searched_data[0],
        homework=searched_data[1:],
        pos=cur_page*user_book.WIDTH,
    )
    if result == 0:
        await bot.send_message(
            text='Предмет успешно добавлен!',
            chat_id=message.chat.id,
            reply_markup=user_book.back_to_main(cur_page, 'homework'),
        )
        text, markup = user_book.show_page(cur_page)
        try:
            await bot.edit_message_text(
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
        await bot.send_message(
            text=('Ваших предметов стало слишком много,'
                  'удалите лишние с помощью кнопки '
                  '<b>Удалить предмет</b>'),
            chat_id=message.chat.id,
            parse_mode='HTML',
        )
        await state.finish()
    else:
        await bot.send_message(
            text='Что-то пошло не так, попробуйте снова!',
            chat_id=message.chat.id
        )



@dp.callback_query_handler(Book.list.filter(action='add2'))
async def query_additional_data(query: types.CallbackQuery,
                                callback_data: typing.Dict[str, str],
                                state: FSMContext):
    user_book = Homework(query.message.chat.id)
    data = user_book.parse_msg(query.message.text)[0]
    ind = int(data[0])-1
    page_data = data[1:]
    cur_page = int(callback_data['page_num'])
    res = user_book.check_existing_data(page_data, ind)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие"
                           "/измененные данные!")
        text, markup = user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return
    elif user_book.pages[res] != page_data:
        text, markup = user_book.view_data_element(cur_page, ind)
        try:
            await bot.edit_message_text(
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
        data['main'] = query.message.message_id
        data['page_num'] = int(callback_data['page_num'])
        data['ind'] = int(callback_data['id'])
        data['name'] = callback_data['name']

    answer = "Введите данные для добавления новой домашки"
    await HomeworkStates.input_homework.set()

    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


@dp.message_handler(state=HomeworkStates.input_homework)
async def process_user_homework_detail_info(message: types.Message,
                                            state: FSMContext):
    message_text = message.text.split('\n')[0]

    async with state.proxy() as data:
        ind = data['ind']
        cur_page = data['page_num']
        message_id = data['main']
        name = data['name']
    user_book = Homework(message.chat.id)
    result = user_book.append_data(
        homework=message_text,
        ind=ind,
    )
    if result == 0:
        await bot.send_message(
            text='Домашка успешно добавлена!',
            chat_id=message.chat.id,
        )
        text, markup = user_book.view_data_element(cur_page, ind)
        try:
            await bot.edit_message_text(
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
        await bot.send_message(
            text=('Ваших домашек стало слишком много, '
                  'удалите лишние с помощью кнопки '
                  '<b>Удалить домашку</b>'),
            chat_id=message.chat.id,
            parse_mode='HTML',
        )
        await state.finish()
    else:
        await bot.send_message(
            text='Что-то пошло не так, попробуйте снова!',
            chat_id=message.chat.id
        )


@dp.message_handler(state=LinksStates.input_data)
async def process_user_message_link(message: types.Message, state: FSMContext):
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
        user_book = Links(message.chat.id)
        cur_page = data['page_num']
        result = user_book.append_data(*searched_data,
                                       cur_page*user_book.WIDTH)
        if result == 0:
            await bot.send_message(
                text='Ссылка успешно добавлена!',
                chat_id=message.chat.id,
                reply_markup=user_book.back_to_main(cur_page, 'links'),
            )
            text, markup = user_book.show_page(cur_page)
            try:
                await bot.edit_message_text(
                    text=text,
                    chat_id=message.chat.id,
                    message_id=data['main'],
                    reply_markup=markup,
                )
            except MessageNotModified:
                # Информация на странице не изменилась
                pass
            await state.finish()
        elif result == -1:
            await bot.send_message(
                text=('Ваших ссылок стало слишком много, '
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


@dp.callback_query_handler(Book.list.filter(action='edit'), state='*')
async def query_edit_info(query: types.CallbackQuery,
                          callback_data: typing.Dict[str, str],
                          state: FSMContext):

    if callback_data['name'] == 'homework':
        user_book = Homework(query.message.chat.id)
        additional = ''
        await HomeworkStates.edit_data.set()
    else:
        user_book = Links(query.message.chat.id)
        additional = '/преподавателя'
        await LinksStates.edit_data.set()
    data = user_book.parse_msg(query.message.text)[0]
    ind = int(data[0])-1
    page_data = data[1:]
    cur_page = int(callback_data['page_num'])
    res = user_book.check_existing_data(page_data, ind)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие"
                           "/измененные данные!")
        text, markup = user_book.show_page(cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return

    variant = callback_data['id']
    answer = 'Введите '
    if variant == '1':
        additional = f'новый предмет{additional}'
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
        data['ind'] = ind

    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
    )


@dp.message_handler(state=HomeworkStates.edit_data)
async def state_edit_homework(message: types.Message, state: FSMContext):
    message_text = message.text.split('\n')[0]
    user_book = Homework(message.chat.id)
    async with state.proxy() as data:
        cur_page = data['page_num']
        ind = data['ind']
        variant = data['var']
        message_id = data['main']
    if variant == '1':
        user_book.update_data_element_first_pos(message_text, ind)
    text, markup = user_book.view_data_element(cur_page, ind)
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=markup,
        )
    except MessageNotModified:
        # Информация в домашке не изменилась
        pass
    await state.finish()


@dp.message_handler(state=LinksStates.edit_data)
async def state_edit_link(message: types.Message, state: FSMContext):
    message_text = message.text.split('\n')[0]
    user_book = Links(message.chat.id)
    async with state.proxy() as data:
        cur_page = data['page_num']
        ind = data['ind']
        variant = data['var']
        if variant == '1':
            user_book.update_data_element_first_pos(message_text, ind)
        elif variant == '2':
            user_book.update_data_element_second_pos(message_text, ind)
        text, markup = user_book.view_data_element(cur_page, ind)
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=message.chat.id,
                message_id=data['main'],
                reply_markup=markup,
            )
        except MessageNotModified:
            # Информация в ссылке не изменилась
            pass
        await state.finish()


@dp.callback_query_handler(Book.list.filter(action='edit2', name='homework'))
async def query_edit_detail_info(query: types.CallbackQuery,
                                 callback_data: typing.Dict[str, str],
                                 state: FSMContext):
    user_book = Homework(query.message.chat.id)
    data = user_book.parse_msg(query.message.text)[0]
    page_data = data[1:]
    res = user_book.check_existing_data(page_data, int(data[0])-1)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие"
                           "/измененные данные!")
        text, markup = user_book.show_page()
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return
    ind_sub = res
    ind_hmw = int(callback_data['page_num']) - 1
    user_pages = user_book.pages[ind_sub][1]
    if len(user_pages)-1 < ind_hmw or user_pages[ind_hmw] != page_data[1][0]:
        ind_hmw = user_pages.index(page_data[1][0])

        text, markup = user_book.view2_data_element(ind_sub, ind_hmw)
        try:
            await bot.edit_message_text(
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
        data['main'] = query.message.message_id
        data['ind_sub'] = ind_sub
        data['ind_hmw'] = ind_hmw

    answer = "Введите новые данные для домашки"
    await HomeworkStates.edit_homework.set()

    await bot.send_message(
        text=answer,
        chat_id=query.message.chat.id,
        parse_mode='HTML',
    )


@dp.message_handler(state=HomeworkStates.edit_homework)
async def state_edit_homework_detail_info(message: types.Message,
                                          state: FSMContext):
    message_text = message.text.split('\n')[0]
    user_book = Homework(message.chat.id)
    async with state.proxy() as data:
        message_id = data['main']
        ind_sub = data['ind_sub']
        ind_hmw = data['ind_hmw']
    user_book.update_data_element_second_pos(message_text, ind_sub, ind_hmw)
    text, markup = user_book.view2_data_element(ind_sub, ind_hmw)
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message_id,
            reply_markup=markup,
        )
    except MessageNotModified:
        # Информация в домашке не изменилась
        pass
    await state.finish()


@dp.callback_query_handler(Book.list.filter(action='delete'), state='*')
async def query_delete_data(query: types.CallbackQuery,
                            callback_data: typing.Dict[str, str],
                            state: FSMContext):
    await state.finish()

    if callback_data['name'] == 'homework':
        user_book = Homework(query.message.chat.id)
        information = 'Предмет'
        data_element = user_book.parse_msg(query.message.text)[0][1:]
    else:
        user_book = Links(query.message.chat.id)
        information = 'Ссылка'
        data_element = user_book.parse_msg(query.message.text)[0][1:]
    try:
        result = user_book.delete_data_element_by_info(data_element)
        if result == 0:
            await query.answer(f'Данные успешно удалены!')
        elif result == -1:
            await query.answer(f'{information} отсутствует.')
    except:
        log.exception('Something went wrong with deleting link'
                      f'user ID:[{query.message.chat.id}]')
        await query.answer('Произошла непредвиденная ошибка.')

    cur_page = int(callback_data['page_num'])
    text, markup = user_book.show_page(cur_page)
    await query.message.edit_text(
        text=text,
        reply_markup=markup,
    )


@dp.callback_query_handler(Book.list.filter(action='delete2', name='homework'), state='*')
async def query_delete_homework(query: types.CallbackQuery,
                                callback_data: typing.Dict[str, str],
                                state: FSMContext):
    await state.finish()

    user_book = Homework(query.message.chat.id)
    data = user_book.parse_msg(query.message.text)[0]
    page_data = data[1:]
    res = user_book.check_existing_data(page_data, int(data[0])-1)
    if res == -1:
        await query.answer("Вы пытаетесь изменить несуществующие"
                           "/измененные данные!")
        text, markup = user_book.show_page()
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
        )
        return
    ind_sub = res
    ind_hmw = int(callback_data['page_num']) - 1
    cur_page = ind_sub+1 // user_book.WIDTH
    user_pages = user_book.pages[ind_sub][1]

    if len(user_pages)-1 < ind_hmw or user_pages[ind_hmw] != page_data[1][0]:
        ind_hmw = user_pages.index(page_data[1][0])
    information = 'Домашка'
    result = user_book.delete_homework_by_ind(ind_sub, ind_hmw)
    if result == 0:
        await query.answer(f'Данные успешно удалены!')
    elif result == -1:
        await query.answer(f'{information} отсутствует.')
    try:
        pass
    except:
        log.exception('Something went wrong with deleting link'
                      f'user ID:[{query.message.chat.id}]')
        await query.answer('Произошла непредвиденная ошибка.')

    text, markup = user_book.view_data_element(cur_page, ind_sub)
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            reply_markup=markup,
        )
    except MessageNotModified:
        # Информация в домашке не изменилась
        pass


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
