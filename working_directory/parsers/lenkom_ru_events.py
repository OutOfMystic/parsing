import json

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.utils.date import month_list
from parse_module.manager.proxy.sessions import AsyncProxySession


class Lenkom(AsyncEventParser):
    proxy_check = SpecialConditions(url='https://tickets.afisha.ru/')

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.afisha.ru/wl/54/api/events?lang=ru'
        self.count_request = 0

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_events(self, data):
        a_event = []

        for event in data:
            free_place = int(event.get('count'))
            if free_place <= 0:
                continue
            title = event.get('name')

            date_and_time = event.get('date')
            date, time = date_and_time.split()
            time = ':'.join(time.split(':')[:2])
            year, month, day = date.split('-')

            normal_date = day + ' ' + month_list[int(month)] + ' ' + year + ' ' + time

            event_id = event.get('id')
            href = f'https://tickets.afisha.ru/wl/54/api/events/info?lang=ru'

            a_event.append([title, href, normal_date, event_id])

        return a_event

    async def request_parser(self):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'tickets.afisha.ru',
            'origin': 'https://tickets.afisha.ru',
            'referer': 'https://tickets.afisha.ru/wl/54/api?building_id=undefined&cat_id=undefined&gclid=991064686.1676449618&site=lenkom.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = await self.session.get(self.url, headers=headers)
        try:
            return r.json()
        except json.JSONDecodeError as e:
            if self.count_request == 10:
                raise Exception(f'Возникла ошибка {e}')
            self.count_request += 1
            return await self.request_parser()

    async def get_events(self):
        json_data = await self.request_parser()

        a_events = self.parse_events(json_data)

        return a_events

    async def body(self):
        a_events = await self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], event_id_=event[3])
