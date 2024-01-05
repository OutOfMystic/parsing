import json
from typing import NamedTuple

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class FcUralRu(SeatsParser):
    url_filter = lambda url: 'ticket.fc-ural.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        ...

    def _parse_seats(self) -> OutputData:
        soup = self._request_to_get_free_sectors()

        links_to_sector_data = self._get_free_sectors_from_soup(soup)

        output_data = self._get_output_data(links_to_sector_data)

        return output_data

    def _get_output_data(self, links_to_sector_data: ResultSet[Tag]) -> OutputData:
        for link_to_sector_data in links_to_sector_data:
            url = 'https://ticket.fc-ural.ru' + link_to_sector_data.get('href')
            soup = self._request_to_place(url)
            sector_name = soup.find('div', class_='zone-name').text.strip()

            json_data_place, json_data_price = self._get_json_data_about_palce_from_soup(soup)

            all_price_zones = self._get_price_zones_from_json(json_data_price)

            output_data = self._get_output_data_from_json(sector_name, json_data_place, all_price_zones)

            yield output_data

    def _get_output_data_from_json(self, sector_name: str, json_data_place: json, all_price_zones: dict[str, int]) -> OutputData:
        tickets = {}
        for place in json_data_place:
            place_row_and_seat = place['name']
            place_row_and_seat = place_row_and_seat.split('Ряд ')[-1]
            place_row, _, place_seat = place_row_and_seat.split()

            place_price_zone_id = place['pricezoneId']
            place_price = all_price_zones[place_price_zone_id]
            tickets[(place_row, place_seat,)] = place_price

        return OutputData(sector_name=sector_name, tickets=tickets)

    def _get_price_zones_from_json(self, json_data_price: json) -> dict[str, int]:
        all_price_zones = {}

        for price_data in json_data_price:
            price_zone_id = price_data['pricezoneId']
            price_value = price_data['value']
            price_value = int(price_value.split('.')[0])
            all_price_zones[price_zone_id] = price_value

        return all_price_zones

    def _get_json_data_about_palce_from_soup(self, soup: BeautifulSoup) -> tuple[json, ...]:
        script_with_json = soup.select('div.content script')[0]
        json_data_place = double_split(script_with_json.text, 'CORE.data.seats = ', ';')
        json_data_place = json.loads(json_data_place)
        json_data_price = double_split(script_with_json.text, 'CORE.data.prices = ', ';')
        json_data_price = json.loads(json_data_price)
        return json_data_place, json_data_price

    def _get_free_sectors_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        links_to_sector_data = soup.select('table.tickets__list a')
        return links_to_sector_data

    def _request_to_place(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'ticket.fc-ural.ru',
            'pragma': 'no-cache',
            'referer': 'https://ticket.fc-ural.ru/view-available-zones/479',
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
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def _request_to_get_free_sectors(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'ticket.fc-ural.ru',
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
