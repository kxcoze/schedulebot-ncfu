import json
import logging
import typing

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import db


WIDTH = 5
API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)

dp = Dispatcher(bot, storage=MemoryStorage())


cbd_poll = CallbackData('poll', 'id',)
cbd_choice = CallbackData('choice', 'action', 'result')


class MainStates(StatesGroup):
    waiting_for_group_name = State()
    add_time_preference = State()


def show_optional_ikeyboard():
    text = (
        'Для изменения времени оповещения нажмите кнопку \n<em><b>Время уведомления</b></em>\n\n'
        'Для выбора типа пар, на которые будут приходить уведомления нажмите кнопку \n<em><b>Тип пар</b></em>'
    )
    markup = types.InlineKeyboardMarkup()

    markup.add(
            types.InlineKeyboardButton(
                'Время уведомления',
                callback_data=cbd_poll.new(id='1')),

            types.InlineKeyboardButton(
                'Тип пар',
                callback_data=cbd_poll.new(id='2')),
    )

    return text, markup


def show_type_preference_ikeyboard():
    text = (
        "От выбранного типа пары зависит, будут ли Вам приходить оповещения "
        "о парах, которые проводятся дистанционно или очно.\n"
        "<em>ВКС</em> — Уведомляются только дистанционные пары.\n"
        "<em>Очный</em> — Уведомляются только очные пары.\n"
        "<em>ВКС/Очный</em> — Уведомляются все пары.\n"
    )
    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            'ВКС',
            callback_data=cbd_choice.new(action='choose', result='distant')
        ),
        types.InlineKeyboardButton(
            'Очный',
            callback_data=cbd_choice.new(action='choose', result='full-time')
        ),
        types.InlineKeyboardButton(
            'ВКС/Очный',
            callback_data=cbd_choice.new(action='choose', result='all')
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            '« Вернуться назад',
            callback_data=cbd_poll.new(id='0'),
        )
    )
    return text, markup


@dp.message_handler(commands=['notifyme'])
async def set_user_notification(message: types.Message):
    # Добавить обработку отсутствия пользователя в БД
    db.update('users', (('notifications', 1), ), 'user_id', message.chat.id)
    try:
        pref_time = json.loads(db.get(
            'users', 'preferences', 'user_id', message.chat.id))['pref_time']
    except Exception as e:
        print(e)
    await message.reply(
        "Вы успешно подписались на уведомления о начале пары!\n\n"
        f"Время за которое Вас уведомлять о начале пары: {pref_time} минут\n"
        "Желаете ли определить время за которое Вас оповещать?\n"
        "Если да, нажмите/введите /setpreferences"
    )


@dp.message_handler(commands=['setpreferences'])
async def command_set_user_preferences(message: types.Message, state: FSMContext):
    await state.finish()
    text, markup = show_optional_ikeyboard()
    await message.answer(
        text,
        reply_markup=markup,
        parse_mode='HTML',
    )


@dp.callback_query_handler(cbd_poll.filter(id='0'), state='*')
async def query_set_user_preferences(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    text, markup = show_optional_ikeyboard()
    await bot.edit_message_text(
        text=text,
        chat_id=query.from_user.id,
        message_id=query.message.message_id,
        reply_markup=markup,
        parse_mode='HTML',
    )


@dp.callback_query_handler(cbd_poll.filter(id='1'), state='*')
async def wait_user_time_preferences(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    answer = (
        "Для установки времени уведомления начала пары, "
        "напишите число от 0 до 60\n"
    )
    await bot.send_message(
                text=answer,
                chat_id=query.from_user.id,
                parse_mode='HTML',
    )

    await MainStates.add_time_preference.set()


@dp.message_handler(state=MainStates.add_time_preference)
async def set_user_time_preferences(message: types.Message, state: FSMContext):
    if message.text.isdigit() and 0 <= int(message.text) <= 60:
        # Добавить обработку отсутствия пользователя в БД
        preferences = json.loads(
            db.get('users', 'preferences', 'user_id', message.chat.id))
        preferences['pref_time'] = message.text
        db.update(
            'users',
            (('preferences', json.dumps(preferences, ensure_ascii=False)), ),
            'user_id', message.chat.id
        )
        await message.answer("Время успешно установлено!")
        await state.finish()
    else:
        await message.answer("Вы ввели не подходящее число!")


@dp.callback_query_handler(cbd_poll.filter(id='2'), state='*')
async def wait_user_type_preferences(query: types.CallbackQuery):
    await query.answer()
    text, markup = show_type_preference_ikeyboard()
    await bot.edit_message_text(
            text=text,
            chat_id=query.from_user.id,
            message_id=query.message.message_id,
            reply_markup=markup,
            parse_mode='HTML',
    )
    # await MainStates.add_time_preference.set()


@dp.callback_query_handler(cbd_choice.filter(action='choose'), state='*')
async def set_user_type_preferences(query: types.CallbackQuery, callback_data: typing.Dict[str, str]):
    await query.answer('Успешно!')
    # Добавить обработку отсутствия пользователя в БД
    preferences = json.loads(
        db.get('users', 'preferences', 'user_id', query.from_user.id))
    preferences['notification_type'] = callback_data['result']
    db.update(
        'users',
        (('preferences', json.dumps(preferences, ensure_ascii=False)), ),
        'user_id', query.from_user.id
    )


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
