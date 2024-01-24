from aiohttp.client_exceptions import ServerDisconnectedError
import asyncio
from aiohttp import ClientTimeout, ClientError
from time import time

import json
from random import randint
from typing import NamedTuple, Optional, Union

from requests.exceptions import JSONDecodeError

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class ZaryadyeHall(AsyncSeatsParser):
    event = 'zaryadyehall.ru'
    url_filter = lambda url: 'tickets.afisha.ru/wl/101/' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id: str = self.url.split('/')[-1]
        self.user_token = self.generate_user_token()
        self.spreading = 5

    @staticmethod
    def generate_user_token():
        current_time = int(time() * 1000)  # Текущее время в миллисекундах
        random_number = randint(100000, 1000000)  # Случайное число
        user_token = f"{current_time}-{random_number}"
        return user_token
        

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def load_cookies_and_xsrf(self):
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "User-Agent": self.user_agent
        }
        url_load_coolies = 'https://tickets.afisha.ru/wl/101/api?site=zaryadyehall.ru&cat_id=undefined&building_id=undefined'
        r1 = await self.session.get(url_load_coolies, headers=headers)
        if r1.status_code == 200:
            set_cookies = r1.headers.get('Set-Cookie')
            XSRF = set_cookies.split(';')[0].split('=')[-1]
            return XSRF
        raise ClientError('cannot load XSRF')


    def _reformat(self, sector_name: str) -> str:
        if 'Бельэтаж сцена' in sector_name:
            if len(sector_name.split()) > 2:
                sector_name = sector_name.split()
                sector_name = f'{sector_name[0]} {sector_name[1]}, ' + ' '.join(sector_name[2:])
        elif ('Амфитеатр' in sector_name or 'Бельэтаж' in sector_name) and 'Места для МГН' not in sector_name:
            sector_name = sector_name.split()
            sector_name = f'{sector_name[0]}, ' + ' '.join(sector_name[1:])
        elif 'Балкон. Стоячие места' == sector_name:
            sector_name = 'Балкон, стоячие места'
        elif 'Балкон' in sector_name:
            try:
                sector_name = sector_name.replace('1', '1-го').replace('2', '2-го')
                sector_name = sector_name.split()
                sector_name = f'{sector_name[0]} {sector_name[1]} {sector_name[2]}а, ' + ' '.join(sector_name[3:])
            except IndexError:
                sector_name = 'Балкон'
        elif 'Места для МГН' in sector_name:
            if 'Партер' in sector_name:
                sector_name = 'Партер (места для маломобильных групп населения)'
            elif 'ЛС' in sector_name:
                sector_name = 'Бельэтаж, левая сторона (места для маломобильных групп населения)'
            elif 'ПС' in sector_name:
                sector_name = 'Бельэтаж, правая сторона (места для маломобильных групп населения)'

        return sector_name

    async def _parse_seats(self) -> Optional[Union[OutputData, list]]:
        json_data = await self._request_to_json_data()
        if json_data is None:
            return []

        places = self._get_place_from_json(json_data)

        output_data = self._get_output_data(places)

        return output_data

    def _get_output_data(self, places: dict[str, list]) -> OutputData:
        sectors_data = {}
        for place in places.get('simple_sectors', []):
            pass  # Билеты на экскурсии и т.п. в виде карточек похожи на танцольные

        for place in places.get('places', []):
            place_price = place.get('price')
            if place_price == 0:
                continue

            place_sector, place_row, place_seat = self._get_place_data(place)

            try:
                old_data: dict[tuple[str, str], int] = sectors_data[place_sector]
                old_data[(place_row, place_seat)] = place_price
                sectors_data[place_sector] = old_data
            except KeyError:
                sectors_data[place_sector] = {(place_row, place_seat): place_price}

        for sector_name, tickets in sectors_data.items():
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_place_data(self, place: dict) -> tuple[str, ...]:
        place_sector = place['sector']['name']
        place_row = place['row']
        place_seat = place['seat']

        place_sector = self._reformat(place_sector)

        return place_sector, place_row, place_seat

    def _get_place_from_json(self, json_data: json) -> dict[str, list]:
        places = {
            'simple_sectors': json_data.get('simple_sectors', []),
            'places': json_data.get('places', [])
        }
        return places

    async def _request_to_json_data(self, count_error=0):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-length': '47',
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'www.afisha.ru',
            'origin': 'https://www.afisha.ru',
            'pragma': 'no-cache',
            'referer': 'https://www.afisha.ru/wl/101/api?gclid=1404449415',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            "X-Xsrf-Token": str(self.XSRF)
        }
        url = 'https://www.afisha.ru/wl/101/api/events/info?lang=ru&sid='
        data = {
            'event_id': str(self.event_id),
            'user_token': self.user_token
        }
        try:
            r = await self.session.post(url, data=data, headers=headers, timeout=ClientTimeout(total=10))
            await asyncio.sleep(0)
        except (asyncio.TimeoutError, ServerDisconnectedError) as ex: 
            self.warning(ex.__class__.__name__, url, data)
            if count_error == 5:
                return None
            self.change_proxy()
            await asyncio.sleep(10)
            self.XSRF = await self.load_cookies_and_xsrf()
            self.user_token = self.generate_user_token()
            return await self._request_to_json_data(count_error=count_error+1)
        try:
            return r.json()
        except JSONDecodeError:
            if count_error == 5:
                return None
            return await self._request_to_json_data(count_error=count_error+1)

    async def body(self) -> None:
        self.XSRF = await self.load_cookies_and_xsrf()
        for sector in await self._parse_seats():
            #self.info(sector.sector_name, len(sector.tickets))
            self.register_sector(sector.sector_name, sector.tickets)
