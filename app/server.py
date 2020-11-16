import logging

from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'


logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)



@dp.message_handler(commands=['start','help'])
async def send_welcome(message: types.Message):
    """Приветствие от бота по команде /start и /help"""
    await message.reply("Hi!\nI'm ScheduleBot!\nPowered by aiogram.")






if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
