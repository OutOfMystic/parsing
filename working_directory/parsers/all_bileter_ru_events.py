from datetime import datetime
import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.manager.proxy.sessions import AsyncProxySession



class BileterEvents(AsyncEventParser):
    proxy_check = SpecialConditions(url="https://www.bileter.ru/")

    def __init__(self,*args):
        super().__init__(*args)
        self.delay = 3600
        self.driver_source = None
        self.urls = [
            ('https://www.bileter.ru/afisha/building/bolshoy_kontsertnyiy_zal_oktyabrskiy.html',
             'БКЗ «Октябрьский»'),
            ('https://www.bileter.ru/afisha/building/malyiy_dramaticheskiy_teatr__teatr_evropyi.html',
             'Театр Европы (МДТ)')]

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

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def reformat_date(date):
        '''бро, если будущий месяц имеет индекс в списке short_months_in_russian
                    меньше чем текущий - то это следующий год'''
        date_now = datetime.now()
        current_year = date_now.year
        current_month = date_now.month - 1
        short_months_in_russian = [
            "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

        find_year = re.search(r'\d{4}', date)
        if find_year:  # 2 Января 2024, 18:00
            box = date.split()
            day = box[0].zfill(2)
            month = box[1][:3].capitalize()
            year = box[2].strip(' ,')
            time = box[3]
            date_to_write = f"{day} {month} {year} {time}"
        else:  # 27 Июля, 19:00
            box = date.split()
            month = box[1][:3].lower().replace('мая', 'май')
            month_find = short_months_in_russian.index(month)
            if month_find < current_month:
                current_year += 1
            day = box[0].zfill(2)
            time = box[2]
            date_to_write = f"{day} {month.capitalize()} {current_year} {time}"

        return date_to_write  # 28 Дек 2023 19:00

    async def get_all_events_by_afishe_item(self, url):
        r = await self.session.get(url)
        soup = BeautifulSoup(r.text, 'lxml')

        all_afishe = soup.find('div', class_='afishe-preview')
        afishe_item = all_afishe.find_all('div', class_='afishe-item')

        all_dates_events = []

        for item in afishe_item:
            name = item.find('div', class_='name').text.strip()
            date_all = item.find('div', class_='date').text

            if '-' in date_all:  # 27 - 29 Июля || 2 - 4 Января 2024
                dates = item.find('div', class_='price')
                dates = dates.find_all('li')
                for i in dates:
                    href = self.main_url + i.find('a').get('href')
                    date = self.reformat_date(next(i.find('a').strings))
                    all_dates_events.append((name, href, date))

            else:  # 30 Июля, 19:00
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

    async def get_all_events_by_building_schedule(self, url):
        r = await self.session.get(url)
        soup = BeautifulSoup(r.text, 'lxml')

        all_afisha = soup.find('section', class_='building-schedule')
        building_schedule_item = all_afisha.find_all('div', class_='building-schedule-item')
        #print(len(building_schedule_item), 'building_schedule_item')
        all_dates_events = []

        for item in building_schedule_item:
            # date
            date = item.find('div', class_='building-schedule-item-date')
            day = date.find('div', class_='schedule-date_date').text.strip()
            month = date.find('div', class_='schedule-date_month').text.strip()
            time = item.find('div', class_='building-schedule-session-time').text.strip()
            full_date = f"{day} {month} {time}"  # 30 Июля 19:00
            date_resault = self.reformat_date(full_date)
            # name and scene
            name = item.find(class_='show-link-title').text.strip()
            scene = item.find(class_='building-link').text.strip()
            href_element = item.find(class_='item')
            if href_element:
                href = href_element.get('href')
                url = self.main_url + href
                all_dates_events.append((name, url, date_resault, scene))

        return all_dates_events

    async def body(self):
        for url, venue in self.urls:
            # a_events = await self.get_all_events_by_afishe_item(url)
            a_events = await self.get_all_events_by_building_schedule(url)
            scene = None
            for event in a_events:
                if len(event) == 4:  # eсть scene
                    scene = event[-1]
                #self.info(event, 'event')
                self.register_event(event[0], event[1], date=event[2], venue=venue, scene=scene)