from typing import NamedTuple
import json

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class MelomanRu(SeatsParser):
    url_filter = lambda url: 'go.unics.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = self.url.split('=')[-1]

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'ПАРТЕР' in sector_name:
            sector_name = sector_name.replace('ПАРТЕР', 'Партер')
        else:
            sector_name = sector_name.replace('-', ' ')

        return sector_name

    def _parse_seats(self) -> OutputData:
        soup = self._request_to_soup()

        free_sectors = self._get_free_sectors_from_soup(soup)

        output_data = self._get_output_data(free_sectors)

        return output_data

    def _get_output_data(self, free_sectors: ResultSet[Tag]) -> OutputData:
        for sector in free_sectors:
            place_sector = sector.find('text').text
            if place_sector == 'СЦЕНА':
                continue

            place_sector_id = sector.get('sector_id')
            json_data_about_places = self._request_to_json_data(place_sector_id)

            price_zones, places = self._get_data_from_json_data(json_data_about_places)
            tickets = self._get_place_data(price_zones, places)
            place_sector = self._reformat(place_sector)

            yield OutputData(sector_name=place_sector, tickets=tickets)

    def _get_place_data(self, price_zones: dict[int, int], places: list) -> dict[tuple[str, str], int]:
        tickets = {}
        for place in places:
            _, row_and_seat = place['n'].split('ряд ')
            place_row, place_seat = row_and_seat.split(' место ')
            place_price_zone = place['z']
            place_price = price_zones[place_price_zone]
            tickets[(place_row, place_seat,)] = place_price
        return tickets

    def _get_data_from_json_data(self, json_data: json) -> tuple[dict[int, int], list]:
        price_zones = {price['zone']: price['price'] for price in json_data['zones']}
        places = json_data['prices']
        return price_zones, places

    def _get_free_sectors_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        svg = soup.find('svg', attrs={'id': 'svg'})
        free_sectors = svg.select('g:not([free="0"]):not([id])')
        return free_sectors

    def _request_to_json_data(self, sector_id: str) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'content-length': '131',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://go.unics.ru',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-csrf-token': self.csrf_token,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            'x-csrf-token': self.csrf_token,
            'event_id': self.event_id,
            'view_id': sector_id
        }
        url = 'https://go.unics.ru/event/get-prices'
        r = self.session.post(url, data=data, headers=headers)
        return r.json()

    def _request_to_soup(self) -> BeautifulSoup:
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
        self.csrf_token = double_split(r.text, '"csrf-token" content="', '">')
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
