from bs4 import BeautifulSoup as BS4
import requests
import json
import csv

class Parser:
    def __init__(self, postURL):
        # URL = 'https://ecampus.ncfu.ru/schedule'
        # postURL1 = 'https://ecampus.ncfu.ru/schedule/GetSpecialities'
        # postURL2 = 'https://ecampus.ncfu.ru/schedule/GetAcademicGroups'
        # URLgroup3 = 'https://ecampus.ncfu.ru/schedule/group/'
        self.url = postURL
        self.urlgroup =  self.url + '/group/'

    def post_url(self, url, req):
        r = requests.post(url, json=req)
        return r.json()

    def get_html(self):
        r = requests.get(self.url)
        return r.text
        
    def get_data(self, html):
        pass       

    def write_in_csv(self, rec_data, data, filename='nfcu_schedule.txt'):
        with open(filename, 'a+') as f:
            writer = csv.writer(f)
            #writer.writerow(('instituteName', 'instituteId', 'specialty', 'branchId'))
            for i in rec_data:
                writer.writerow((i['instituteName'], data['instituteId'], i['Name'], data['branchId']))
    
    def write_from_json(data):
        pass

def main():
    url = 'https://ecampus.ncfu.ru/schedule/GetSpecialities'
    site = Parser(url)
    #site.get_data(site.get_html())
    #site.write_in_files(site.get_html())
    instituteName = input()
    d = {'instituteName': instituteName}
    instituteId = int(input())
    js_req = {'branchId': 1, 'instituteId': instituteId}
    data = site.post_url(url+'/'+str(instituteId), js_req)
    for i in data:
        i.update(d)
    print(data)
    site.write_in_csv(data, js_req, 'ncfu.csv')

if __name__ == '__main__':
    main()
