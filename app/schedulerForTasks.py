import time
import threading
import json
import asyncio
from pprint import pprint
from datetime import datetime

import schedule
from aiogram import Bot, types

import db
import scheduleCreator as SC

API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'

bot = Bot(token=API_TOKEN)


def update_schedules_users():
    data = db.fetchall('users', ('user_id', 'group_code', 'subgroup'))
    for user in data:
        # print(user['user_id'], user['group_code'], user['subgroup'])
        try:
            SC.update_schedule_user(user['user_id'], user['group_code'], user['subgroup'])
        except:
            # print("FAILED")
            continue
        # print("SUCCESS")


def prepare_receivers(cur_lesson):
    cur_weekday, cur_time = datetime.today().weekday(), datetime.datetime.now().strftime('%H:%M').split(':')
    if cur_weekday == 6:
        return

    weekdays = {0 : 'Понедельник',
                1 : 'Вторник',
                2 : 'Среда',
                3 : 'Четверг',
                4 : 'Пятница',
                5 : 'Суббота',
                6 : 'Воскресенье'}

    cur_day = weekdays[cur_weekday]


    time_lesson_start = SC._get_schedule_bell_ncfu()[cur_lesson].split(' - ')[0].split(':')
    verification_time = (
        int(time_lesson_start[0]) - int(cur_time[0]),
        int(time_lesson_start[-1]) - int(cur_time[-1]),
    )
    if verification_time[0] >= 1:
        verification_time = verification_time[0]
    else:
        verification_time = verification_time[-1]

    data = db.fetchall('users', ('user_id', 'notifications', 'subgroup', 'preferences'))
    subscribers = []
    for user in data:
        if user['notifications'] == 1 and user['preferences'] == verification_time:
            subscribers.append(user)

    receivers = []
    for sub in subscribers:
        schedulejs = json.loads(db.get('users', 'schedule_cur_week', 'user_id', sub['user_id']))
        flag = True
        copied_schedulejs = []
        for ind, day in enumerate(schedulejs):
            copied_schedulejs.append({'weekday': day['weekday'],
                                      'date': day['date'],
                                      'lessons': []})
            for lesson in day['lessons']:
                for group_number in lesson['groupNumber'].split(', '):
                    if group_number == sub['subgroup']:
                        flag = False
                        copied_schedulejs[ind]['lessons'].append(lesson)
                    elif group_number == '':
                        copied_schedulejs[ind]['lessons'].append(lesson)

        if not len(copied_schedulejs) > 0:
            continue
        elif flag:
            copied_schedulejs = schedulejs

        for day in copied_schedulejs:
            if day['weekday'] == cur_day:
                for lesson in day['lessons']:

                    if lesson['number'] == str(cur_lesson):
                        group_number = ''
                        if flag and lesson['groupNumber'] != '':
                            group_number = ' у ' +lesson['groupNumber'] + '-й подгруппы, '
                        message = ''.join("Сейчас начнется "+lesson['number']+
                                          " пара - "+lesson['lessonName']+
                                          ", "+lesson['lessonType']+
                                          group_number+
                                          " у "+lesson['teacherName']+
                                          " в "+lesson['audName']+" ауд.")
                        receivers.append({'user_id':sub['user_id'], 'message':message})
    return receivers

def start_background_eventloop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def send_message_to_users(cur_lesson=3):
    receivers = prepare_receivers(cur_lesson)
    for user in receivers:
        await bot.send_message(user['user_id'], user['message'])

async def run_continuous(interval=1):
    while True:
        schedule.run_pending()
        await asyncio.sleep(interval)

def prepare_to_sending_notification(lesson_num):
    task_send = asyncio.create_task(send_message_to_users(lesson_num))

def schedule_for_tasks():

    # Присылать уведомления о начале пары
    bell_schedule = SC._get_schedule_bell_ncfu()
    for num, lesson in bell_schedule.items():
        if num.isdigit():
            time_lesson = lesson.split()[0].split(':')
            for appr_time in reversed(range(0, 61)):

                hour, minute = _sub_correctly(time_lesson, appr_time)

                res = [str(hour), str(minute)]

                for ind, time_iter in enumerate(res):
                    if len(time_iter) <= 1:
                        res[ind] = '0'*(2-len(time_iter))+time_iter
                lesson_start = res[0]+':'+res[-1]
                schedule.every().day.at(lesson_start).do(prepare_to_sending_notification, num)
    # Обновить расписание хранящиеся в БД
    schedule.every().sunday.at("00:00:00").do(update_schedules_users)

    # Обновить коды университета
    schedule.every(4).weeks.do(db.insert_codes)
    pprint(schedule.jobs)


def _sub_correctly(time_lesson, requested_subtraction):
    requsted_time = int(time_lesson[-1]) - requested_subtraction
    if requsted_time < 0:
        hour, minute = int(time_lesson[0])-1, 60 - abs(requsted_time)
    else:
        hour, minute = int(time_lesson[0]), requsted_time
    return hour, minute


def _main():
    loop = asyncio.new_event_loop()
    schedule_for_tasks()
    off_thread = threading.Thread(
            target=start_background_eventloop, args=(loop,),
            name='schedule_thread',
            daemon=True,
    ).start()
    asyncio.run_coroutine_threadsafe(run_continuous(), loop)

if __name__ == '__main__':
    _main()
