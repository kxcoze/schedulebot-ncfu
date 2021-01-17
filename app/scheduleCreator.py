import requests
import json
import csv
import time
from typing import List
from datetime import datetime

from bs4 import BeautifulSoup as BS4
from selenium import webdriver


import db


# Used for parsing data from html code
class Parser:
    def post_url(self, url: str, req):
        r = requests.post(url, json=req)
        return r.json()

    def get_html(self, url: str):
        r = requests.get(url)
        return r.text

    def get_schedule(self, html: str):
        soup = BS4(html, 'lxml')
        table = soup.find(
                'table',
                class_='table table-hover lesson-schedule'
        ).find('tbody').find_all('tr')
        schedule_data = []
        ind = -1
        for item in table:
            if item.find('th') is not None:
                days = item.find_all('span')
                weekday = days[0].text
                date = days[1].text
                schedule_data.append({'weekday': weekday,
                                      'date': date,
                                      'lessons': []})
                ind += 1
            elif item is not None and ind != -1:
                stats = item.find_all('td')
                number = ', '.join((
                        stats[0].find('div').text.strip(),
                        stats[0].find('div')['title'],
                ))
                lessonName = stats[1].text
                audName = stats[2].text.strip().replace('\n', '')
                lessonType = stats[3].text
                groupNumber = stats[4].find('span').text \
                    .replace('(', '').replace(')', '')

                teacherName = stats[5].find('a').text
                lesson = {'number': number,
                          'lessonName': lessonName,
                          'audName': audName,
                          'lessonType': lessonType,
                          'groupNumber': groupNumber,
                          'teacherName': teacherName}
                schedule_data[ind]['lessons'].append(lesson)

        return schedule_data


# Used for parsing pages with JS
class SelParser:
    def __init__(self, url):
        self.URL = url

    def get_jshtml(self):
        options = webdriver.FirefoxOptions()
        # options.add_argument('--headless')
        browser = webdriver.Firefox(options=options)
        browser.get(self.URL)
        html = browser.page_source
        browser.quit()

        return html

    def get_schedule_html(self):
        options = webdriver.FirefoxOptions()
        # options.add_argument('--headless')
        browser = webdriver.Firefox(options=options)
        browser.get(self.URL)
        elements = browser.find_elements_by_class_name('item')
        cur_week_html = browser.page_source
        index_to_click = -1
        for index, element in enumerate(elements):
            if 'selected' in element.get_attribute('class'):
                index_to_click = index + 1
                break
        time.sleep(1)
        elements[index_to_click].click()
        next_week_html = browser.page_source
        browser.quit()
        return cur_week_html, next_week_html


# Used for writiting in files
class WriterInFiles:
    def write_in_txt(self, data: str, filename='schedule.txt'):
        with open(filename, 'w') as f:
            f.write(data)

    def write_in_csv(self, rec_data, data: List, filename='nfcu_schedule.csv'):
        with open(filename, 'a+') as f:
            writer = csv.writer(f)
            for i in rec_data:
                writer.writerow((i['instituteName'],
                                 data['instituteId'],
                                 i['Name'],
                                 data['branchId']))

    def write_in_json(self, data: List, filename='ncfu_schedule.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)


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
    # pprint.pprint(data)
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
    except db.sqlite3.IntegrityError:
        db.update(
                'users',
                (('group_code', group_code),
                 ('subgroup', group_subnum),
                 ('schedule_cur_week', schedule_weeks[0]),
                 ('schedule_next_week', schedule_weeks[1])),
                'user_id', user_id,
        )


def get_formatted_schedule(user_id, range, requested_week='cur'):
    schedulejs = json.loads(
            db.get('users', f'schedule_{requested_week}_week', 'user_id', user_id))

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
        weekday = ' '.join(_format_rus_words([week_to_work, date_to_operate.lower()])).strip()
        if date_to_operate == 'Воскресенье':
            return (f"<b><em>Вы запросили расписание на {weekday}, "
                    "может быть стоит отдохнуть?</em></b>")

    if range != 'week':
        schedulejs = [x for x in schedulejs if x['weekday'] == date_to_operate]

    flag = True
    copied_schedulejs = []
    user_subgroup = db.get('users', 'subgroup', 'user_id', user_id)
    for ind, day in enumerate(schedulejs):
        copied_schedulejs.append({'weekday': day['weekday'],
                                  'date': day['date'],
                                  'lessons': []})
        for lesson in day['lessons']:
            for group_number in lesson['groupNumber'].split(', '):
                if group_number == user_subgroup:
                    flag = False
                    copied_schedulejs[ind]['lessons'].append(lesson)
                elif group_number == '':
                    copied_schedulejs[ind]['lessons'].append(lesson)

    if not len(copied_schedulejs) > 0:
        return f"<b><em>На {weekday} доступного расписания нет!</em></b>"
    elif flag:
        copied_schedulejs = schedulejs

    formatted_schedule = f'<b><em>Расписание занятий на {weekday}</em></b>\n\n'
    for day in copied_schedulejs:
        formatted_schedule += ''.join(
                '<b>'+day['weekday']+', '+day['date']+'</b>\n')

        for lesson in day['lessons']:
            numb_para, time_para = lesson['number'].split(', ')

            groupNumber = ''
            if flag and lesson['groupNumber'] != '':
                groupNumber = lesson['groupNumber']+'-я подгруппа, '

            eod = '\n\n'
            if lesson == day['lessons'][-1]:
                eod = '\n\n\n'

            audName = lesson['audName']

            lessonType = ', '
            if len(lesson['lessonType'].split()) > 1:
                lessonT = lesson['lessonType'].split()
                for i in lessonT:
                    lessonType += i[0].upper()
            else:
                lessonType += lesson['lessonType'].strip()

            formatted_schedule += ''.join(
                    numb_para
                    + ' <em>('+time_para+')</em>\n'
                    + lesson['lessonName']
                    + ', '+audName
                    + lessonType+', '
                    + groupNumber
                    + lesson['teacherName']+eod
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


def main():
    # url = 'https://ecampus.ncfu.ru/schedule/group/14904'
    # parser = SelParser(url)
    # parser.get_schedule_html()
    # pprint(get_json_schedule(14904), indent=6)
    # print(get_every_aliases_days_week())
    print(_get_schedule_bell_ncfu()['3'])


if __name__ == '__main__':
    #
    # get_formatted_schedule(input(), input())
    main()
