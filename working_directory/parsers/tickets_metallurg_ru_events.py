from parse_module.models.parser import EventParser
from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class XKMetalurg(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.metallurg.ru/webapi/calendars/available/list/grouped'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_events(self, json_data):
        a_events = []

        all_events = json_data[0].get('webTypes')[0].get('calendars')

        for event in all_events:
            title = event.get('name')
            title = title.replace('"', '').replace('-', ' - ')
            id_to_href = event.get('id')
            href = f'https://tickets.metallurg.ru/webapi/sectors/{str(id_to_href)}/available/list'

            time = event.get('time')
            if time is None:
                continue
            time = time.split(':')
            date = event.get('day')
            date = date.split('-')[::-1]
            date[1] = month_list[int(date[1])]

            normal_date = ' '.join(date) + ' ' + ':'.join(time[:-1])

            a_events.append([title, href, normal_date])

        return a_events

    async def get_events(self):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'content-type': 'application/json',
            'host': 'tickets.metallurg.ru',
            'origin': 'https://tickets.metallurg.ru',
            'referer': 'https://tickets.metallurg.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        data = {"isSeason": -1}
        r = await self.session.post(self.url, headers=headers, json=data, ssl=False)

        if not r.json():
            return []
        a_events = self.parse_events(r.json())

        return a_events

    async def body(self):
        a_events = await self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])