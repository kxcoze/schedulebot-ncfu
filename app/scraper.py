import os
import time
import subprocess
import logging

import requests
from bs4 import BeautifulSoup as BS4
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH')
# GECKODRIVER_PATH = os.getenv('GECKODRIVER_PATH')
log = logging.getLogger('app_logger')


class SelScrapingSchedule:

    html = ''

    def restart_script(self, browser):
        """Перезапуск скрипта"""

        # Выход из браузера в случае рестарта скрипта
        browser.quit()
        log.warning("Restarting script...")
        return

    def check_connection(self):
        """Проверка наличия интернета"""
        # Можно сделать лучше!
        # Данная функция проверяет наличие интернета, а не скорость соединения,
        # поэтому необходимо переделать в скором времени.
        try:
            subprocess.check_call(["ping", "-c 1", "www.google.ru"])
            log.warning("Connection is good.")
            return True
        except subprocess.CalledProcessError:
            log.warning("Connection is broken.")
            return False

    def get_html_from_schedule(self):
        """Прокликиваем все доступные институты и специальности
           ради получения ссылок на группы, возвращаем html-документ
           страницы в переменную класса html"""
        url = 'https://ecampus.ncfu.ru/schedule'
        log.info(f'Initialize getting all specialities from {url}')
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument('--headless')
            browser = webdriver.Firefox(options=options)
            # browser = webdriver.Firefox(
            #     executable_path=GECKODRIVER_PATH, options=options)
            browser.get(url)
        except:
            self.restart_script(browser)
            return

        XPATH_to_institutes = (
            "//div[@id='page']/div[@id='select-group']"
            "/div[@class='col-lg-7 col-md-6']"
            "/div[@id='institutes']"
            "/div[@class='panel panel-default']"
        )

        XPATH_to_specialities = ''.join((
            XPATH_to_institutes,
            ("/div[@class='panel-collapse collapse in']"
             "/div[@class='panel-body']"
             "/div[@class='panel-group specialities']"
             "/div[@class='panel panel-default']")))

        try:
            institutes = WebDriverWait(browser, 30).until(
                    EC.presence_of_all_elements_located((
                        By.XPATH, XPATH_to_institutes))
            )
        except:
            log.exception("Cannot load list of institutes!\n"
                          "Please reload the script!")
            self.restart_script(browser)
        else:
            wait = WebDriverWait(browser, 10)
            for item in institutes:
                try:
                    wait.until(
                            EC.element_to_be_clickable((
                                By.XPATH,
                                XPATH_to_institutes))
                    )
                    item.click()
                    log.info(f'Successful clicked on this: {item}')
                    specialities = wait.until(
                                EC.presence_of_all_elements_located((
                                    By.XPATH,
                                    XPATH_to_specialities))
                    )
                    for speciality in specialities:
                        try:
                            wait.until(
                                    EC.element_to_be_clickable((
                                        By.XPATH,
                                        XPATH_to_specialities))
                            )
                            speciality.click()
                            log.info(f'Successful clicked on this: {speciality}')
                        except:
                            log.exception("Cannot load list of groups!")
                            # Если беда с подключением перезапускаем скрипт, иначе продолжаем
                            if not self.check_connection():
                                self.restart_script(browser)
                                return

                except:
                    log.exception("Cannot load list of specialities!")
                    # Если беда с подключением перезапускаем скрипт, иначе продолжаем
                    if not self.check_connection():
                        self.restart_script(browser)
                        return

            self.html = browser.page_source
            time.sleep(5)
        finally:
            browser.quit()


class ParserSchedule:
    def __init__(self, html):
        self.html = html

    def get_data(self):
        soup = BS4(self.html, 'lxml')
        institutes = soup.find('div', id='institutes') \
            .find_all('div', class_='panel panel-default', recursive=False)

        data_from_schedule = []
        for institute in institutes:
            instituteName = institute.find('div', class_='panel-heading') \
                .find('span').text.strip()
            data_instit = {'instituteName': instituteName, 'specialities': []}

            specialities = institute.find(
                    'div', class_='panel-group specialities').find_all(
                                'div',
                                class_='panel panel-default',
                                recursive=False
                                )
            for speciality in specialities:
                specialityName = speciality.find(
                        'div', class_='panel-heading') \
                            .find('span').text.strip()
                data_specialities = {
                        'specialityName': specialityName,
                        'groups': [],
                }

                list_group = speciality.find('ul', class_='list-group') \
                    .find_all('a')
                for group in list_group:
                    groupName = group.find('span').text
                    groupCode = group.get('href').split('/')[-1]

                    data_groups = {
                            'groupName': groupName,
                            'groupCode': groupCode,
                    }

                    data_specialities['groups'].append(data_groups)
                data_instit['specialities'].append(data_specialities)
            data_from_schedule.append(data_instit)

        return data_from_schedule


# Used for parsing pages with JS
class SelParser:
    def __init__(self, url):
        self.URL = url

    def get_jshtml(self):
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        browser = webdriver.Firefox(options=options)
        # browser = webdriver.Firefox(
        #     executable_path=GECKODRIVER_PATH, options=options)
        html = ''
        try:
            browser.get(self.URL)
            html = browser.page_source
        finally:
            browser.quit()

        return html

    def get_schedule_html(self):
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        browser = webdriver.Firefox(options=options)
        # browser = webdriver.Firefox(
        #     executable_path=GECKODRIVER_PATH, options=options)
        browser.get(self.URL)
        cur_week_html, next_week_html = '', ''
        try:
            elements = browser.find_elements_by_class_name('item')
            cur_week_html = browser.page_source
            index_to_click = -1
            for index, element in enumerate(elements):
                if 'selected' in element.get_attribute('class'):
                    index_to_click = index + 1
                    break
            time.sleep(0.25)
            elements[index_to_click].click()
            time.sleep(0.25)
            next_week_html = browser.page_source
        except:
            log.exception('Something went wrong in headless browser!')
        finally:
            browser.quit()

        return cur_week_html, next_week_html


# Used for parsing data from html code
class Parser:

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


def get_codes():
    schedule = SelScrapingSchedule()
    while not schedule.html:
        schedule.get_html_from_schedule()

    parser = ParserSchedule(schedule.html)

    return parser.get_data()
