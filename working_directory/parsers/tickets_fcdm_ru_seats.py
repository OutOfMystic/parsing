import json
from typing import NamedTuple

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class TicketsFcdmRu(SeatsParser):
    event = 'tickets.fcdm.ru'
    url_filter = lambda url: 'tickets.fcdm.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'A207' == sector_name:
            sector_name = 'Сектор A207 PLATINUM'
        elif 'A208' == sector_name:
            sector_name = 'Сектор A208 PLATINUM'
        elif 'C206' == sector_name:
            sector_name = 'Сектор C206 PLATINUM'
        elif 'A209' == sector_name:
            sector_name = 'Сектор A209 GOLD'
        elif 'C204' == sector_name:
            sector_name = 'Сектор C204 GOLD'
        elif 'A206' == sector_name:
            sector_name = 'Сектор A206 PLATINUM'
        elif 'C209LB' == sector_name:
            sector_name = 'Сектор C209 LOUNGE BAR'
        elif len(sector_name) >= 3:
            sector_name = 'Сектор ' + sector_name
        return sector_name

    def _parse_seats(self) -> OutputData:
        json_data = self._requests_to_json_data()

        free_place = self._get_free_place_from_json_data(json_data)

        output_data = self._get_output_data(free_place)

        return output_data

    def _get_output_data(self, free_place: dict[str, list[int]]) -> OutputData:
        sectors_data = {}
        for place_data, price_data in free_place.items():
            sector_name, place_row_and_seat = place_data.split('-')
            place_row, place_seat = place_row_and_seat.split(';')
            place_price = price_data[2]

            tickets = {(place_row, place_seat,): place_price}
            try:
                old_tickets = sectors_data[sector_name]
                sectors_data[sector_name] = old_tickets | tickets
            except KeyError:
                sectors_data[sector_name] = tickets

        for sector_name, tickets in sectors_data.items():
            sector_name = self._reformat(sector_name)
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_free_place_from_json_data(self, json_data: json) -> dict[str, list[int]]:
        free_place = json_data['seats']
        return free_place

    def _requests_to_json_data(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        url = f'https://tickets.fcdm.ru/api/event-show/sale/{self.url.split("/")[-1]}/available-seats/full'
        r = self.session.get(url, headers=headers, verify=False)
        return r.json()

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
