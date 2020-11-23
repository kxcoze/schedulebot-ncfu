from bs4 import BeautifulSoup as BS4
from selenium import webdriver
from typing import List
import requests
import json
import csv

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
        options.add_argument('--headless')
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

def get_formatted_schedule(code_group):
    url = 'https://ecampus.ncfu.ru/schedule/group/' + code_group
    parser = Parser()
    jsParser = SelParser(url)
    html = jsParser.get_data_from_url()
    schedule = parser.get_schedule(html)
    formatted_schedule = ''
    for day in schedule:
        formatted_schedule += ''.join(day['weekday']+', '+day['date']+'\n')
        for lesson in day['lessons']:
            groupNumber = ''
            if lesson['groupNumber'] != '':
                groupNumber = lesson['groupNumber']+', '
            
            eof = '\n'
            if lesson == day['lessons'][-1]:
                eof = '\n\n'
            formatted_schedule += ''.join(lesson['number']+', '+lesson['lessonName']+', '
                                    +lesson['lessonType']+', '+groupNumber
                                    +lesson['teacherName']+eof)
    #print(formatted_schedule)
    writer = WriterInFiles()
    writer.write_in_txt(formatted_schedule)
    return formatted_schedule

if __name__ == '__main__':
    get_formatted_schedule(input())
