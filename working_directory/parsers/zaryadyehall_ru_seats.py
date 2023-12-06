import json
from random import randint
from typing import NamedTuple, Optional, Union

from requests.exceptions import JSONDecodeError

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class ZaryadyeHall(SeatsParser):
    event = 'zaryadyehall.ru'
    url_filter = lambda url: 'listim.com' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id: str = self.url.split('/')[-1]
        # self.user_token: str = double_split(self.url, 'gclid=', '#')
        self.user_token: str = f'1404449{randint(100, 999)}'

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'Бельэтаж сцена' in sector_name:
            if len(sector_name.split()) > 2:
                sector_name = sector_name.split()
                sector_name = f'{sector_name[0]} {sector_name[1]}, ' + ' '.join(sector_name[2:])
        elif 'Амфитеатр' in sector_name or 'Бельэтаж' in sector_name:
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

        return sector_name

    def _parse_seats(self) -> Optional[Union[OutputData, list]]:
        json_data = self._request_to_json_data()
        if json_data is None:
            return []

        places = self._get_place_from_json(json_data)

        output_data = self._get_output_data(places)

        return output_data

    def _get_output_data(self, places: dict[str, list]) -> OutputData:
        sectors_data = {}
        for place in places['simple_sectors']:
            pass  # Билеты на экскурсии и т.п. в виде карточек похожи на танцольные

        for place in places['places']:
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
            'simple_sectors': json_data['simple_sectors'],
            'places': json_data['places']
        }
        return places

    def _request_to_json_data(self, count_error=0):
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
            'user-agent': self.user_agent
        }
        url = 'https://www.afisha.ru/wl/101/api/events/info?lang=ru&sid='
        data = {
            'event_id': self.event_id,
            'user_token': self.user_token
        }
        r = self.session.post(url, data=data, headers=headers)
        try:
            return r.json()
        except JSONDecodeError:
            if count_error == 5:
                return None
            return self._request_to_json_data(count_error=count_error+1)

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
