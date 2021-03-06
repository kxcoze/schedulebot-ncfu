import os
import threading
import json
import asyncio
import logging
from pprint import pprint
from datetime import datetime, timedelta

import schedule
from aiogram import Bot
from aiogram.utils import exceptions

import db
from schedulecreator import update_schedule_user, _get_schedule_bell_ncfu


bot = Bot(token=os.getenv('API_TOKEN'))
log = logging.getLogger('app_logger')


def update_schedules_users():
    data = db.fetchall('users', ('user_id', 'group_code', 'subgroup'))
    for user in data:
        try:
            update_schedule_user(
                user['user_id'], user['group_code'], user['subgroup'])
            log.info(f"ID:{user['user_id']} schedule successful updated")
        except:
            log.exception(f"ID:{user['user_id']} failed to update schedule")


def prepare_receivers(cur_lesson):
    receivers = []
    cur_weekday = datetime.today().weekday()
    if cur_weekday == 6:
        return receivers

    weekdays = {
        0: 'Понедельник',
        1: 'Вторник',
        2: 'Среда',
        3: 'Четверг',
        4: 'Пятница',
        5: 'Суббота',
    }

    time_lesson_start = _get_schedule_bell_ncfu()[cur_lesson] \
        .split(' - ')[0].split(':')

    cur_string_day = weekdays[cur_weekday]
    now = datetime.now()
    lesson_start = now.replace(
        hour=int(time_lesson_start[0]), minute=int(time_lesson_start[-1]))

    verification_time = (lesson_start - now).seconds // 60
    data = db.fetchall(
        'users', ('user_id', 'notifications', 'subgroup', 'preferences'))

    subscribers = []
    for user in data:
        pref_time = int(json.loads(user['preferences'])['pref_time'])
        if user['notifications'] == 1 and pref_time == verification_time:
            subscribers.append(user)

    for sub in subscribers:
        schedulejs = json.loads(
            db.get('users', 'schedule_cur_week', 'user_id', sub['user_id']))

        searched_lessons = []
        sub_prefs = json.loads(sub['preferences'])
        for day in schedulejs:
            lesson_day = int(day['date'].split(' ')[0])
            cur_day = datetime.today().day
            if day['weekday'] == cur_string_day and lesson_day == cur_day:
                for lesson in day['lessons']:
                    if lesson['number'][0] == cur_lesson and \
                            (lesson['groupNumber'] == '' or \
                            sub['subgroup'] == '0' or \
                            sub['subgroup'] in lesson['groupNumber']) and \
                            (sub_prefs['notification_type'] == 'all' or \
                            lesson['audName'] not in 'ВКС/ЭТ' and \
                            sub_prefs['notification_type'] == 'full-time' or \
                            lesson['audName'] in 'ВКС/ЭТ' and \
                            sub_prefs['notification_type'] == 'distant') and \
                            ('Иностранный язык в' not in lesson['lessonName'] or \
                            sub_prefs['foreign_lan'] in lesson['lessonName']):
                        searched_lessons.append(lesson)

        if not searched_lessons:
            continue

        start = ''
        if verification_time == 60:
            start = 'Через час'
        elif verification_time == 0:
            start = 'Сейчас'
        else:
            start = f'Через {verification_time} мин.'

        message = f"{start} начнётся {cur_lesson} пара:\n"
        for searched_lesson in searched_lessons[::-1]:
            if searched_lesson['audName'] in 'ВКС/ЭТ':
                audName = ''
            else:
                audName = f"Аудитория: {searched_lesson['audName']}\n"

            group_number = ''
            if sub['subgroup'] == '0' and searched_lesson['groupNumber'] != '':
                group_number = f"Подгруппа: №{searched_lesson['groupNumber']}\n"

            lessonType = ''
            if searched_lesson['lessonType'] != searched_lesson['lessonName']:
                lessonType = f"{searched_lesson['lessonType']}\n"

            links = json.loads(
                db.get('users', 'links', 'user_id', sub['user_id']))
            searched_link = ''
            for link in links:
                # Может реализовать по совпадениям?
                link_data = link[0].lower()
                lesson_name = searched_lesson['lessonName'].lower()
                lesson_teacher = searched_lesson['teacherName'].lower()
                initials = lesson_teacher.split(' ')
                initials = ' '.join((
                    initials[0], initials[1][0]+'.', initials[2][0]+'.')).lower()
                if link_data == lesson_name or \
                        link_data == lesson_teacher or \
                        link_data == initials:
                    searched_link = f'\nСсылка на пару: {link[-1]}'
                    break

            message += (
                f"{group_number}"
                f"{searched_lesson['lessonName']}\n"
                f"{lessonType}"
                f"Преподаватель: {searched_lesson['teacherName']}\n"
                f"{audName}"
                f"{searched_link}\n\n"
            )
        receivers.append({'user_id': sub['user_id'], 'message': message})

    return receivers


def start_background_eventloop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


async def send_message(user_id: int,
                       text: str,
                       disable_notification: bool = False) -> bool:
    try:
        await bot.send_message(
            user_id, text, disable_notification=disable_notification)
    except exceptions.BotBlocked:
        log.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        log.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        log.error(
            f"Target [ID:{user_id}]: Flood limit is exceeded."
            "Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await send_message(user_id, text)  # Recursive call
    except exceptions.UserDeactivated:
        log.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        log.exception(f"Target [ID:{user_id}]: failed")
    else:
        log.info(f"Target [ID:{user_id}]: success")
        return True
    return False


async def send_message_to_users(cur_lesson=1):
    receivers = prepare_receivers(cur_lesson)
    count = 0
    if receivers:
        try:
            for user in receivers:
                if await send_message(user['user_id'], user['message']):
                    count += 1
                # 20 messages per second (Limit: 30 messages per second)
                await asyncio.sleep(.05)
        finally:
            log.info(f"{count} messages successful sent.")
    else:
        log.info('No users to send message.')


async def run_continuous(interval=1):
    while True:
        schedule.run_pending()
        await asyncio.sleep(interval)


def prepare_to_sending_notification(lesson_num):
    asyncio.create_task(send_message_to_users(lesson_num))


def planning_tasks():
    # Присылать уведомления о начале пары
    bell_schedule = _get_schedule_bell_ncfu()
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
    schedule.every(10).weeks.do(db.insert_codes)


def init_taskmanager():
    loop = asyncio.new_event_loop()
    planning_tasks()
    threading.Thread(
            target=start_background_eventloop, args=(loop,),
            name='schedule_thread',
            daemon=True,
    ).start()
    asyncio.run_coroutine_threadsafe(run_continuous(), loop)
