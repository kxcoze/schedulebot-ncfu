import os
import logging
import re
import asyncio
import typing
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext, filters
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified

import db
import scheduleCreator as SC
import schedulerForTasks as tasks
import linkmanager as lm


API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'
WIDTH = 5
main_commands_viewing_schedule, optional_commands_viewing_schedule = SC.get_every_aliases_days_week()

ex = ThreadPoolExecutor(max_workers=1)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)

# Возможно стоит изменить storage
dp = Dispatcher(bot, storage=MemoryStorage())

list = CallbackData(
        'page',
        'id',
        'page_num',
        'action',
)  # page:<id>:<page_num>:<action>


class MainStates(StatesGroup):
    waiting_for_group_name = State()


class AddStates(StatesGroup):
    input_link = State()
    edit_link = State()
    del_link = State()


@dp.message_handler(commands=['start'])
async def initializebot(message: types.Message):
    """Приветствие от бота по команде /start"""
    """Возможно здесь стоит добавить юзера в базу данных"""
    await message.answer(
            "Привет! \n"
            "Я бот для расписаний СКФУ! \n"
            "Для команд просмотра всех команд наберите /help \n"
            "<em>Powered by aiogram.</em>", parse_mode='HTML')


@dp.message_handler(commands=['help'], state='*')
async def send_help_commands(message: types.Message, state: FSMContext):
    """Вывод всех возможных команд бота"""
    await state.finish()
    await message.answer(
            "Список всех команд: \n"
            "/setgroup - Ввод группы для показа расписания \n"
            "/today - Посмотреть расписание на сегодня \n"
            "/tommorow или /tom - Посмотреть расписание на завтра \n"
            "/week - Посмотреть расписание на неделю \n"
            "/bell - Посмотреть расписание звонков \n"
            "/notifyme - Подписаться на уведомления о начале пары \n"
            "/stopnotifyme - Отписаться от уведомлений ")


@dp.message_handler(commands=['setgroup'], state=None)
async def set_user_group(message: types.Message):
    await message.reply(
            "Введите название группы (в любом регистре) и укажите номер подгруппы (можно оставить пустым), например:\n"
            "ЭКП-б-о-19-1 \n"
            "КГИ-б-о-18-1(1) \n"
            "тбо-б-о-19-1 2 \n")

    await MainStates.waiting_for_group_name.set()


@dp.message_handler(state=MainStates.waiting_for_group_name)
async def wait_for_group_name(message: types.Message, state: FSMContext):
    # Регулярное выражение для поиска группы
    regroup = re.compile('(([а-яА-я]-[а-яА-Я]{3}|[а-яА-Я]{3})-[а-я]+?-[а-я]+?-\d{1,3}(-[0-9а-яА-Я.]+|-\d|))|([а-яА-я]-[а-яА-Я]{1,3}-\d+)')

    # Регулярное выражение для поиска подгруппы
    resubgroup = re.compile('[^-\\d]([0-9]{1})([^-\\d]|\\Z)')

    try:
        group_name = regroup.search(message.text).group().lower()
    except:
        await message.reply("Введен неверный формат группы!")
        return

    try:
        # Поиск подгруппы в сообщении пользователя
        group_subnum = resubgroup.search(message.text).groups()[0]
    except:
        group_subnum = 0


    group_code = db.get('univer_code', 'group_code', 'group_name', group_name)

    # Возможно есть реализация получше! Может быть перенести в другой скрипт?
    if not group_code == -1:
        answer_success = await message.answer("Группа найдена, пробуем загрузить Ваше расписание...")
        try:
            await asyncio.get_running_loop().run_in_executor(ex, SC.update_schedule_user, message.chat.id, group_code, group_subnum)
        except:
            # Успешно
            pass
        finally:
            await bot.edit_message_text(chat_id=message.chat.id,
                                        message_id=answer_success.message_id,
                                        text="Расписание на неделю загружено!\n"
                                             "Вы можете просмотреть его используя команду /week")
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
        """
        schedule = await asyncio.get_running_loop().run_in_executor(
                ex, SC.get_formatted_schedule, message.chat.id, command, week)
        """
        schedule = SC.get_formatted_schedule(message.chat.id, command, week)
        await message.answer(schedule, parse_mode='HTML')
    else:
        await message.reply("Похоже что Вы не выбрали группу перед тем как посмотреть расписание, пожалуйста, воспользуйтесь командой /setgroup и укажите Вашу группу")


@dp.message_handler(commands=['notifyme'])
async def set_user_notification(message: types.Message):
    db.update('users', (('notifications', 1), ), 'user_id', message.chat.id)
    await message.reply("Вы успешно подписались на уведомления о начале пары!")


@dp.message_handler(commands=['stopnotifyme'])
async def stop_user_notification(message: types.Message):
    db.update('users', (('notifications', 0), ), 'user_id', message.chat.id)
    await message.reply("Вы отписались от уведомлений о начале пары!")


@dp.message_handler(commands=['bell'])
async def print_commands(message: types.Message):
    await message.answer(SC.get_formatted_schedule_bell(), parse_mode='HTML')


def search_nonempty_page(links, left, right, cur_page):
    page = cur_page
    while page > 0 and len(links[left:right]) == 0:
        right -= WIDTH
        left -= WIDTH
        page -= 1

    return left, right, page


def show_page(user_id, cur_page=0):
    links = lm.get_links(user_id)
    left = cur_page * WIDTH
    right = cur_page*WIDTH + WIDTH

    if len(links[left:right]) == 0:
        left, right, cur_page = search_nonempty_page(links,
                                                     left, right, cur_page)

    add_prev = False
    add_next = False

    links_size = len(links)
    if cur_page > 0:
        add_prev = True

    if right < links_size:
        add_next = True

    if links_size == 0:
        text = ('Список ваших ссылок пуст.\n'
                'Нажмите кнопку <b>Добавить ссылку</b> '
                'для добавления очередной ссылки \n'
                'Заметьте поддерживается не более 15 ссылок \n'
                'Если предмет/преподаватель указаны корректно, то '
                'при оповещении о начале пары '
                'cсылка добавится автоматически.')
    else:
        text = '<b><em>Ваши ссылки</em></b>\n'
    markup = types.InlineKeyboardMarkup()
    menu = []
    if add_prev:
        menu.append(types.InlineKeyboardButton(
                '«',
                callback_data=list.new(
                    id='-', page_num=cur_page-1, action='prev'))
                    )
    for ind, link in enumerate(links[left:right], start=left+1):
        text += (f"№{ind}\n"
                 f"Предмет/Преподаватель: {link[0]}\n"
                 f"Ссылка на пару: {link[1]}\n\n")

        menu.append(types.InlineKeyboardButton(
                ind,
                callback_data=list.new(
                    id=ind, page_num=cur_page, action='view'))
                    )
    if add_next:
        menu.append(types.InlineKeyboardButton(
                '»',
                callback_data=list.new(
                    id='-', page_num=cur_page+1, action='next'))
                    )

    markup.row(*menu)

    markup.add(
            types.InlineKeyboardButton(
                'Добавить ссылку',
                callback_data=list.new(
                    id='-', page_num=cur_page, action='add')),
    )
    return text, markup


def view_link_data(user_id, cur_page, ind):
    markup = types.InlineKeyboardMarkup()

    links = lm.get_links(user_id)
    text = ''.join(f"№{ind+1}\n"
                   f"Предмет/Преподаватель: {links[ind][0]}\n"
                   f"Ссылка на пару: {links[ind][1]}\n")
    markup.row(
            types.InlineKeyboardButton(
                'Изменить предмет/препод.',
                callback_data=list.new(
                    id="1", page_num=cur_page, action='edit')),

            types.InlineKeyboardButton(
                'Изменить ссылку',
                callback_data=list.new(
                    id="2", page_num=cur_page, action='edit')),
    )
    markup.row(
            types.InlineKeyboardButton(
                'Удалить ссылку',
                callback_data=list.new(
                    id=ind, page_num=cur_page, action='delete_link')),

            types.InlineKeyboardButton(
                '« Вернуться назад',
                callback_data=list.new(
                    id='-', page_num=cur_page, action='main')),
    )
    return text, markup


def back_to_main(cur_page):
    markup = types.InlineKeyboardMarkup()

    markup.add(
            types.InlineKeyboardButton(
                '« Вернуться назад',
                callback_data=list.new(
                    id='-', page_num=cur_page, action='main')),
    )
    return markup


@dp.message_handler(commands=['links'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    try:
        text, markup = show_page(message.chat.id)
        await message.answer(
                text=text,
                reply_markup=markup,
                parse_mode='HTML',
        )
    except TypeError:
        # Если пользователь пытается работать со ссылками
        # но его нет в БД
        db.insert_new_user(message.chat.id)
        await cmd_start(message, state)


@dp.callback_query_handler(list.filter(action=['main', 'prev', 'next']),
                           state='*')
async def query_show_prev_next_page(query: types.CallbackQuery,
                                    callback_data: typing.Dict[str, str]):
    await query.answer()
    cur_page = int(callback_data['page_num'])
    text, markup = show_page(query.from_user.id, cur_page)
    await query.message.edit_text(
            text=text,
            reply_markup=markup,
            parse_mode='HTML',
    )


@dp.callback_query_handler(list.filter(action='view'), state='*')
async def query_show_link_info(query: types.CallbackQuery,
                               callback_data: typing.Dict[str, str]):
    cur_page = int(callback_data['page_num'])
    ind = int(callback_data['id']) - 1

    regex = ".(.?)\n\\D+: (.*)\n\\D+: (.*)"
    message_text = query.message.text
    data = re.findall(regex, message_text)
    link = data[ind % WIDTH][1:]

    new_ind = lm.check_existing_link(query.from_user.id, link, ind)
    if new_ind == -1:
        await query.answer('Такого номера не существует!')
        text, markup = show_page(query.from_user.id, cur_page)
        await query.message.edit_text(
            text=text,
            reply_markup=markup,
            parse_mode='HTML')
        return
    elif new_ind != ind:
        ind = new_ind
        cur_page = ind // WIDTH

    try:
        await query.answer()
        text, markup = view_link_data(query.from_user.id, cur_page, ind)
        await query.message.edit_text(text, reply_markup=markup)
    except:
        await query.answer('Произошла непредвиденная ошибка.')


@dp.callback_query_handler(list.filter(action=['edit']), state='*')
async def query_edit_info(query: types.CallbackQuery,
                          callback_data: typing.Dict[str, str],
                          state: FSMContext):
    text = query.message.text
    regex = re.compile(".(.?)\n\\D+: (.*)\n\\D+: (.*)")
    data = regex.search(text).groups()
    ind = int(data[0])-1
    link = data[1:]

    cur_page = int(callback_data['page_num'])
    ind = lm.check_existing_link(query.from_user.id, link, ind)
    if ind == -1:
        await query.answer("Вы пытаетесь изменить несуществующую"
                           "/измененную ссылку!")
        text, markup = show_page(query.from_user.id, cur_page)
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
                chat_id=query.from_user.id,
                parse_mode='HTML',
    )
    await AddStates.edit_link.set()


@dp.message_handler(state=AddStates.edit_link)
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

        text, markup = view_link_data(message.chat.id, cur_page, ind)
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


@dp.callback_query_handler(list.filter(action='delete_link'), state='*')
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
        result = lm.delete_link_by_info(query.from_user.id, link, ind)
        if result == 0:
            await query.answer('Ссылка успешно удалена!')
        elif result == -1:
            await query.answer('Ссылка отсутствует.')
    except:
        await query.answer('Произошла непредвиденная ошибка.')

    cur_page = int(callback_data['page_num'])
    text, markup = show_page(query.from_user.id, cur_page)
    await query.message.edit_text(
            text=text,
            reply_markup=markup,
            parse_mode='HTML',
    )


# Возможно стоит добавить ограничитель нажатий
@dp.callback_query_handler(list.filter(action='add'))
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
    await AddStates.input_link.set()
    async with state.proxy() as data:
        data['main'] = query.message.message_id
        data['page_num'] = int(callback_data['page_num'])
    await bot.send_message(
            text=answer,
            chat_id=query.from_user.id,
            parse_mode='HTML',
    )


@dp.message_handler(state=AddStates.input_link)
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
                                cur_page*WIDTH)
        if result == 0:
            await bot.send_message(
                    text='Ссылка успешно добавлена!',
                    chat_id=message.chat.id,
                    reply_markup=back_to_main(cur_page),
            )
            text, markup = show_page(message.chat.id, cur_page)
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


@dp.callback_query_handler(list.filter(action='del'))
async def query_delete_link_by_num(
        query: types.CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):

    await query.answer('Для удаления ссылки из списка напишите его номер')

    if len(lm.get_links(query.from_user.id)) == 0:
        await bot.send_message(
                text="Ваш список ссылок пуст!",
                chat_id=query.from_user.id,
                parse_mode='HTML',
        )
        return await state.finish()

    async with state.proxy() as data:
        data['main'] = query.message.message_id
        data['page_num'] = int(callback_data['page_num'])

    await bot.send_message(
            text='Для удаления ссылки из списка напишите его номер',
            chat_id=query.from_user.id,
            parse_mode='HTML',
    )

    await AddStates.del_link.set() 


def main():
    """
    Фоновый поток для отслеживания сторонних задач, таких как: 
    1) обновление кодов универа в БД, 
    2) обновление текущего расписания в БД для всех пользователей,
    3) отправка уведомлений о начале пары.
    """
    tasks._main()

    # Основной поток для бота
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
