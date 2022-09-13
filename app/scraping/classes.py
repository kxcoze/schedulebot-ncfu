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
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

FIREFOX_BINARY = FirefoxBinary("/opt/firefox/firefox")

PROFILE = webdriver.FirefoxProfile()
PROFILE.set_preference("browser.cache.disk.enable", False)
PROFILE.set_preference("browser.cache.memory.enable", False)
PROFILE.set_preference("browser.cache.offline.enable", False)
PROFILE.set_preference("network.http.use-cache", False)
PROFILE.set_preference(
    "general.useragent.override",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:72.0) Gecko/20100101 Firefox/72.0",
)

FIREFOX_OPTS = Options()
FIREFOX_OPTS.log.level = "trace"  # Debug
FIREFOX_OPTS.headless = True
GECKODRIVER_LOG = "/geckodriver.log"


def is_element_visible_in_viewpoint(driver, element) -> bool:
    return driver.execute_script(
        "var elem = arguments[0],                 "
        "  box = elem.getBoundingClientRect(),    "
        "  cx = box.left + box.width / 2,         "
        "  cy = box.top + box.height / 2,         "
        "  e = document.elementFromPoint(cx, cy); "
        "for (; e; e = e.parentElement) {         "
        "  if (e === elem)                        "
        "    return true;                         "
        "}                                        "
        "return false;                            ",
        element,
    )


class SelScrapingSchedule:

    html = ""

    def restart_script(self, browser):
        """Перезапуск скрипта"""

        # Выход из браузера в случае рестарта скрипта
        browser.quit()
        logging.warning("Restarting script...")
        return

    def check_connection(self):
        """Проверка наличия интернета"""
        # Можно сделать лучше!
        # Данная функция проверяет наличие интернета, а не скорость соединения,
        # поэтому необходимо переделать в скором времени.
        try:
            subprocess.check_call(["ping", "-c 1", "www.google.ru"])
            logging.warning("Connection is good.")
            return True
        except subprocess.CalledProcessError:
            logging.warning("Connection is broken.")
            return False

    def get_html_from_schedule(self):
        """Прокликиваем все доступные институты и специальности
        ради получения ссылок на группы, возвращаем html-документ
        страницы в переменную класса html"""
        url = "https://ecampus.ncfu.ru/schedule"
        logging.info(f"Initialize getting all group codes from {url}")
        ff_opt = {
            "firefox_binary": FIREFOX_BINARY,
            "firefox_profile": PROFILE,
            "options": FIREFOX_OPTS,
            "service_log_path": GECKODRIVER_LOG,
        }
        browser = webdriver.Firefox(**ff_opt)
        browser.get(url)
        XPATH_to_institutes = (
            "//div[@id='page']/div[@id='select-group']"
            "/div[@class='col-lg-7 col-md-6']"
            "/div[@id='institutes']"
            "/div[@class='panel panel-default']"
        )

        XPATH_to_specialities = "".join(
            (
                XPATH_to_institutes,
                (
                    "/div[@class='panel-collapse collapse in']"
                    "/div[@class='panel-body']"
                    "/div[@class='panel-group specialities']"
                    "/div[@class='panel panel-default']"
                    "/div[@class='panel-heading']"
                ),
            )
        )

        try:
            institutes = WebDriverWait(browser, 30).until(
                EC.presence_of_all_elements_located((By.XPATH, XPATH_to_institutes))
            )
        except:
            logging.exception(
                "Cannot load list of institutes!\n" "Please reload the script!"
            )
            self.restart_script(browser)
        else:
            time.sleep(2)
            wait = WebDriverWait(browser, 10)
            for item in institutes[::-1]:
                try:
                    wait.until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_to_institutes))
                    )
                    while not is_element_visible_in_viewpoint(browser, item):
                        item.location_once_scrolled_into_view
                    item.click()
                    logging.info(f"Successful clicked on this: {item.text}")
                    specialities = wait.until(
                        EC.presence_of_all_elements_located(
                            (By.XPATH, XPATH_to_specialities)
                        )
                    )
                    for speciality in specialities[::-1]:
                        try:
                            while not is_element_visible_in_viewpoint(
                                browser, speciality
                            ):
                                speciality.location_once_scrolled_into_view
                            speciality.click()
                            logging.info(
                                f"Successful clicked on this: {speciality.text}"
                            )
                        except:
                            logging.exception("Cannot load list of groups!")
                            # Если беда с подключением перезапускаем скрипт, иначе продолжаем
                            if not self.check_connection():
                                self.restart_script(browser)
                                return

                except:
                    logging.exception("Cannot load list of specialities!")
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
        soup = BS4(self.html, "lxml")
        institutes = soup.find("div", id="institutes").find_all(
            "div", class_="panel panel-default", recursive=False
        )

        data_from_schedule = []
        for institute in institutes:
            instituteName = (
                institute.find("div", class_="panel-heading").find("span").text.strip()
            )
            data_instit = {"instituteName": instituteName, "specialities": []}

            specialities = institute.find(
                "div", class_="panel-group specialities"
            ).find_all("div", class_="panel panel-default", recursive=False)
            for speciality in specialities:
                specialityName = (
                    speciality.find("div", class_="panel-heading")
                    .find("span")
                    .text.strip()
                )
                data_specialities = {
                    "specialityName": specialityName,
                    "groups": [],
                }

                list_group = speciality.find("ul", class_="list-group").find_all("a")
                for group in list_group:
                    groupName = group.find("span").text
                    groupCode = group.get("href").split("/")[-1]

                    data_groups = {
                        "groupName": groupName,
                        "groupCode": groupCode,
                    }

                    data_specialities["groups"].append(data_groups)
                data_instit["specialities"].append(data_specialities)
            data_from_schedule.append(data_instit)

        return data_from_schedule
