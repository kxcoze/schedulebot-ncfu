import threading
import json
import asyncio
from pprint import pprint
from datetime import datetime, timedelta

import schedule
from aiogram import Bot

import db
import scheduleCreator as SC

API_TOKEN = '1458781343:AAEN9-LvDZeOKa3fn738zgDpqVssqFIJ-Ok'

bot = Bot(token=API_TOKEN)


def update_schedules_users():
    data = db.fetchall('users', ('user_id', 'group_code', 'subgroup'))
    for user in data:
        # print(user['user_id'], user['group_code'], user['subgroup'])
        try:
            SC.update_schedule_user(
                user['user_id'], user['group_code'], user['subgroup'])
        except:
            # print("FAILED")
            pass
        # print("SUCCESS")


def prepare_receivers(cur_lesson):
    cur_weekday = datetime.today().weekday()
    if cur_weekday == 6:
        return

    weekdays = {
        0: 'Понедельник',
        1: 'Вторник',
        2: 'Среда',
        3: 'Четверг',
        4: 'Пятница',
        5: 'Суббота',
    }
    time_lesson_start = SC._get_schedule_bell_ncfu()[cur_lesson] \
        .split(' - ')[0].split(':')

    cur_day = weekdays[cur_weekday]
    now = datetime.now()
    lesson_start = now.replace(hour=int(time_lesson_start[0]), minute=int(time_lesson_start[-1]))

    verification_time = (lesson_start - now).seconds // 60
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
                    if lesson['number'][0] == cur_lesson:
                        start = ''
                        if verification_time == 60:
                            start = 'Через час'
                        elif verification_time == 0:
                            start = 'Сейчас'
                        else:
                            start = f'Через {verification_time} минут'

                        group_number = ''
                        if flag and lesson['groupNumber'] != '':
                            group_number = f"Подгруппа: №{lesson['groupNumber']}\n"

                        audName = ''
                        if lesson['audName'] != 'ВКС' and lesson['audName'] != 'ЭТ':
                            audName = f"Аудитория: {lesson['audName']}\n"

                        links = json.loads(
                            db.get('users', 'link', 'user_id', sub['user_id']))
                        searched_link = ''
                        for link in links:
                            # Может реализовать по совпадениям?
                            if link[0] == lesson['lessonName'] or link[0] == lesson['teacherName']:
                                searched_link = f'\nСсылка на пару: {link[-1]}'
                                break

                        message = (
                            f"{start} начнётся {lesson['number'][0]} пара:\n"
                            f"{lesson['lessonName']}\n"
                            f"{lesson['lessonType']}\n"
                            f"{group_number}"
                            f"Преподаватель: {lesson['teacherName']}\n"
                            f"{audName}"
                            f"{searched_link}"
                        )
                        receivers.append(
                            {'user_id': sub['user_id'], 'message': message})
    return receivers


def start_background_eventloop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


async def send_message_to_users(cur_lesson=1):
    receivers = prepare_receivers(cur_lesson)
    for user in receivers:
        await bot.send_message(user['user_id'], user['message'])


async def run_continuous(interval=1):
    while True:
        schedule.run_pending()
        await asyncio.sleep(interval)


def prepare_to_sending_notification(lesson_num):
    asyncio.create_task(send_message_to_users(lesson_num))


def schedule_for_tasks():
    # Присылать уведомления о начале пары
    bell_schedule = SC._get_schedule_bell_ncfu()
    for num, lesson in bell_schedule.items():
        if num.isdigit():
            time_lesson_start = lesson.split()[0].split(':')
            lesson_start = datetime.now().replace(
                hour=int(time_lesson_start[0]),
                minute=int(time_lesson_start[-1]),
            )
            for appr_time in reversed(range(0, 61)):
                appr_lesson_start = lesson_start - timedelta(minutes=appr_time)
                schedule.every().day.at(appr_lesson_start.strftime("%H:%M")).do(
                    prepare_to_sending_notification, num)

    # Обновить расписание хранящиеся в БД
    schedule.every().sunday.at("00:00:00").do(update_schedules_users)

    # Обновить коды университета
    schedule.every(4).weeks.do(db.insert_codes)
    pprint(schedule.jobs)


def _main():
    loop = asyncio.new_event_loop()
    schedule_for_tasks()
    threading.Thread(
            target=start_background_eventloop, args=(loop,),
            name='schedule_thread',
            daemon=True,
    ).start()
    asyncio.run_coroutine_threadsafe(run_continuous(), loop)


if __name__ == '__main__':
    _main()
