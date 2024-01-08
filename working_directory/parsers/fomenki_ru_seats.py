import json
from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class Fomenko(AsyncSeatsParser):
    url_filter = lambda url: 'fomenki.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_seats(self, json_data):
        total_sector = []
        all_sector = {}

        all_data = json.loads(json_data)

        for data in all_data.get('tickets'):
            sector = data.get('section_name').capitalize()
            row = data.get('row')
            seat = data.get('place')
            price = int(data.get('price'))

            if '' == sector:
                sector = 'Партер'
            if 'Партер рекомендовано детям от 10 лет' == sector:
                sector = 'Партер'
            if 'Сектор а' == sector or 'Сектор б' == sector:
                sector = sector.title()
            if 'Ложа балкона правая' == sector:
                sector = 'Правая ложа балкона'
            if 'Ложа балкона левая' == sector:
                sector = 'Левая ложа балкона'
            if 'Ложа б' == sector:
                sector = sector.title()
                seat = 'Б' + seat
            if 'Ложа а' == sector:
                sector = sector.title()
                seat = 'А' + seat

            if all_sector.get(sector):
                dict_sector = all_sector[sector]
                dict_sector[(row, seat,)] = price
            else:
                all_sector[sector] = {(row, seat,): price}

        for sector, total_seats_row_prices in all_sector.items():
            total_sector.append(
                {
                    "name": sector,
                    "tickets": total_seats_row_prices
                }
            )
        return total_sector

    async def request_parser(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'fomenki.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        return await self.session.get(url, headers=headers)

    async def get_seats(self):
        r = await self.request_parser(url=self.url)

        a_events = self.parse_seats(r.text)

        return a_events

    async def body(self):
        all_sectors = await self.get_seats()

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
