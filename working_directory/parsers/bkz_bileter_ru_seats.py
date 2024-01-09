import json

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils.parse_utils import double_split, decode_unicode_escape


class BkzPars(AsyncSeatsParser):
    url_filter = lambda url: 'bileter.ru' in url
    proxy_check = NormalConditions()

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = self.url.split('/')[-1]

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def get_seats(self, url_seats):
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
            "Referer": f"https://www.bileter.ru/performance/{self.event_id}",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "user-agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }

        r = self.session.get(url_seats, headers=headers)

        activePlaces = double_split(r.json()['html'], '"activePlaces":', '],') + ']'
        activePlaces = decode_unicode_escape(activePlaces)
        activePlaces = json.loads(activePlaces)

        return activePlaces

    @staticmethod
    def reformat(activePlaces):
        reformat_dict = {
            'Партер середина': 'Партер',
            'Партер правая сторона': 'Партер',
            'Партер левая сторона': 'Партер',
            'Балкон лев.ст.огр.видимость': 'Балкон (места с ограниченной видимостью)',
            'Балкон пр.ст.огр.видимость': 'Балкон (места с ограниченной видимостью)',
            'Балкон центр огр.видимость': 'Балкон (места с ограниченной видимостью)',
            'Балкон левая сторона': 'Балкон',
            'Балкон правая сторона': 'Балкон',
            'Балкон центр': 'Балкон',
            'Правая ложа': 'Правая ложа',
            'Левая ложа': 'Левая ложа'
        }

        a_sectors = {}
        for i in activePlaces:
            if i['section'] in reformat_dict:
                section = reformat_dict.get(i['section'])
            else:
                section = i['section']
            if section is not None:
                a_sectors.setdefault(section, {}).update(
                        {(i['row'], i['place']): i['price']}
                    )    
        return a_sectors

    async def body(self):
        url_seats = f'https://www.bileter.ru/performance/hall-scheme?IdPerformance={self.event_id}'
        activePlaces = self.get_seats(url_seats)
        a_sectors = self.reformat(activePlaces)

        for sector_name, tickets in a_sectors.items():
            self.register_sector(sector_name, tickets)