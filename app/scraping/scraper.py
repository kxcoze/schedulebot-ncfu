import json
import aiohttp
import locale
import logging
from datetime import datetime, timedelta

from scraping.classes import SelScrapingSchedule, ParserSchedule
from helpers import _get_eng_days_week, _format_rus_words

locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")


async def parse_json(json_data, id):
    if not json_data:
        raise ValueError(f"json data for {id} is empty. maybe group schedule is empty?")
    result = []
    for day in json_data:
        weekday = day["WeekDay"]
        date = datetime.fromisoformat(day["Date"]).strftime("%d %B")
        lessons = []
        for lesson in day["Lessons"]:
            number_start = lesson["PairNumberStart"]
            number_end = lesson["PairNumberEnd"]
            lesson_name = lesson["Discipline"]
            lesson_start = datetime.fromisoformat(lesson["TimeBegin"]).strftime("%H:%M")
            lesson_end = datetime.fromisoformat(lesson["TimeEnd"]).strftime("%H:%M")
            lesson_type = lesson["LessonType"].strip()
            aud_name = lesson["Aud"]["Name"]
            teacher_name = lesson.get("Teacher")
            if teacher_name:
                teacher_name = teacher_name["Name"].strip()
            else:
                teacher_name = ""
            group_number = ""
            for group in lesson["Groups"]:
                if int(group["Id"]) == id:
                    group_number = group["Subgroup"]
                    break

            if len(group_number) > 1:
                group_number = ", ".join(sorted(set(group_number[1:-1].split(", "))))
            number = (
                number_start
                if number_start == number_end
                else f"{number_start}-{number_end}"
            )
            lesson_time = f"{lesson_start} - {lesson_end}"
            lessons.append(
                {
                    "number": f"{number} пара, {lesson_time}",
                    "lessonName": lesson_name,
                    "lessonType": lesson_type,
                    "audName": aud_name,
                    "teacherName": teacher_name,
                    "groupNumber": group_number,
                }
            )
        if lessons:
            result.append(
                {
                    "weekday": weekday,
                    "date": date,
                    "lessons": lessons,
                }
            )
    return result


async def get_data_from_getschedule(id):
    url = "https://ecampus.ncfu.ru/schedule/GetSchedule"
    now = datetime.now() + timedelta(days=1)
    monday_cur_week = (
        now - timedelta(days=now.weekday())
    ).strftime("%Y-%m-%d")
    monday_next_week = (
        (now - timedelta(days=now.weekday()))
        + timedelta(days=7)
    ).strftime("%Y-%m-%d")
    async with aiohttp.ClientSession() as session:
        params = {"date": monday_cur_week, "Id": id, "targetType": 2}
        async with session.post(url, params=params) as resp:
            json_cur_week = await resp.json()

        params = {"date": monday_next_week, "Id": id, "targetType": 2}
        async with session.post(url, params=params) as resp:
            json_next_week = await resp.json()
    try:
        json_cur_week = await parse_json(json_cur_week, id)
    except ValueError as e:
        json_cur_week = None
        logging.warning(e)

    try:
        json_next_week = await parse_json(json_next_week, id)
    except ValueError as e:
        json_cur_week = None
        logging.warning(e)
    return json_cur_week, json_next_week


async def get_formatted_schedule(user, group, range, requested_week="cur"):
    schedulejs = getattr(group, f"schedule_{requested_week}_week")
    user_subgroup = str(user.subgroup)
    user_foreign_lang = user.foreign_lan if user.foreign_lan else ""

    today = datetime.today().isoweekday() - 1
    tom = 0 if today + 1 > 6 else today + 1
    date_dict = {"today": today, "tommorow": tom, "week": -1}
    date_dict.update(_get_eng_days_week())

    days_week = {
        -1: "Неделя",
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }

    for key in date_dict.keys():
        if range in key:
            range = key
            break

    date_to_operate = days_week[date_dict[range]]

    if range == "today":
        weekday = "сегодня"
    elif range == "tommorow":
        weekday = "завтра"
    else:
        week_to_work = "" if requested_week == "cur" else "следующий"
        weekday = " ".join(
            _format_rus_words([week_to_work, date_to_operate.lower()])
        ).strip()
        if date_to_operate == "Воскресенье":
            return (
                f"<b><em>Вы запросили расписание на {weekday}, "
                "может быть стоит отдохнуть?</em></b>"
            )

    if range != "week":
        schedulejs = [x for x in schedulejs if x["weekday"] == date_to_operate]

    if not schedulejs:
        return f"<b><em>На {weekday} доступного расписания нет!</em></b>"

    formatted_schedule = f"<b><em>Расписание занятий на {weekday}</em></b>\n"
    for day in schedulejs:
        formatted_schedule += f"\n<b>{day['weekday']}, {day['date']}</b>\n"

        for lesson in day["lessons"]:
            if (
                user_subgroup != "0"
                and user_subgroup not in lesson["groupNumber"]
                and lesson["groupNumber"] != ""
            ):
                continue
            elif (
                "Иностранный язык в" in lesson["lessonName"]
                and user_foreign_lang not in lesson["lessonName"]
            ):
                continue
            numb_para, time_para = lesson["number"].split(", ")

            audName = lesson["audName"]

            lessonType = ", "
            if len(lesson["lessonType"].split()) > 1:
                lessonT = lesson["lessonType"].split()
                for string in lessonT:
                    lessonType += string[0].upper()
            else:
                lessonType += lesson["lessonType"].strip()

            groupNumber = ""
            if user_subgroup == "0" and lesson["groupNumber"] != "":
                groupNumber = f"{lesson['groupNumber']}-я подгруппа, "

            teacherName = ' '.join(lesson['teacherName'].split())
            lessonName = ' '.join(lesson['lessonName'].split())

            formatted_schedule += (
                f"{numb_para} "
                f"<em>({time_para})</em>\n"
                f"{lessonName}, "
                f"{audName}"
                f"{lessonType}, "
                f"{groupNumber}"
                f"{teacherName}\n\n"
            )

    return formatted_schedule


def get_data_from_schedule():
    schedule = SelScrapingSchedule()
    while not schedule.html:
        schedule.get_html_from_schedule()

    parser = ParserSchedule(schedule.html)

    return parser.get_data()


async def get_codes():
    # [0] - Группа, [1] - Код группы
    unparsed_data = get_data_from_schedule()
    result = []
    for item in unparsed_data:
        for speciality in item["specialities"]:
            for group in speciality["groups"]:
                result.append(
                    (group["groupName"].lower(), int(group["groupCode"].lower()))
                )
    return result
