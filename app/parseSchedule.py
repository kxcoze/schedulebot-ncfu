from bs4 import BeautifulSoup as BS4

from selScrapingNCFU import SelScrapingSchedule

class ParserSchedule:
    def __init__(self, html):
        self.html = html
        
    
    def get_data(self):
        soup = BS4(self.html, 'lxml')
        institutes = soup.find('div', id='institutes').find_all('div',class_ = 'panel panel-default', recursive=False)
        
        data_from_schedule = []
        for institute in institutes:
            instituteName = institute.find('div', class_='panel-heading').find('span').text.strip()
            data_instit = {'instituteName':instituteName, 'specialities':[]}

            specialities = institute.find('div', class_='panel-group specialities').find_all('div', class_='panel panel-default', recursive=False)
            for speciality in specialities:
                specialityName = speciality.find('div', class_='panel-heading').find('span').text.strip()
                data_specialities = {'specialityName':specialityName, 'groups':[]}

                list_group = speciality.find('ul', class_='list-group').find_all('a')
                for group in list_group:
                    groupName = group.find('span').text
                    groupCode = group.get('href').split('/')[-1]

                    data_groups = {'groupName':groupName, 'groupCode':groupCode}


                    data_specialities['groups'].append(data_groups)
                data_instit['specialities'].append(data_specialities)
            data_from_schedule.append(data_instit)

                
        return data_from_schedule


def get_codes():
    schedule = SelScrapingSchedule()    
    while not schedule.html:    
        schedule.get_html_from_schedule()
   
    parser = ParserSchedule(schedule.html)

    return parser.get_data()
