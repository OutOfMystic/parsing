import json
from typing import NamedTuple

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class WwwMosconsvRu(AsyncSeatsParser):
    event = 'mosconsv.ru'
    url_filter = lambda url: 'api.zapomni.systems' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'Амфитеатр' in sector_name:
            if '1' in sector_name:
                sector_name = 'Первый амфитеатр, ' + ' '.join(sector_name.split()[2:])
            elif '2' in sector_name:
                sector_name = 'Второй амфитеатр, ' + ' '.join(sector_name.split()[2:])
        elif 'Ложа №10' in sector_name:
            sector_name = 'Второй амфитеатр, ложа 10'
        elif 'Ложа №9' in sector_name:
            sector_name = 'Второй амфитеатр, ложа 9'
        return sector_name

    def _parse_seats(self) -> OutputData:
        json_data = self._request_to_json_data()

        place_data = self._get_place_from_json_data(json_data)

        price_data = self._get_price_zone_from_json_data(json_data)

        output_data = self._get_output_data(place_data, price_data)

        return output_data

    def _get_output_data(self, place_data: dict, price_data: dict[int, int]) -> OutputData:
        sectors_data = {}
        for place in place_data:
            place_sector = place['Place']['meta']['sector']['name']['ru']
            place_row = place['Place']['meta']['row']['name']
            place_seat = place['Place']['meta']['seat']

            place_sector = self._reformat(place_sector)

            price_zone = place['price_values'][0]
            place_price = price_data[price_zone]

            try:
                old_data: dict[tuple[str, str], int] = sectors_data[place_sector]
                old_data[(place_row, place_seat)] = place_price
                sectors_data[place_sector] = old_data
            except KeyError:
                sectors_data[place_sector] = {(place_row, place_seat): place_price}

        for sector_name, tickets in sectors_data.items():
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_place_from_json_data(self, json_data: json) -> dict:
        all_places = json_data['tickets']
        return all_places

    def _get_price_zone_from_json_data(self, json_data: json) -> dict[int, int]:
        output_price_data = {}

        all_price_zone = json_data['prices']
        for price_zone_id, price_value in all_price_zone.items():
            price_for_this_price_zone = price_value['amount']
            output_price_data[price_zone_id] = price_for_this_price_zone

        return output_price_data

    def _request_to_place(self, url: str) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'tickets.fc-zenit.ru',
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
        r = self.session.get(url, headers=headers)
        return r.json()

    def _request_to_json_data(self) -> BeautifulSoup:
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
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uIjoiMDBhYWNhMTVmNTgxNjg2MTY5Y2VkODY0Y2VkMTU0MjM1ZDFjNjU0MTI5ZmMzZmFmNGNiMDM5NWFmYTU4ZmM3NTYwMmFjMzhkNGY0OWVkYTE3ZmYzM2QzYzA4YjdkN2M5ZDA2MzNhMGViZmI1OTc4Y2M2ZWIxMDc5ZWJjNmViNzAyMjVhMzk2YzE5NTNhMjJhYTlhZjUyMWZiOTg1ZTI1MGQ2OWNjNjFmNDZiZmE3ODg5NjkwM2JiNDhmNzhmNTM0ZjBkMGEwMjYyYjVjNmFlZTJkNWI2YzkwNGFkZmQyYzE0YTM3OTlhNTI3NzI2MDZkMDgzMWU4NmI3NmU5N2YyMTA5M2U3NDQwMGRjZGU2MmMzMDM2YzFmYjkzMmQ5NDM3MDIwMTdlM2Q1MmIwNzU2Y2YzOTU2ZTcyMjQ4OGZhMzYyY2Q5NDgxOTMxNTI4ZDZjNjYwNDkyMWRmODJlYjFhZWNmYjc3MjA2NWEyODlhNjZhOWJhYjQyNGQyMGQ0Y2JlOWQ4YjY2MGUzZWY0YzNjZmI1ODkyZTNjNWQ0NmY0MmY3YWUyZDZiNzRlY2VhZGM2MWM5OTY4Mjc2MTcyODE1NjExYzAzODAxYWYwNTVlZDBlYzczYmVmOWFiMWJkMGZhZTZkMmU1ODkzYWNlMjVkZTRmNGU2ZGJkNTM0MmY1NjRmOGYxYmJkMCIsImlhdCI6MTY4MjUxNTA3N30.nW27Qm7fulBPnBj1fztSArSxsC7su4DjqdLMVkZuGPU',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'mosconsv.zapomni.ru',
            'pragma': 'no-cache',
            'referer': r.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        parametr_for_url = r.url.split('=')[-1]
        url_to_data = f'https://mosconsv.zapomni.ru/api/widget/v1/schedule/{parametr_for_url}/tickets'
        r = self.session.get(url_to_data, headers=headers)
        return r.json()

    async def body(self):
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
