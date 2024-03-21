import json
import inspect
import re

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.utils.parse_utils import decode_unicode_escape, double_split


class BileterSeats(AsyncSeatsParser):
    url_filter = lambda url: 'bileter.ru' in url
    proxy_check = SpecialConditions(url="https://www.bileter.ru/")

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id_ = self.url.split('/')[-1]
        self.a_sectors = {}

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def get_seats(self, url_seats):
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
            "Referer": f"https://www.bileter.ru/performance/{self.event_id_}",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "user-agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }

        r = await self.session.get(url_seats, headers=headers)

        activePlaces = double_split(r.json()['html'], '"activePlaces":', '],') + ']'
        activePlaces = decode_unicode_escape(activePlaces)
        activePlaces = json.loads(activePlaces)

        return activePlaces

    def reformat_europe_teatr(self, sector):
        name = sector.get('section')
        row = sector.get('row')
        place = sector.get('place')
        price = sector.get('price')
        res_name = name
        if name == 'Партер' and self.scene == 'Камерная сцена':
            res_name = 'Амфитеатр'
        if name == 'Амфитеатр' and self.scene == 'Основной - усеченный':#TODO нужно загрузить реальную схему!
            res_name = 'Партер'
        if name == 'Ложа':
            res_name = f'{name} {row}'
            res_name = res_name.replace('A','А')
            row = '1'
            place = re.search(r'\d+', place)[0]
        self.a_sectors.setdefault(res_name, {}).update(
                {(row, place): price}
            )

    def reformat(self, activePlaces, venue):
        reformat_dict = {}
        if venue == 'БКЗ «Октябрьский»':
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
        elif 'Театр Европы (МДТ)' in venue:
            reformat_dict = {
                'Ложа': self.reformat_europe_teatr,
                'Партер': self.reformat_europe_teatr,
                'Амфитеатр': self.reformat_europe_teatr
            }

        for i in activePlaces:
            # print(i, 'iactivePlace')
            if i['section'] in reformat_dict:
                section = reformat_dict.get(i['section'])
                if inspect.ismethod(section):
                    section(i)
                    continue
            else:
                section = i['section']
            if section is not None:
                self.a_sectors.setdefault(section, {}).update(
                    {(i['row'], i['place']): i['price']}
                )

    async def body(self):
        url_seats = f'https://www.bileter.ru/performance/hall-scheme?IdPerformance={self.event_id_}'
        activePlaces = await self.get_seats(url_seats)
        self.reformat(activePlaces, self.venue)# fill self.a_sectors

        for sector_name, tickets in self.a_sectors.items():
            #self.info(sector_name, len(tickets))
            self.register_sector(sector_name, tickets)