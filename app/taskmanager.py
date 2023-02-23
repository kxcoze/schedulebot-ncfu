import threading
import json
import asyncio
import logging
from datetime import datetime, timedelta

import schedule
from aiogram import Bot
from aiogram.utils import exceptions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from scraping.scraper import get_data_from_getschedule, get_codes
from db.models import User, Group
from config import load_config, Config
from helpers import _get_schedule_bell_ncfu
from decorators import add_message_id_in_db_for_group


def init_engine_and_bot():
    config: Config = load_config()
    engine = create_async_engine(
        f"postgresql+asyncpg://{config.db.user}:{config.db.password}@{config.db.host}/{config.db.db_name}",
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
        future=True,
        poolclass=NullPool,
    )

    async_sessionmaker = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    bot = Bot(config.bot.token, parse_mode="HTML")
    bot["db"] = async_sessionmaker
    return bot


@add_message_id_in_db_for_group
async def send_message(
    user_id: int, text: str, disable_notification: bool = False, **kwargs
) -> bool:

    try:
        msg = await bot.send_message(
            user_id, text, disable_notification=disable_notification
        )
    except exceptions.BotBlocked:
        logging.error(f"Target [ID:{user_id}]: blocked by user")
    except exceptions.ChatNotFound:
        logging.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        logging.error(
            f"Target [ID:{user_id}]: Flood limit is exceeded."
            "Sleep {e.timeout} seconds."
        )
        await asyncio.sleep(e.timeout)
        return await send_message(user_id, text)  # Recursive call
    except exceptions.UserDeactivated:
        logging.error(f"Target [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        logging.exception(f"Target [ID:{user_id}]: failed")
    else:
        logging.info(f"Target [ID:{user_id}]: success")
        return msg
    return None


async def update_groups_schedules():
    db_session = bot.get("db")
    async with db_session() as session:
        sql = select(Group).where(Group.schedule_cur_week.is_not(None))
        groups = [group[0] for group in (await session.execute(sql)).fetchall()]
        count = 0
        for group in groups:
            try:
                (
                    group.schedule_cur_week,
                    group.schedule_next_week,
                ) = await get_data_from_getschedule(group.id)
                await session.commit()
                logging.info(f"Name:{group.name} schedule successful updated")
                count += 1
            except:
                logging.exception(f"Name:{group.name} failed to update schedule")
    logging.info(f"{count} schedules has been updated!")


async def prepare_receivers(cur_lesson):
    receivers = []
    cur_weekday = datetime.today().weekday()
    if cur_weekday == 6:
        return receivers

    weekdays = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
    }

    time_lesson_start = _get_schedule_bell_ncfu()[cur_lesson].split(" - ")[0].split(":")

    cur_string_day = weekdays[cur_weekday]
    now = datetime.now()
    lesson_start = now.replace(
        hour=int(time_lesson_start[0]), minute=int(time_lesson_start[-1])
    )

    verification_time = (lesson_start - now).seconds // 60
    db_session = bot.get("db")
    async with db_session() as session:
        sql = select(User).where(
            User.is_notified == True,
            User.group_id.is_not(None),
            User.pref_time == verification_time,
        )
        users = [user[0] for user in (await session.execute(sql)).fetchall()]

        users_group_id = set([user.group_id for user in users])
        sql = select(Group.id, Group.schedule_cur_week).where(
            Group.id.in_(users_group_id), Group.schedule_cur_week.is_not(None)
        )
        dict_id_schedule = dict((await session.execute(sql)).fetchall())

    for user in users:
        searched_lessons = []
        schedule = dict_id_schedule.get(user.group_id)
        if not schedule:
            continue
        for day in schedule:
            lesson_day = int(day["date"].split(" ")[0])
            cur_day = datetime.today().day
            if day["weekday"] == cur_string_day and lesson_day == cur_day:
                for lesson in day["lessons"]:
                    if (
                        lesson["number"][0] == cur_lesson
                        and (
                            lesson["groupNumber"] == ""
                            or user.subgroup == 0
                            or str(user.subgroup) in lesson["groupNumber"]
                        )
                        and (
                            user.notification_type == "all"
                            or lesson["audName"] not in "ВКС/ЭТ"
                            and user.notification_type == "full-time"
                            or lesson["audName"] in "ВКС/ЭТ"
                            and user.notification_type == "distant"
                        )
                        and (
                            "Иностранный язык в" not in lesson["lessonName"]
                            or user.foreign_lan in lesson["lessonName"]
                        )
                    ):
                        searched_lessons.append(lesson)

        if not searched_lessons:
            continue

        start = ""
        if verification_time == 60:
            start = "Через час"
        elif verification_time == 0:
            start = "Сейчас"
        else:
            start = f"Через {verification_time} мин."

        message = f"{start} начнётся {cur_lesson} пара:\n"
        for searched_lesson in searched_lessons[::-1]:
            if searched_lesson["audName"] in "ВКС/ЭТ":
                audName = ""
            else:
                audName = f"Аудитория: {searched_lesson['audName']}\n"

            group_number = ""
            if user.subgroup == 0 and searched_lesson["groupNumber"] != "":
                group_number = f"Подгруппа: №{searched_lesson['groupNumber']}\n"

            lessonType = ""
            if searched_lesson["lessonType"] != searched_lesson["lessonName"]:
                lessonType = f"{searched_lesson['lessonType']}\n"
            teacherName = ""
            if searched_lesson["teacherName"]:
                teacherName = f"Преподаватель: {searched_lesson['teacherName']}\n"
            # links = json.loads(db.get("users", "links", "user_id", sub["user_id"]))
            links = user.links
            searched_link = ""
            for link in links:
                # Может реализовать по совпадениям?
                link_data = link[0].lower()
                lesson_name = searched_lesson["lessonName"].lower()
                lesson_teacher = searched_lesson["teacherName"].lower()
                initials = lesson_teacher.split(" ")
                initials = " ".join(
                    (initials[0], initials[1][0] + ".", initials[2][0] + ".")
                ).lower()
                if (
                    link_data == lesson_name
                    or link_data == lesson_teacher
                    or link_data == initials
                ):
                    searched_link = f"\nСсылка на пару: {link[-1]}"
                    break

            message += (
                f"{group_number}"
                f"{searched_lesson['lessonName']}\n"
                f"{lessonType}"
                f"{teacherName}"
                f"{audName}"
                f"{searched_link}\n\n"
            )
        receivers.append({"user_id": user.id, "message": message})

    return receivers


async def send_message_to_users(cur_lesson):
    receivers = await prepare_receivers(cur_lesson)
    count = 0
    if receivers:
        for user in receivers:
            msg = await send_message(user["user_id"], user["message"])
            if msg is not None:
                count += 1
            # 20 messages per second (Limit: 30 messages per second)
            await asyncio.sleep(0.05)
        try:
            pass
        finally:
            logging.info(f"{count} messages successful sent.")
    else:
        logging.info("No users to send message.")


async def update_group_codes():
    groups = await get_codes()
    db_session = bot.get("db")
    async with db_session() as session:
        for group in groups:
            try:
                await session.merge(
                    Group(
                        id=group[1],
                        name=group[0],
                    )
                )
                await session.commit()
                logging.info(f"NEW DATA -> {group[0]} with id:{group[1]}")
            except:
                logging.error("Something went wrong when insert codes")
                return
    logging.info(f"Successful updated {len(groups)} groups!")


def prepare_to_sending_notification(lesson_num):
    asyncio.create_task(send_message_to_users(lesson_num))


def prepare_to_update_groups_schedule():
    asyncio.create_task(update_groups_schedules())


def prepare_to_update_group_codes():
    asyncio.create_task(update_group_codes())


def planning_tasks():
    # Присылать уведомления о начале пары
    bell_schedule = _get_schedule_bell_ncfu()
    for num, lesson in bell_schedule.items():
        if num.isdigit():
            time_lesson_start = lesson.split()[0].split(":")
            lesson_start = datetime.now().replace(
                hour=int(time_lesson_start[0]),
                minute=int(time_lesson_start[-1]),
            )
            for appr_time in reversed(range(0, 61)):
                appr_lesson_start = lesson_start - timedelta(minutes=appr_time)
                schedule.every().day.at(appr_lesson_start.strftime("%H:%M")).do(
                    prepare_to_sending_notification,
                    num,
                )

    # Обновить расписание хранящиеся в БД
    schedule.every().sunday.at("00:00:00").do(prepare_to_update_groups_schedule)

    # Обновить коды университета
    schedule.every(10).weeks.do(prepare_to_update_group_codes)


async def run_continuous(interval=1):
    while True:
        schedule.run_pending()
        await asyncio.sleep(interval)


def start_background_eventloop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


def init_taskmanager():
    global bot
    bot = init_engine_and_bot()
    loop = asyncio.new_event_loop()
    planning_tasks()
    threading.Thread(
        target=start_background_eventloop,
        args=(loop,),
        name="schedule_thread",
        daemon=True,
    ).start()
    asyncio.run_coroutine_threadsafe(run_continuous(), loop)
