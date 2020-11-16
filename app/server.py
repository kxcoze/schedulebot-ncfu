import logging

from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'


logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)



@dp.message_handler(commands=['start'])
async def initializebot(message: types.Message):
    """Приветствие от бота по команде /start"""
    """Возможно здесь стоит добавить юзера в базу данных"""
    await message.answer(
            "Привет! \n"
            "Я бот для расписаний СКФУ! \n"
            "Для команд просмотра всех команд наберите /help.\n"
            "Powered by aiogram.")


@dp.message_handler(commands=['help'])
async def send_help_commands(message: types.Message):
    """Вывод всех возможных команд бота"""
    await message.answer(
            "Список команд: \n"
            "/getGroup - Составить Ваше личное расписание занятий. \n"
            "/schedule - Посмотреть Ваше текущее расписание на неделю. \n"
            "/notifyMe - Подписаться на уведомления о начале пары. \n"
            "/stopNotifyMe - Отписаться от уведомлений. ")

@dp.message_handler(commands=['setGroup'])
async def make_user_group(message: types.Message):
    pass

@dp.message_handler(commands=['schedule'])
async def make_user_group(message: types.Message):
    pass

@dp.message_handler(commands=['notifyMe'])
async def make_user_group(message: types.Message):
    pass

@dp.message_handler(commands=['stopNotifyMe'])
async def make_user_group(message: types.Message):
    pass

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
