from bs4 import BeautifulSoup
from datetime import datetime

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Bilettorg(AsyncEventParser):
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.urls = {
            #'https://www.bilettorg.ru/anonces/106/': '*', # Большой театр
            'https://www.bilettorg.ru/anonces/31/': '*', # Театр Ленком
            'https://www.bilettorg.ru/anonces/132/': '*', #Никулина цирк
            'https://www.bilettorg.ru/anonces/133/': '*', #Вернадский цирк
            'https://www.bilettorg.ru/anonces/9/': '*', # Вахтангова
            #'https://www.bilettorg.ru/anonces/113/': '*' #Kreml
            'https://www.bilettorg.ru/anonces/43/': '*', #mhat chehkova
            'https://www.bilettorg.ru/anonces/114/': '*',#stanislavskii
            'https://www.bilettorg.ru/anonces/39/': '*', #ramt
            'https://www.bilettorg.ru/anonces/187/': '*', #ugolock durova
            'https://www.bilettorg.ru/anonces/33/': '*', #maly
            
        }

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_events(self, soup):
        a_events = []

        all_events = soup.select('li.wow.fadeIn')
        venue = soup.find('h1', class_='title__headline').text.split(',')[0].strip()
        if venue in self.reformat_venue:
            venue = self.reformat_venue.get(venue)

        for event in all_events:
            title = event.find('a', class_='title').text.strip()

            date, month = event.find('p', class_='date1').text.strip().split()
            month = month.title()[:3]
            if month == 'Мая':
                month = 'Май'
            time = event.find('p', class_='date2').text.strip().split()[1]
            month_current = datetime.now().month
            month_event = month_list.index(month)

            year = datetime.now().year
            if month_event < month_current:
                year += 1

            normal_date = f'{int(date):02d} {month} {year} {time}'

            scene = event.find_all('p')[2].text

            href = event.find('span', class_='a-like2')
            if href is None:
                continue
            href = href.get('onclick')
            href = double_split(href, "='", "';")
            href = f'https://www.bilettorg.ru{href}'

            a_events.append([title, href, normal_date, scene, venue])
        return a_events

    async def get_all_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'www.bilettorg.ru',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self):
        
        self.reformat_venue = {
            'Главный театр России': 'Большой театр'
        }

        for url in self.urls:
            soup = await self.get_all_events(url)
            a_events = self.parse_events(soup)

            for event in a_events:
                if 'цирк Юрия Никулина' in event[4]:
                    if any(
                        [i in event[2] for i in [
                            '10 Дек 2023 18:00', '09 Дек 2023 18:00'
                        ]]
                    ):
                        continue
                elif 'вернадского' in event[4].lower():
                    if any(
                        [i in event[2] for i in [
                            '23 Дек 2023 13:00'
                        ]]
                    ):
                        continue
                
                    
                self.register_event(event[0], event[1], date=event[2], 
                                    scene=event[3], venue=event[4])