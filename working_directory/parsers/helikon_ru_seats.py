import json
from typing import NamedTuple

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class HelikonRu(SeatsParser):
    event = 'helikon.ru'
    url_filter = lambda url: 'helikon.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.url = 'https://core.helikon.ubsystem.ru/uiapi/event/scheme?id=' + self.url.split('/')[-1]

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'Стол' in sector_name:
            sector_name = sector_name.replace('№', '')
        elif 'Партер' in sector_name:
            sector_name = 'Партер'
        elif 'Амфитеатр' in sector_name and 'равая' in sector_name:
            sector_name = 'Амфитеатр, правая сторона'
        elif 'Амфитеатр' in sector_name and 'евая' in sector_name:
            sector_name = 'Амфитеатр, левая сторона'

        return sector_name

    def _parse_seats(self) -> OutputData:
        json_data = self._request_to_all_place()

        all_place = self._get_all_place_from_json_data(json_data)

        output_data = self._get_output_data(all_place)

        return output_data

    def _get_output_data(self, all_place: list[dict]) -> OutputData:
        sectors_data = {}
        for place in all_place:
            is_free = place['unavailable']
            if is_free == 0:
                sector_name = place['areaTitle']
                place_row = place['row']
                place_seat = place['seat']
                place_price = place['price']

                tickets = {(place_row, place_seat): place_price}

                try:
                    old_tickets = sectors_data[sector_name]
                    sectors_data[sector_name] = old_tickets | tickets
                except KeyError:
                    sectors_data[sector_name] = tickets

        for sector_name, tickets in sectors_data.items():
            sector_name = self._reformat(sector_name)
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_all_place_from_json_data(self, json_data: json) -> list[dict]:
        all_place = json_data['seats']
        return all_place

    def _request_to_all_place(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://www.helikon.ru',
            'pragma': 'no-cache',
            'referer': 'https://www.helikon.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers, verify=False)
        return r.json()

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
