import os

import logging
import re
import asyncio
import threading
import schedule
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from concurrent.futures import ThreadPoolExecutor

import db
import scheduleCreator as SC
import schedulerForTasks as tasks

API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'

ex = ThreadPoolExecutor(max_workers=os.cpu_count()-2)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)

# Возможно стоит изменить storage
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


@dp.message_handler(commands=['help'], state='*')
async def send_help_commands(message: types.Message, state: FSMContext):
    await state.finish()
    """Вывод всех возможных команд бота"""
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
    await MainStates.waiting_for_group_name.set()
    await message.reply(
            "Введите название группы (в любом регистре) и укажите номер подгруппы (можно оставить пустым), например:\n"
            "ЭКП-б-о-19-1 \n"
            "КГИ-б-о-18-1(1) \n"
            "тбо-б-о-19-1 2 \n")


@dp.message_handler(state=MainStates.waiting_for_group_name)
async def wait_for_group_name(message: types.Message, state: FSMContext):
    # Регулярное выражение для поиска группы
    regroup = re.compile('(([а-яА-я]-[а-яА-Я]{3}|[а-яА-Я]{3})-[а-я]+?-[а-я]+?-\d{1,3}(-[0-9а-яА-Я.]+|-\d|))|([а-яА-я]-[а-яА-Я]{1,3}-\d+)')

    # Регулярное выражение для поиска подгруппы
    resubgroup = re.compile('[^-\d]([0-9]{1})([^-\d]|\Z)')
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


@dp.message_handler(commands=['week', 'today', 'tommorow', 'tom'])
async def make_user_schedule(message: types.Message):
    command = re.compile('/\w+').search(message.text).group()[1:]
    group_code = db.get('users', 'group_code', 'user_id', message.chat.id)
    if not group_code == -1:
        if command == 'tom':
            command = 'tommorow'
        # Not save! Need to use same threads for sqlite3 and executor
        schedule = await asyncio.get_running_loop().run_in_executor(ex, SC.get_formatted_schedule, message.chat.id, command)
        await message.answer(schedule, parse_mode='HTML')
    else:
        await message.reply("Похоже что Вы не выбрали группу перед тем как посмотреть расписание, пожалуйста, воспользуйтесь командой /setgroup и укажите Вашу группу")

@dp.message_handler(commands=['notifyme'])
async def set_user_notification(message: types.Message):
    db.update('users', [['notifications', 1]], 'user_id', message.chat.id)
    await message.reply("Вы успешно подписались на уведомления о начале пары!")

@dp.message_handler(commands=['stopnotifyme'])
async def stop_user_notification(message: types.Message):
    db.update('users', [['notifications', 0]], 'user_id', message.chat.id)
    await message.reply("Вы отписались от уведомлений о начале пары!")

@dp.message_handler(commands=['bell'])
async def print_commands(message: types.Message):
    await message.answer(SC.get_formatted_schedule_bell(), parse_mode='HTML')

@dp.message_handler(commands=[])
async def print_commands(message: types.Message):
    await message.answer()

def main():
    """Поток для отслеживания сторонних задач, таких как: 
    обновление кодов универа в БД, 
    обновление текущего расписания в БД для всех пользователей,
    отправка уведомлений о начале пары.
    """
    tasks._main()

    #Основной поток для бота
    executor.start_polling(dp, skip_updates=True)

if __name__ == '__main__':
    main()
