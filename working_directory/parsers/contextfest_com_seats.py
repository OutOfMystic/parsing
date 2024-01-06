import json
from typing import NamedTuple

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class Contextfest(AsyncSeatsParser):
    url_filter = lambda url: 'ticketscloud.com' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str, row: str, seat: str) -> tuple[str, str]:
        if_seat_in_parter = [
            39, 40, 61, 62, 63, 64, 85, 86, 87, 88, 109, 110, 111, 112, 133, 134, 135, 136, 157, 158, 159, 160,
            181, 182, 183, 184, 205, 206, 207, 208, 229, 230, 231, 232, 253, 254, 255, 256, 277, 278, 279, 280,
            301, 302, 323
        ]
        if 'Партер' in sector_name and int(seat) in if_seat_in_parter:
            sector_name: str = 'Партер (неудобные места)'
        elif 'Партер' in sector_name and 'Гардероб' in sector_name:
            sector_name: str = 'Партер'
        elif 'Балкон' in sector_name:
            if '3го яруса' in sector_name or '3-го яруса' in sector_name:
                sector_name: str = 'Балкон третьего яруса'
        elif 'Партер-трибуна' in sector_name:
            sector_name: str = 'Кресла партера'
        elif 'Галерея 3го яр.' in sector_name or 'Галерея 3-го яруса' in sector_name:
            row: str = ''
            if 'правая' in sector_name or 'пр. ст.' in sector_name:
                sector_name: str = 'Галерея третьего яруса. Правая сторона'
            else:
                sector_name: str = 'Галерея третьего яруса. Левая сторона'
        elif 'Места за креслами' in sector_name:
            sector_name: str = 'Места за креслами'
        elif 'Партер' in sector_name:
            sector_name: str = 'Кресла партера'
        elif 'Ложи' in sector_name:
            number_lozha: str = row
            if 'Бельэтажа' in sector_name:
                new_sector_name: str = 'Бельэтаж'
            elif 'Бенуара' in sector_name:
                new_sector_name: str = 'Бенуар'
            elif '2-го яруса' in sector_name:
                new_sector_name: str = 'Второй ярус'
            else:
                new_sector_name: str = sector_name
            if 'правая' in sector_name:
                sector_name: str = f'{new_sector_name}. Правая сторона, ложа ' + number_lozha
            else:
                sector_name: str = f'{new_sector_name}. Левая сторона, ложа ' + number_lozha
            row = ''
        elif 'Бельэтаж' in sector_name:
            sector_name: str = 'Балкон бельэтажа'

        return sector_name, row

    def _parse_seats(self) -> OutputData:
        json_data = self._request_to_all_place()

        places = self._get_place_from_json_data(json_data)

        prices_and_sectors = self._get_prices_and_sectors(json_data)

        output_data = self._get_output_data(places, prices_and_sectors)

        return output_data

    def _get_output_data(self, places_tickets: dict, prices_and_sectors: dict[str, tuple[str, int]]) -> OutputData:
        sectors_data = {}
        for places_tickets_row in places_tickets.values():
            for place_row, place_tickets_seat in places_tickets_row.items():
                for place_seat, place_data in place_tickets_seat.items():
                    if place_data['status'] != 'vacant':
                        continue
                    place_data_id = place_data['set']
                    place_sector, place_price = prices_and_sectors[place_data_id]

                    place_sector, place_row_new = self._reformat(place_sector, place_row, place_seat)

                    tickets = {(place_row_new, place_seat): place_price}

                    try:
                        old_tickets = sectors_data[place_sector]
                        sectors_data[place_sector] = old_tickets | tickets
                    except KeyError:
                        sectors_data[place_sector] = tickets

        for sector_name, tickets in sectors_data.items():
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_prices_and_sectors(self, json_data: json) -> dict[str, tuple[str, int]]:
        prices_and_sectors = {}
        data = json_data['sets']
        for id_price, price_and_sector in data.items():
            sector_name = price_and_sector['name']
            price = price_and_sector['prices'][0]['full']
            price = int(price.split('.')[0])

            price_and_sector = (sector_name, price)
            prices_and_sectors[id_price] = price_and_sector
        return prices_and_sectors

    def _get_place_from_json_data(self, json_data: json) -> dict:
        places = json_data['tickets']
        return places

    def _request_to_all_place(self) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'authorization': f'token {self.token}',
            'cache-control': 'no-cache',
            'content-length': '36',
            'content-type': 'application/json',
            'origin': 'https://ticketscloud.com',
            'pragma': 'no-cache',
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
            'event': self.event_id
        }
        r = self.session.post(self.url, headers=headers, json=data)
        return r.json()

    async def body(self):
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
