from bs4 import BeautifulSoup as BS4
from selenium import webdriver
from typing import List

import threading
import asyncio
import requests
import json
import csv

from datetime import datetime

import db

# Used for parsing data from html code
class Parser:
    def post_url(self, url:str, req):
        r = requests.post(url, json=req)
        return r.json()

    def get_html(self, url:str):
        r = requests.get(url)
        return r.text
        
    def get_schedule(self, html:str):
        soup = BS4(html, 'lxml')
        table = soup.find('table', class_ = 'table table-hover lesson-schedule').find('tbody').find_all('tr')
        schedule_data = []
        ind = -1
        for item in table:
            if item.find('th') != None:
                days = item.find_all('span')
                weekday = days[0].text
                date = days[1].text
                schedule_data.append({'weekday': weekday, 
                                      'date': date,
                                      'lessons': []})
                ind += 1
            elif item != None and ind != -1: 
                stats = item.find_all('td')
                number = stats[0].find('span').text
                lessonName = stats[1].text
                audName = stats[2].text.strip().replace('\n', '')
                lessonType = stats[3].text
                groupNumber = stats[4].find('span').text.replace('(', '').replace(')','')
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
    
    def get_data_from_url(self):
        options = webdriver.FirefoxOptions()
        #options.add_argument('--headless')
        browser = webdriver.Firefox(options=options)
        browser.get(self.URL)
        html = browser.page_source
        browser.quit()
        
        return html

# Used for writiting in files
class WriterInFiles:
    def write_in_txt(self, data:str, filename='schedule.txt'):
        with open(filename, 'w') as f:
            f.write(data)
    
    def write_in_csv(self, rec_data, data:List, filename='nfcu_schedule.csv'):
        with open(filename, 'a+') as f:
            writer = csv.writer(f)
            #writer.writerow(('instituteName', 'instituteId', 'specialty', 'branchId'))
            for i in rec_data:
                writer.writerow((i['instituteName'], 
                                 data['instituteId'], 
                                 i['Name'], 
                                 data['branchId']))

    def write_in_json(self, data:List, filename='ncfu_schedule.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def insert_db_json_schedule(code_group):
    url = f'https://ecampus.ncfu.ru/schedule/group/{code_group}'

    jsParser = SelParser(url)
    html = jsParser.get_data_from_url()

    parser = Parser()
    schedule = parser.get_schedule(html)

    js = json.dumps(schedule, ensure_ascii=False)
    return js

def update_schedule_user(user_id, group_code, group_subnum):
    schedule = insert_db_json_schedule(group_code)
    try:    
        db.insert('users', user_id, group_code, group_subnum, 0, schedule)    
    except db.sqlite3.IntegrityError:    
        db.update('users', [['group_code', group_code],                  
                            ['schedule', schedule],     
                            ['subgroup', group_subnum]], 'user_id', user_id) 


def get_formatted_schedule(user_id, range):
    schedulejs = json.loads(db.get('users', 'schedule', 'user_id', user_id))
    today = datetime.today().isoweekday()-1
    tom = 0 if today + 1 > 6 else today + 1
    date_dict = {'today': today, 'tommorow': tom, 'week': -1}
    weekdays = {-1: 'Неделя',
                0 : 'Понедельник',
                1 : 'Вторник',
                2 : 'Среда',
                3 : 'Четверг',
                4 : 'Пятница',
                5 : 'Суббота',
                6 : 'Воскресенье'}
    date_to_operate = weekdays[date_dict[range]]

    if date_to_operate == 'Воскресенье':
        return "<b><em>Вы запросили расписание на воскресенье, может быть стоит отдохнуть?</em></b>"
    elif range == 'week':
        weekday = 'неделю'
    elif range == 'today':
        weekday = 'сегодня'
        schedulejs = [x for x in schedulejs if x['weekday'] == date_to_operate]
    elif range == 'tommorow':
        weekday = 'завтра'
        schedulejs = [x for x in schedulejs if x['weekday'] == date_to_operate]



    user_subgroup = db.get('users', 'subgroup', 'user_id', user_id)
    flag = True
    copied_schedulejs = []
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
        return f"<b><em>На {weekday} доступного расписания нету!</em></b>"
    elif flag:
        copied_schedulejs = schedulejs

    schedule_bell = _get_schedule_bell_ncfu()
    formatted_schedule = f'<b><em>Расписание занятий на {weekday}</em></b>\n\n'
    for day in copied_schedulejs:
        formatted_schedule += ''.join('<b>'+day['weekday']+', '+day['date']+'</b>\n')
        for lesson in day['lessons']:
            groupNumber = ''
            if flag and lesson['groupNumber'] != '':
                groupNumber = lesson['groupNumber']+'-я подгруппа, '

            eod = '\n\n'
            if lesson == day['lessons'][-1]:
                eod = '\n\n\n'
            
            lessonType = ', '
            if lesson['lessonType'] != 'Лекция':
                lessonT = lesson['lessonType'].split()
                for i in lessonT:
                    lessonType += i[0].upper()
            else:
                lessonType = ''

            formatted_schedule += ''.join(lesson['number']+' пара '+'<em>('+schedule_bell[lesson['number']]+')</em>\n'
                                    +lesson['lessonName']
                                    +', '+lesson['audName']
                                    +lessonType+', '
                                    +groupNumber
                                    +lesson['teacherName']+eod)
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

if __name__ == '__main__':
    #get_json_schedule(input())
    #get_formatted_schedule(input(), input())
    print(get_formatted_schedule_bell())
