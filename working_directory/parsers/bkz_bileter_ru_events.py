import re
from datetime import datetime

from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession

class BkzEvents(EventParser):
    proxy_check_url = 'https://www.bileter.ru/'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.bileter.ru/afisha/building/bolshoy_kontsertnyiy_zal_oktyabrskiy.html'
        self.main_url = 'https://www.bileter.ru'
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            'user-agent': self.user_agent
        }
    

    def before_body(self):
        self.session = ProxySession(self)

    @staticmethod
    def reformat_date(date):
        find_year = re.search(r'\d{4}', date)

        if find_year: #2 Января 2024, 18:00
            box = date.split()
            day = box[0].zfill(2)
            month = box[1][:3].capitalize()
            year = box[2].strip(' ,')
            time = box[3]
            date_to_write = f"{day} {month} {year} {time}"
        else: #27 Июля, 19:00
            box = date.split()
            month = box[1][:3].capitalize()
            day = box[0].zfill(2)
            year = str(datetime.now().year)
            time = box[2]
            date_to_write = f"{day} {month} {year} {time}"
            
        return date_to_write #28 Дек 2023 19:00

    def get_all_events(self):
        r = self.session.get(self.url)
        soup = BeautifulSoup(r.text, 'lxml')

        all_afishe = soup.find('div', class_='afishe-preview')
        afishe_item = all_afishe.find_all('div', class_='afishe-item')

        all_dates_events = []

        for item in afishe_item:
            name = item.find('div', class_='name').text.strip()
            date_all = item.find('div', class_='date').text

            if '-' in date_all: # 27 - 29 Июля || 2 - 4 Января 2024        
                dates = item.find('div', class_='price')
                dates = dates.find_all('li')
                for i in dates:
                    href = self.main_url + i.find('a').get('href')
                    date = self.reformat_date(next(i.find('a').strings))
                    all_dates_events.append((name, href, date))
                
            else: #30 Июля, 19:00
                try:
                    href = self.main_url + item.find('div', class_='price').find('a').get('href')
                    date = self.reformat_date(date_all.strip())
                    all_dates_events.append((name, href, date))
                except:
                    dates = item.find('div', class_='price')
                    dates = dates.find_all('li')
                    for i in dates:
                        href = self.main_url + i.find('a').get('href')
                        date = self.reformat_date(next(i.find('a').strings))
                        all_dates_events.append((name, href, date))
                    
        return all_dates_events
            


    def body(self):
        a_events = self.get_all_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue='БКЗ «Октябрьский»')


    