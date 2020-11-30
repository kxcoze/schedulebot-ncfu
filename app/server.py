import logging
import re

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

import db
import scheduleCreator as SC

API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'


logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class MainStates(StatesGroup):
    waiting_for_group_name = State()

@dp.message_handler(commands=['start'])
async def initializebot(message: types.Message):
    """Приветствие от бота по команде /start"""
    """Возможно здесь стоит добавить юзера в базу данных"""
    await message.answer(
            "Привет! \n"
            "Я бот для расписаний СКФУ! \n"
            "Для команд просмотра всех команд наберите /help \n"
            "<em>Powered by aiogram.</em>", parse_mode='HTML')


@dp.message_handler(commands=['help'])
async def send_help_commands(message: types.Message):
    """Вывод всех возможных команд бота"""
    await message.answer(
            "Список команд: \n"
            "/setgroup - Ввод группы для показа расписания \n"
            "/today - Посмотреть расписание на сегодня \n"
            "/tommorow или /tom - Посмотреть расписание на завтра \n"
            "/week - Посмотреть расписание на неделю \n"
            "/notifyMe - Подписаться на уведомления о начале пары \n"
            "/stopNotifyMe - Отписаться от уведомлений ")

@dp.message_handler(commands=['setGroup'], state=None)
async def set_user_group(message: types.Message):
    await MainStates.waiting_for_group_name.set()
    await message.reply(
            "Введите название группы (в любом регистре), например:\n"
            "ЭКП-б-о-19-1 \n")


@dp.message_handler(state=MainStates.waiting_for_group_name)
async def wait_for_group_name(message: types.Message, state: FSMContext):
    regex = re.compile('(([а-яА-я]-[а-яА-Я]{3}|[а-яА-Я]{3})-[а-я]+?-[а-я]+?-\d{1,3}(-[0-9а-яА-Я.]+|-\d|))|([а-яА-я]-[а-яА-Я]{1,3}-\d+)')
    try:
        group_name = regex.search(message.text).group().lower()
    except:
        await message.reply("Введен неверный формат группы!")
        await state.finish()
        return

    group_code = db.get('group_code', 'univer_code', 'group_name', group_name)
    if not group_code == -1:
        schedule = SC.insert_db_json_schedule(group_code)
        try:
            db.insert('users', message.chat.id, group_code, 0, schedule)
        except db.sqlite3.IntegrityError:
            db.update('users', 'group_code', group_code, 'user_id', message.chat.id)    
            db.update('users', 'schedule', schedule, 'user_id', message.chat.id)
        await message.answer("Успешно!")
    else: 
        await message.reply("Введенная группа не существует, попробуйте снова")
    await state.finish()


@dp.message_handler(commands=['week', 'today', 'tommorow', 'tom'])
async def make_user_schedule(message: types.Message):
    command = re.compile('/\w+').search(message.text).group()[1:]
    group_code = db.get('group_code', 'users', 'user_id', message.chat.id)
    if not group_code == -1:
        if command == 'tom':
            command = 'tommorow'
        schedule = SC.get_formatted_schedule(message.chat.id, command)
        await message.answer(schedule, parse_mode='HTML')
    else:
        await message.reply("Похоже что Вы не выбрали группу перед тем как посмотреть расписание, пожалуйста, воспользуйтесь командой /setGroup и укажите Вашу группу")

@dp.message_handler(commands=['notifyMe'])
async def set_user_notification(message: types.Message):
    pass

@dp.message_handler(commands=['stopNotifyMe'])
async def stop_user_notification(message: types.Message):
    pass

@dp.message_handler(commands=[])
async def print_commands(message: types.Message):
    await message.answer()

"""
@dp.message_handler(commands=['magic'])
async def show_animation(message: types.Message):
    
    ans = "Загрузка данных начата! "
    mes_bot = await bot.send_message(message.chat.id, ans+'|')
    
    for i in animation.anim():
        await bot.edit_message_text(chat_id=message.chat.id,message_id=mes_bot.message_id,text=(ans+i))
"""

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
