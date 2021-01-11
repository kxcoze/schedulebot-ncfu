import time

import subprocess

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SelScrapingSchedule:

    html = ''

    def restart_script(self, browser):
        """Перезапуск скрипта"""

        # Выход из браузера в случае рестарта скрипта
        browser.quit()
        print("Restarting script...")
        # self.get_html_from_schedul()
        return

    def check_connection(self):
        """Проверка наличия интернета"""
        # Можно сделать лучше! 
        # Данная функция проверяет наличие интернета, а не скорость соединения, 
        # поэтому необходимо переделать в скором времени.
        try:
            subprocess.check_call(["ping", "-c 1", "www.google.com"])
            print("Connection is good.\n")
            return True
        except subprocess.CalledProcessError:
            print("Connection is broken.\n")
            return False

    def get_html_from_schedule(self):
        """Прокликиваем все доступные институты и специальности
           ради получения ссылок на группы, возвращаем html-документ 
           страницы в переменную класса html"""
        try:
            url = 'https://ecampus.ncfu.ru/schedule'
            options = webdriver.FirefoxOptions()
            # options.add_argument('--headless')
            browser = webdriver.Firefox(options=options)
            browser.get(url)
        except:
            self.restart_script(browser)
            return
        # XPATH = /div[@class='panel-collapse collapse in']/div[@class='panel-body']/div[@class='panel-group specialities']/div[@class='panel panel-default']
        XPATH_to_institutes = "//div[@id='page']/div[@id='select-group']/div[@class='col-lg-7 col-md-6']/div[@id='institutes']/div[@class='panel panel-default']"
        
        XPATH_to_specialities = XPATH_to_institutes + "/div[@class='panel-collapse collapse in']/div[@class='panel-body']/div[@class='panel-group specialities']/div[@class='panel panel-default']"
        
        # XPATH_to_groups = XPATH_to_specialities + "/div[@class='panel-collapse collapse in']/div[@class='panel-body']/ul[@class='list-group']/li[@class='list-group-item']"
        try:
            institutes = WebDriverWait(browser, 30).until(
                    EC.presence_of_all_elements_located((By.XPATH, XPATH_to_institutes))
            )
        except:
            print("Warning! Cannot load list of institutes!\n"
                  "Please reload the script!")
            self.restart_script(browser)
        finally:
            wait = WebDriverWait(browser, 10)
            for item in institutes:
                try:
                    wait.until(
                            EC.element_to_be_clickable((
                                By.XPATH,
                                XPATH_to_institutes))
                    )
                    item.click()
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
                            """
                            Просто клики, без проверки наличия групп
                            groups = wait.until(
                                    EC.presence_of_all_elements_located((By.XPATH, XPATH_to_groups))
                            )
                            """
                        except:
                            print("Warning! Cannot load list of groups!")
                            # Если беда с подключением перезапускаем скрипт, иначе продолжаем
                            if not self.check_connection():
                                self.restart_script(browser)
                                return

                except:
                    print("Warning! Cannot load list of specialities!")
                    # Если беда с подключением перезапускаем скрипт, иначе продолжаем
                    if not self.check_connection():
                        self.restart_script(browser)
                        return

        self.html = browser.page_source
        time.sleep(5)
        browser.quit()
