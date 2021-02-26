import json
import logging
from typing import List
from datetime import datetime
from sqlite3 import IntegrityError

import db
from scraper import SelParser, Parser

log = logging.getLogger('app_logger')


def get_json_schedule(code_group):
    url = f'https://ecampus.ncfu.ru/schedule/group/{code_group}'

    jsParser = SelParser(url)
    html = jsParser.get_jshtml()

    parser = Parser()
    schedule = parser.get_schedule(html)

    js = json.dumps(schedule, ensure_ascii=False)
    return js


def get_two_weeks_schedule(code_group):
    url = f'https://ecampus.ncfu.ru/schedule/group/{code_group}'

    scraper = SelParser(url)
    weeks_html = scraper.get_schedule_html()

    parser = Parser()
    # data[0] - текущая неделя, data[1] - следующая неделя
    data = ['', '']
    for ind, week in enumerate(weeks_html):
        data[ind] = json.dumps(parser.get_schedule(week), ensure_ascii=False)
    return data[0], data[1]


# Возможно следует поместить данную функцию в другой скрипт
def update_schedule_user(user_id, group_code, group_subnum):
    schedule_weeks = get_two_weeks_schedule(group_code)
    try:
        db.insert_new_user(
                user_id,
                group_code=group_code,
                group_subnum=group_subnum,
                schedule_cur_week=schedule_weeks[0],
                schedule_next_week=schedule_weeks[1],
        )
        log.info(f'ID:[{user_id}] schedule successful added in db->users')
    except IntegrityError:
        db.update(
                'users',
                (('group_code', group_code),
                 ('subgroup', group_subnum),
                 ('schedule_cur_week', schedule_weeks[0]),
                 ('schedule_next_week', schedule_weeks[1])),
                'user_id', user_id,
        )
        log.info(f'ID:[{user_id}] schedule successful updated db->users')


def get_formatted_schedule(user_id, range, requested_week='cur'):
    data_dict = db.fetchall(
        'users',
        (f'schedule_{requested_week}_week', 'subgroup', 'preferences'),
        f"WHERE user_id={user_id}"
    )[0]
    schedulejs = json.loads(data_dict[f'schedule_{requested_week}_week'])
    user_subgroup = data_dict['subgroup']
    user_foreign_lang = json.loads(data_dict['preferences'])['foreign_lan']

    today = datetime.today().isoweekday()-1
    tom = 0 if today + 1 > 6 else today + 1
    date_dict = {'today': today, 'tommorow': tom, 'week': -1}
    date_dict.update(_get_eng_days_week())

    days_week = {
                -1: 'Неделя',
                0: 'Понедельник',
                1: 'Вторник',
                2: 'Среда',
                3: 'Четверг',
                4: 'Пятница',
                5: 'Суббота',
                6: 'Воскресенье'}

    for key in date_dict.keys():
        if range in key:
            range = key
            break

    date_to_operate = days_week[date_dict[range]]

    if range == 'today':
        weekday = 'сегодня'
    elif range == 'tommorow':
        weekday = 'завтра'
    else:
        week_to_work = '' if requested_week == 'cur' else 'следующий'
        weekday = ' '.join(_format_rus_words(
            [week_to_work, date_to_operate.lower()])).strip()
        if date_to_operate == 'Воскресенье':
            return (f"<b><em>Вы запросили расписание на {weekday}, "
                    "может быть стоит отдохнуть?</em></b>")

    if range != 'week':
        schedulejs = [x for x in schedulejs if x['weekday'] == date_to_operate]

    if not len(schedulejs) > 0:
        return f"<b><em>На {weekday} доступного расписания нет!</em></b>"

    formatted_schedule = f'<b><em>Расписание занятий на {weekday}</em></b>\n'
    for day in schedulejs:
        formatted_schedule += f"\n<b>{day['weekday']}, {day['date']}</b>\n"

        for lesson in day['lessons']:
            if user_subgroup != '0' and \
                    user_subgroup not in lesson['groupNumber'] and \
                    lesson['groupNumber'] != '':
                continue
            elif 'Иностранный язык в' in lesson['lessonName'] and \
                    user_foreign_lang not in lesson['lessonName']:
                continue
            numb_para, time_para = lesson['number'].split(', ')

            audName = lesson['audName']

            lessonType = ', '
            if len(lesson['lessonType'].split()) > 1:
                lessonT = lesson['lessonType'].split()
                for str in lessonT:
                    lessonType += str[0].upper()
            else:
                lessonType += lesson['lessonType'].strip()

            groupNumber = ''
            if user_subgroup == '0' and lesson['groupNumber'] != '':
                groupNumber = f"{lesson['groupNumber']}-я подгруппа, "

            formatted_schedule += (
                    f"{numb_para} "
                    f"<em>({time_para})</em>\n"
                    f"{lesson['lessonName']}, "
                    f"{audName}"
                    f"{lessonType}, "
                    f"{groupNumber}"
                    f"{lesson['teacherName']}\n\n"
            )

    return formatted_schedule


def get_formatted_schedule_bell():
    bell = _get_schedule_bell_ncfu()
    formatted_bell = '<b><em>Расписание звонков СКФУ</em></b>\n'

    for k, v in bell.items():
        if not k.isdigit():
            formatted_bell += k.split(',')[0] + ' \t'
        else:
            formatted_bell += k + ' пара \t\t\t'
        formatted_bell += v + '\n'

    return formatted_bell


def get_every_aliases_days_week() -> [List, List]:
    fweekdays = list(_get_eng_days_week().keys())
    result = fweekdays.copy()
    second_result = []
    for item in fweekdays:
        result.append(item[:3])
        if item.startswith('t'):
            result.append(item[1:])
            second_result.append(item[1:3])

    return result, second_result


def _format_rus_words(words):
    vowels = {'я': 'ю', 'а': 'у'}
    checked = words[-1][-1]
    if checked in vowels.keys():
        words[-1] = words[-1][:-1] + vowels[checked]
        words[-2] = words[-2][:-2] + 'ую' if len(words[-2]) > 0 else ''
    elif checked == 'е':
        words[-2] = words[-2][:-2] + 'ее' if len(words[-2]) > 0 else ''

    return words


def _get_eng_days_week():
    weekdays = {
            'week': -1,
            'monday': 0,
            'tuesday': 1,
            'wednesday': 2,
            'thursday': 3,
            'friday': 4,
            'saturday': 5,
            'sunday': 6,
    }
    return weekdays


def _get_schedule_bell_ncfu():
    bell = {'1': '8:00 - 9:30',
            '2': '9:40 - 11:10',
            '3': '11:20 - 12:50',
            'Большая перемена, 30 минут': '12:50 - 13:20',
            '4': '13:20 - 14:50',
            '5': '15:00 - 16:30',
            'Большая перемена, 20 минут': '16:30 - 16:50',
            '6': '16:50 - 18:20',
            '7': '18:30 - 20:00',
            '8': '20:10 - 21:40'}
    return bell


def _get_meaning_of_preferences():
    meaning = {'all': "Очный/ВКС", 'full-time': 'Очный', 'distant': 'ВКС'}
    return meaning
