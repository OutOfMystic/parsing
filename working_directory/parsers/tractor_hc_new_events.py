from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from dataclasses import dataclass
from json import loads
from datetime import datetime as dt
from dateutil.parser import isoparse
from itertools import chain


@dataclass()
class Event:
    id_: int
    title: str
    date: dt
    parent_id: int


class HcTractorEventsNew(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tractor-arena.com/events'
        self.event_format = "https://tractor-arena.com/events/{id}"

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def get_json(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,'
                      'image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
        r = self.session.get(url=self.url, headers=headers)
        return loads(BeautifulSoup(r.text, 'lxml').select_one("#__NEXT_DATA__").text)

    @staticmethod
    def get_events_arr(json: dict):
        return json['props']['pageProps']['events']['results']

    @staticmethod
    def parse_event(item) -> Event:
        p = item["persons"]
        item = item['event']
        children = item.get('children', [])
        if not len(children):
            yield Event(
                id_=item['id'],
                title=f'{p[0]["name"]} - {p[1]["name"]}' if len(p) else item["title"],
                date=isoparse(item['date']),
                parent_id=item['id']
            )
        else:
            for chld in children:
                yield Event(
                    id_=chld['id'],
                    title=f'{p[0]["name"]} - {p[1]["name"]}' if len(p) else item["title"],
                    date=isoparse(f"{chld['date_start']}T{chld['time_start']}+00:00"),
                    parent_id=item['id']
                )

    async def body(self):
        events = chain(*map(self.parse_event, self.get_events_arr(self.get_json())))

        for event in events:
            self.register_event(
                event.title,
                self.event_format.format(id=event.id_),
                date=event.date,
                parent_id=event.parent_id
            )
            