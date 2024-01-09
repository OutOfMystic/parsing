from datetime import datetime
import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class VtbArena(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://vtb-arena.com/poster/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_events(self, soup):
        a_events = []

        # all_events = soup.find_all('div', class_='col')
        all_events = soup.select('#poster_poster div.col.w-33')

        for event in all_events:
            title = event.find('a', class_='card-c__title').text.strip()

            #03 ноября - 06 ноября or 02 ноября 2023 20:45
            date = event.find('div', class_='card-c__date')
            find_many_dates = date.text.strip().split()
            # date = double_split(str(date), '>', '<').strip()
            href = event.find('a', class_='card-c__label')
            if not href:
                continue
            href = href.get('href')
            if '-' in find_many_dates or len(find_many_dates) < 5:
                box = self.get_all_event_dates(href, title)
                a_events.extend(box)
            else:
                try:
                    _date = date.get('content')
                    datetime_object = datetime.strptime(_date, '%Y-%m-%dT%H:%M')
                except:
                    _date = date.text.strip().split()
                    month = _date[1][:3].title()
                    if month == 'Мая':
                        month = 'Май'
                    datetime_object = f"{_date[0]} {month} {_date[2]} {_date[-1]}"
                if not href:
                    continue
                
                a_events.append([title, href, datetime_object])

        return a_events

    def get_all_event_dates(self, event_url, title):
        if 'http' not in event_url:
            event_url = f'https://vtb-arena.com{event_url}'
        a1_events = []
        soup = self.get_events(event_url)
        box_main = soup.find_all(class_=re.compile(r'time-block__main'))
        for event in box_main:
            trs = event.find_all('tr', class_=False)
            day = event.find(class_='time-block__day').text.strip()
            month, year = event.find(class_='time-block__month').text.strip().split()
            month = month[:3].capitalize()
            if month.lower == 'мая':
                month = 'Май'
            for date in trs:
                href = date.find(class_='btn').get('href')
                time = date.find(attrs={'data-label':"Время"}).text.strip()
                date_to_write = f"{day} {month} {year} {time}"
                a1_events.append((title, href, date_to_write))
        return a1_events

    async def get_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'referer': 'https://vtb-arena.com/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')
        return soup

    async def body(self):
        soup = await self.get_events(self.url)
        a_events = self.parse_events(soup)

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue='ВТБ Арена')