import json
from typing import NamedTuple

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class CircusSochiRu(AsyncSeatsParser):
    url_filter = lambda url: 'ticket-place.ru' in url and '|sochi' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.url = self.url[:self.url.index('|')]

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        ...

    async def _parse_seats(self) -> OutputData:
        json_data = await self._request_to_all_place()

        all_place = self._get_all_place_from_json_data(json_data)

        output_data = self._get_output_data(all_place)

        return output_data

    def _get_output_data(self, all_place: list[dict]) -> OutputData:
        sectors_data = {}
        for place in all_place:
            is_free = place['status']
            if is_free == 'free':
                sector_name = place['sector_name']
                place_row = str(place['row_sector'])
                place_seat = str(place['seat_number'])
                place_price = place['price']

                tickets = {(place_row, place_seat): place_price}

                try:
                    old_tickets = sectors_data[sector_name]
                    sectors_data[sector_name] = old_tickets | tickets
                except KeyError:
                    sectors_data[sector_name] = tickets

        for sector_name, tickets in sectors_data.items():
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_all_place_from_json_data(self, json_data: json) -> list[dict]:
        all_place = json_data['data']['seats']['data']
        return all_place

    async def _request_to_all_place(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'ticket-place.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r_json = await self.session.get_json(self.url, headers=headers)
        return r_json

    async def body(self) -> None:
        self.debug('Starting body')
        for sector in await self._parse_seats():
            if 'Ложа' in sector.sector_name:
                continue
            self.register_sector(sector.sector_name, sector.tickets)
