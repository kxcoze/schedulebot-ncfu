from bs4 import BeautifulSoup as BS4
from scheduleCreator import WriterInFiles


class ParserSchedule:
    def __init__(self, html):
        self.html = html
        
    
    def get_data(self):
        soup = BS4(self.html, 'lxml')
        institutes = soup.find('div', id='institutes').find_all('div',class_ = 'panel panel-default', recursive=False)
        
        data_for_university = []
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
            data_for_university.append(data_instit)

                
        return data_for_university







def main():
    html = ''
    with open('schedule.html') as f:
        html = f.read()
    writer = WriterInFiles()
    parser = ParserSchedule(html)
    json_data = parser.get_data()
    
    writer.write_in_json(json_data, 'university_codes.json')

if __name__ == '__main__':
    main()
