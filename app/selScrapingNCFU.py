from scheduleCreator import Parser, WriterInFiles
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_data_from_url(url):
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    browser = webdriver.Firefox(options=options)
    browser.get(url)
    # XPATH = /div[@class='panel-collapse collapse in']/div[@class='panel-body']/div[@class='panel-group specialities']/div[@class='panel panel-default']
    XPATH = "//div[@id='page']/div[@id='select-group']/div[@class='col-lg-7 col-md-6']/div[@id='institutes']/div[@class='panel panel-default']"
    

    try:
        institutes = WebDriverWait(browser, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, XPATH))
        )
    finally:
        for item in institutes:
            item.click()
            try:
                specialities = WebDriverWait(browser, 5).until(
                            EC.presence_of_all_elements_located((By.XPATH, XPATH + "/div[@class='panel-collapse collapse in']/div[@class='panel-body']/div[@class='panel-group specialities']/div[@class='panel panel-default']"))
                )
                for speciality in specialities:
                    speciality.click()
            finally:
                continue
            
    html = browser.page_source
    browser.quit()
    
    return html

def main():
    url = 'https://ecampus.ncfu.ru/schedule'
    writer = WriterInFiles()
    html = get_data_from_url(url)
    writer.write_in_txt(html, 'schedule.html')

if __name__ == '__main__':
    main()
