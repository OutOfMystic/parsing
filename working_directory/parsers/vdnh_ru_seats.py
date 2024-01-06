import json
from typing import NamedTuple

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class VDNHRu(AsyncSeatsParser):
    event = 'vdnh.ru'
    url_filter = lambda url: 'vdnh.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.action_id = double_split(self.url, '&id=', '&')
        self.token = double_split(self.url, '&token=', '&')
        self.fid = double_split(self.url, '&frontendId=', '&')

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'Амфитеатр' in sector_name:
            if '1' in sector_name:
                sector_name = 'Первый амфитеатр, ' + ' '.join(sector_name.split()[2:])
            elif '2' in sector_name:
                sector_name = 'Второй амфитеатр, ' + ' '.join(sector_name.split()[2:])
        return sector_name

    async def _parse_seats(self) -> OutputData:
        json_data = await self._requests_to_json_data_action_event_id()

        action_event_id = self._get_action_event_id_from_json_data(json_data)

        soup = await self._request_to_get_svg_with_place(action_event_id)

        all_row = self._get_row_from_soup(soup)

        price_zones = self._get_price_zones_from_soup(soup)

        output_data = self._get_output_data(all_row, price_zones)

        return output_data

    def _get_output_data(self, all_row: ResultSet[Tag], price_zones: dict[str, int]) -> OutputData:
        sector_name = 'Партер'
        tickets = {}

        for row in all_row:
            place_row = row['sbt:row']
            places = self._get_free_place_from_row(row)
            for place in places:
                place_seat = place['sbt:seat']
                place_price_zone = place['sbt:cat']
                place_price = price_zones[place_price_zone]

                tickets[(place_row, place_seat,)] = place_price

        return OutputData(sector_name=sector_name, tickets=tickets)

    def _get_price_zones_from_soup(self, soup: BeautifulSoup) -> dict[str, int]:
        all_price_zones = soup.findAll('category')
        all_price_zones = {price_zone['sbt:index']: int(price_zone['sbt:price']) for price_zone in all_price_zones}
        return all_price_zones

    def _get_row_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        all_row = soup.findAll('g', class_='c1')
        return all_row

    def _get_free_place_from_row(self, row: Tag) -> ResultSet[Tag]:
        free_place = row.select('circle[sbt\:state="1"]')
        return free_place

    def _get_action_event_id_from_json_data(self, json_data: json) -> str:
        action_event_id = json_data['action']['venueList'][0]['actionEventList'][0]['actionEventId']
        return action_event_id

    async def _requests_to_json_data_action_event_id(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'content-length': '196',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://vdnh.ru',
            'pragma': 'no-cache',
            'referer': 'https://vdnh.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent
        }
        data = {
            "userId": 0,
            "sessionId": "ab230c4929f2216c7cdd393424f9a004",
            "fid": self.fid,
            "token": self.token,
            "versionCode": "1.0",
            "locale": "ru",
            "command": "GET_ACTION_EXT",
            "cityId": "2",
            "actionId": self.action_id
        }
        url = 'https://api.bil24.pro/json'
        r = await self.session.post(url, headers=headers, json=data)
        return r.json()

    async def _request_to_get_svg_with_place(self, action_event_id: str) -> BeautifulSoup:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://vdnh.ru',
            'pragma': 'no-cache',
            'referer': 'https://vdnh.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent
        }
        url = (f'https://api.bil24.pro/image'
               f'?type=seatingPlan&actionEventId={action_event_id}'
               f'&userId=0&fid={self.fid}&locale=ru&rnd=0.628378540899625')
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'xml')

    async def body(self):
        sector = await self._parse_seats()
        self.register_sector(sector.sector_name, sector.tickets)
