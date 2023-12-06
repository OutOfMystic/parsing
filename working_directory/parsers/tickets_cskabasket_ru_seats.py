import json
from typing import NamedTuple

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class CskaBasket(SeatsParser):
    event = 'tickets.cskabasket.ru'
    url_filter = lambda url: 'tickets.cskabasket.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = self.url.split('=')[-1]
        self.csrf_frontend = None

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'Сектор B4' in sector_name:
            sector_name = 'Сектор B4'
        elif 'Сектор АП' == sector_name:
            sector_name = 'Партер АП'
        elif 'Сектор D0' == sector_name:
            sector_name = 'Партер D0'
        elif 'Сектор B0' == sector_name:
            sector_name = 'Партер B0'
        elif 'Сектор C2c' == sector_name:
            sector_name = 'Сектор C2'
        elif 'Сектор C3c' == sector_name:
            sector_name = 'Сектор C3'
        elif 'Сектор A2c' == sector_name:
            sector_name = 'Сектор A2'
        elif 'Сектор A3c' == sector_name:
            sector_name = 'Сектор A3'

        return sector_name

    def _parse_seats(self) -> OutputData:
        soup = self._request_to_get_free_sectors()

        self._set_csrf_frontend(soup)

        free_sectors = self._get_free_sectors_from_soup(soup)

        output_data = self._get_output_data(free_sectors)

        return output_data

    def _get_output_data(self, free_sectors: ResultSet[Tag]) -> OutputData:
        for sector in free_sectors:
            sector_name = sector.get('sector_name')
            sector_name = self._reformat(sector_name)

            sector_id = sector.get('view_id')
            json_data = self._request_to_place(sector_id)

            all_price_zones = self._get_price_zones_from_json(json_data)

            all_place_in_sector = json_data['prices']

            output_data = self._get_output_data_from_json(sector_name, all_place_in_sector, all_price_zones)

            yield output_data

    def _get_output_data_from_json(
            self, sector_name: str, all_place_in_sector: json, all_price_zones: dict[int, int]
    ) -> OutputData:
        tickets = {}
        for place in all_place_in_sector:
            place_row_and_seat = place['n']
            place_row_and_seat = place_row_and_seat.split('Ряд ')[-1]
            place_row, _, place_seat = place_row_and_seat.split()

            place_price_zone_id = place['z']
            place_price = all_price_zones[place_price_zone_id]
            tickets[(place_row, place_seat,)] = place_price

        return OutputData(sector_name=sector_name, tickets=tickets)

    def _get_price_zones_from_json(self, json_data: json) -> dict[int, int]:
        output_price_zones = {}
        price_zones = json_data['zones']
        for price_zone in price_zones:
            price_zone_id = price_zone['zone']
            price_zone_price = price_zone['price']
            output_price_zones[price_zone_id] = price_zone_price
        return output_price_zones

    def _get_free_sectors_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        svg = soup.select('svg#mainsvg')[0]
        free_sectors = svg.select('g:not([free="0"])')
        return free_sectors

    def _set_csrf_frontend(self, soup: BeautifulSoup) -> None:
        self.csrf_frontend = soup.select('meta[name="csrf-token"]')[0].get('content')

    def _request_to_place(self, sector_id: str) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'content-length': '131',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://tickets.cskabasket.ru',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            'event_id': self.event_id,
            'view_id': sector_id,
            '_csrf-frontend': self.csrf_frontend
        }
        url = 'https://tickets.cskabasket.ru/event/get-prices'
        r = self.session.post(url, data=data, headers=headers)
        return r.json()

    def _request_to_get_free_sectors(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
