import json
from typing import NamedTuple

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class Mikhailovsky(AsyncSeatsParser):
    event = 'mikhailovsky.ru'
    url_filter = lambda url: 'mikhailovsky.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str, row: str, seat: str) -> tuple[str, ...]:
        if 'ярус' in sector_name:
            sector_name = sector_name.replace('-й', '')
        if 'Ложа' in row:
            if 'А' in row or 'Б' in row or 'В' in row or 'Д' in row:
                sector_name = row + ' - (2 билета рядом) продаётся по два места'
                if 'В' in sector_name or 'Д' in sector_name:
                    if seat == '1' or seat == '4':
                        seat = 'Места 1 и 4'
                    elif seat == '2' or seat == '5':
                        seat = 'Места 2 и 5'
                    elif seat == '3' or seat == '6':
                        seat = 'Места 3 и 6'
                else:
                    if seat == '1' or seat == '5':
                        seat = 'Места 1 и 5'
                    elif seat == '2' or seat == '6':
                        seat = 'Места 2 и 6'
                    elif seat == '3' or seat == '7':
                        seat = 'Места 3 и 7'
                    else:
                        seat = 'Места 4 и 8'
            else:
                sector_name = f'Ложи {sector_name}а'.capitalize()
                row = row.replace('Ложа ', '')
        if sector_name == 'Ложи бельэтажа':
            sector_name = 'Ложи бельэтажа - (4 билета рядом) продаётся целиком'
            row = 'Ложа номер ' + row
            seat = 'Места с 1 по 4'
        if sector_name == 'Ложи бенуара':
            sector_name = sector_name + ' - (2 билета рядом) продаётся по два места'
            row = 'Ложа номер ' + row
            if seat == '1' or seat == '3':
                seat = 'Места 1 и 3'
            elif seat == '2' or seat == '4':
                seat = 'Места 2 и 4'
        if sector_name == 'ВИП Партер':
            sector_name = 'VIP-партер'

        return sector_name, row, seat

    async def _parse_seats(self) -> OutputData:
        text_data = await self._request_to_text_data()

        json_data = self._get_json_data_from_text(text_data)

        output_data = self._get_output_data(json_data)

        return output_data

    def _get_output_data(self, json_data: json) -> OutputData:
        sectors_data = {}
        for place in json_data.values():
            is_busy = place.get('IS_BUSY')
            if is_busy is True:
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

    def _get_place_data(self, place) -> tuple[str, str, str, int]:
        data_about_place = place['JS']

        data_place = data_about_place['part_name']
        data_place = list(map(lambda x: x.replace('Ряд', '').replace('Место', '').strip(), data_place))

        if 'Царская ложа' in data_place:
            place_sector, place_seat = data_place
            place_row = '1'
        else:
            place_sector, place_row, place_seat = data_place

        place_sector, place_row, place_seat = self._reformat(place_sector, place_row, place_seat)

        place_price = data_about_place['groupPrice']

        return place_sector, place_row, place_seat, place_price

    def _get_json_data_from_text(self, text_data: str) -> json:
        json_data_from_script_in_page = double_split(text_data, "var arPlace = JSON.parse('", "');")
        return json.loads(json_data_from_script_in_page)

    async def _request_to_text_data(self) -> str:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'mikhailovsky.ru',
            'pragma': 'no-cache',
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
        r = await self.session.get(self.url, headers=headers)
        return r.text

    async def body(self) -> None:
        for sector in await self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
