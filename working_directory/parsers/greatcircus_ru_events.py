
from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.date import month_list


class Parser(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.greatcircus.ru/#!events'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def get_events(self, events_data):
        a_events = []
        set_pres = await self.get_set_pres()

        for month_data in events_data:
            month = month_list[month_data['month']]
            year = month_data['year']

            for venue in month_data['venues']:
                shows_list = venue['shows_list']
                activity_dict = {activity['activity_index']: activity['activity'] for activity in shows_list if isinstance(activity, dict)}

                for week in venue['weeks'].values():
                    for day_dict in week.values():
                        day = day_dict['day']

                        for event in day_dict['events']:
                            title = activity_dict[event['activity_index']]
                            time = event['time']
                            date = f'{day} {month} {year} {time}'
                            show_id = event['show_id']
                            pre = set_pres[event['set']]
                            href = f'https://iframeab-{pre}.intickets.ru/node/{show_id}/?locale=ru_RU'

                            a_events.append([title, href, date])

        return a_events

    async def get_request(self):
        url = 'https://www.greatcircus.ru/api/tickets/calendardata/0?lang=ru'  # &set=1, непонятно надо или нет
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
            'host': 'www.greatcircus.ru',
            'referer': 'https://www.greatcircus.ru/',
            'sec-ch-ua': '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        
        r_json = await self.session.get_json(url, headers=headers)
        return r_json

    async def get_set_pres(self):
        url = 'https://www.greatcircus.ru/app/events/show.js'
        r_text = await self.session.get_text(url, headers={})

        set_pres = {
            1: 'pre4073',
            2: 'pre4809'
        }

        if 'iframeab' not in r_text:
            pass
        else:
            # TODO Если окажется что эти переменные меняются. Парсить их из r.text

            pass

        return set_pres

    async def body(self):
        events_data = await self.get_request()
        a_events = await self.get_events(events_data)

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])
