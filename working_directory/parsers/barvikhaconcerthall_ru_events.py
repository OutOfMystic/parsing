from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class BarvikhaConcertHall(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://barvikhaconcerthall.ru/events/calendar/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_events(self, soup):
        a_events = []

        items_list = soup.find_all('a', class_='schedule-event')

        for item in items_list:
            title = item.find('div', class_='schedule-event__title').text

            date_and_time = item.find('div', class_='schedule-event__date').text.strip()
            date, time = date_and_time.split('  •  ')
            date = date.split()
            date[1] = date[1][:3].title()

            normal_date = ' '.join(date) + ' ' + time

            href = item.get('href')
            href = f'https://barvikhaconcerthall.ru{href}'

            a_events.append([title, href, normal_date])

        return a_events

    async def get_events(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'barvikhaconcerthall.ru',
            'referer': 'https://barvikhaconcerthall.ru/events/calendar/',
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
        r = await self.session.get(self.url, headers=headers)

        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.parse_events(soup)

        return a_events

    async def body(self):
        a_events = await self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])
