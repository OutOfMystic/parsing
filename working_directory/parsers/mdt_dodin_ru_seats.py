import json
from typing import NamedTuple

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.manager.proxy.sessions import AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class MdtDodin(AsyncSeatsParser):
    proxy_check = SpecialConditions(url='https://mdt-dodin.ru/')
    event = 'mdt-dodin.ru'
    url_filter = lambda url: 'mdt-dodin.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'Ложа' in sector_name:
            sector_name = sector_name.replace('"', '')
        elif 'Основная' in self.scheme.name and 'Амфитеатр' in sector_name:
            sector_name = 'Партер'

        return sector_name

    async def _parse_seats(self) -> OutputData:
        json_data = await self._request_to_json_data()

        output_data = self._get_output_data(json_data)

        return output_data

    def _get_output_data(self, json_data: json) -> OutputData:
        sectors_data = {}
        for place in json_data:
            is_busy = place.get('unavailable')
            if is_busy == 1:
                continue

            place_sector, place_row, place_seat, place_price = self._get_place_data(place)

            if sectors_data.get(place_sector):
                old_data: dict[tuple[str, str], int] = sectors_data[place_sector]
                old_data[(place_row, place_seat)] = place_price
                sectors_data[place_sector] = old_data
            else:
                sectors_data[place_sector] = {(place_row, place_seat): place_price}

        for sector_name, tickets in sectors_data.items():
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_place_data(self, place: dict) -> tuple[str, str, str, int]:
        place_sector = place['areaTitle']
        place_row = place['row']
        if place_row == '':
            place_row = '1'
        place_seat = place['seat']

        place_sector = self._reformat(place_sector)

        place_price = place['price']

        return place_sector, place_row, place_seat, place_price

    async def _request_to_json_data(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://mdt-dodin.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent
        }
        url = 'https://mdtdodin.core.ubsystem.ru/uiapi/event/scheme?id=' + self.url.split('/')[-1]
        r = await self.session.get(url, headers=headers, ssl=False)
        return r.json()['seats']

    async def body(self) -> None:
        for sector in await self._parse_seats():
            #self.info(sector.sector_name, len(sector.tickets))
            self.register_sector(sector.sector_name, sector.tickets)
