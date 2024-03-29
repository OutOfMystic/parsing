from datetime import datetime
import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils import utils


class HcTractorEvents(AsyncEventParser):
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://hctraktor.org/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def get_html(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        url = 'https://hctraktor.org/'
        r = await self.session.get(url=url, headers=headers)
        return r.text


    @staticmethod
    def make_event(soup, clientkey):
        day, month, time = soup.find(class_='t-list__row-date').text.split()

        short_months_in_russian = [
            "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"
            ]
        month_now = datetime.now().month - 1
        month_request = short_months_in_russian.index(month.lower())

        year_now = datetime.now().year
        if month_request < month_now:
            year_now += 1
        
        date_final = f"{day} {month.capitalize()} {year_now} {time}"

        team1, team2 = map(lambda s: s.text.strip(), soup.find_all(class_='tlr-teams__team-title'))
        title = f"{team1} - {team2}"

        href_btn_onclick = soup.find(class_='btn btn--bg').get('onclick')
        session = re.search(r"(?<=id:')[\w\-@]+", href_btn_onclick)[0]

        href = f'https://widget.afisha.yandex.ru/w/sessions/{session}?clientKey={clientkey}'

        return title, href, date_final, clientkey, session

    async def body(self):
        r = await self.get_html()
        clientkey = double_split(r, "setDefaultClientKey',", '])', n=0).strip(" '")

        soup = BeautifulSoup(r, 'lxml')
        box = soup.find_all(class_='t-list__row')
        a_events = []

        for event in box:
            try:
                event_info = self.make_event(event, clientkey)
            except Exception as ex:
                self.error(f'Cannot load one event {ex}')
            else:
                a_events.append(event_info)


        for event in a_events:
            event_params = {"client_key":event[3],
                            "session_id":event[4]}
            self.register_event(event[0], event[1], date=event[2],
                                event_params=str(event_params).replace("'", "\""), venue='Ледовая арена «Трактор»')
