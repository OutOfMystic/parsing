from parse_module.models.parser import EventParser
from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class XKAvangarg(EventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.hawk.ru/webapi/calendars/available/list/grouped-by-types'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, json_data):
        a_events = []

        if len(json_data) == 0:
            return None

        all_events = json_data[0].get('calendars')

        for event in all_events:
            title = event.get('name')
            if 'Парковка' not in title:
                home_team = event.get('ownerTeamName')
                guest_team = event.get('guestTeamName')
                if home_team and guest_team:
                    title = home_team + ' - ' + guest_team
                elif not home_team and guest_team:
                    title = guest_team
                elif not guest_team and home_team:
                    title = home_team
                else:
                    title = event.get('name')
                id_to_href = event.get('id')
                href = f'https://tickets.hawk.ru/webapi/sectors/{str(id_to_href)}/available/list'

                time = event.get('time')
                date = event.get('day')

                time = time.split(':')
                date = date.split('-')[::-1]
                date[1] = month_list[int(date[1])]

                normal_date = ' '.join(date) + ' ' + ':'.join(time[:-1])

                a_events.append([title, href, normal_date])

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def get_events(self):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            # 'content-length': '37',
            'content-type': 'application/json',
            'host': 'tickets.hawk.ru',
            'origin': 'https://tickets.hawk.ru',
            'referer': 'https://tickets.hawk.ru/tickets?webTypeId=1',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        data = {
            "isSeason": 0,
            "withoutActionType": 93
        }
        r = self.session.post(self.url, headers=headers, json=data, verify=False)

        a_events = self.parse_events(r.json())

        return a_events

    def body(self):
        a_events = self.get_events()

        if a_events is None:
            return

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue='G-Drive Арена')
