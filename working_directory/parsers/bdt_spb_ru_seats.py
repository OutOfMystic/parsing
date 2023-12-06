import json
from typing import NamedTuple

from requests import Response
from bs4 import BeautifulSoup
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class BdtSpb(SeatsParser):
    event: str = 'bdt.spb.ru'
    url_filter: str = lambda url: 'spb.ticketland.ru' in url and not 'aleksandrinskiy-teatr' in url
    proxy_check_url: str = 'https://spb.ticketland.ru/'

    def __init__(self, *args: list, **extra: dict) -> None:
        super().__init__(*args, **extra)
        self.delay: int = 1200
        self.driver_source: None = None

    def before_body(self) -> None:
        self.session: ProxySession = ProxySession(self)

    def _reformat(self, sector_name: str, row: str, seat: str) -> tuple[str, str]:
        if_seat_in_parter = [
            39, 40, 61, 62, 63, 64, 85, 86, 87, 88, 109, 110, 111, 112, 133, 134, 135, 136, 157, 158, 159, 160,
            181, 182, 183, 184, 205, 206, 207, 208, 229, 230, 231, 232, 253, 254, 255, 256, 277, 278, 279, 280,
            301, 302, 323
        ]
        if 'Партер' in sector_name and int(seat) in if_seat_in_parter:
            sector_name: str = 'Партер'
            # sector_name: str = 'Партер (неудобные места)'
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
        elif 'Ложа' in sector_name:
            number_lozha: str = sector_name.split()[1].replace('№', '')
            if 'бельэтажа' in sector_name:
                new_sector_name: str = 'Бельэтаж'
            elif 'бенуар' in sector_name:
                new_sector_name: str = 'Бенуар'
            elif '2-го яруса' in sector_name:
                new_sector_name: str = 'Второй ярус'
            else:
                new_sector_name: str = sector_name
            if 'правая' in sector_name:
                sector_name: str = f'{new_sector_name}. Правая сторона, ложа ' + number_lozha
            else:
                sector_name: str = f'{new_sector_name}. Левая сторона, ложа ' + number_lozha
        elif 'Бельэтаж' in sector_name:
            sector_name: str = 'Балкон бельэтажа'

        return sector_name, row

    def parse_seats(self) -> list[OutputData]:
        soup: BeautifulSoup = self._request_to_csrf()
        csrf: str = soup.find('meta', attrs={'name': 'csrf-token'}).get('content')
        data_to_url: str = soup.select('body script')[0].text
        data_to_url: str = double_split(data_to_url, 'webPageId: ', ',')

        url: str = (
            f'https://spb.ticketland.ru/hallview/map/{data_to_url}/'
            f'?json=1&all=1&isSpecialSale=0&tl-csrf={csrf}'
        )
        json_data: json = self._request_to_place(url)

        total_sector: list[OutputData] = self._get_output_data(json_data)

        return total_sector

    def _get_output_data(self, json_data: json) -> list[OutputData]:
        output_list: list[OutputData] = []

        all_seats_in_sectors: dict[str, dict[tuple[str, str], int]] = {}
        try:
            all_places: list = json_data.get('places')
        except AttributeError:
            return []
        for place in all_places:
            place_sector: str = place.get('section').get('name')

            place_seat: str = place.get('place')
            place_row: str = place.get('row')
            place_price: int = place.get('price')

            place_sector, place_row = self._reformat(place_sector, place_row, place_seat)

            if all_seats_in_sectors.get(place_sector):
                old_data: dict[tuple[str, str], int] = all_seats_in_sectors[place_sector]
                old_data[(place_row, place_seat)] = place_price
                all_seats_in_sectors[place_sector] = old_data
            else:
                all_seats_in_sectors[place_sector] = {(place_row, place_seat): place_price}

        for sector_name, tickets in all_seats_in_sectors.items():
            output_list.append(OutputData(sector_name=sector_name, tickets=tickets))

        return output_list

    def _request_to_place(self, url: str) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'spb.ticketland.ru',
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
        r: Response = self.session.get(url, headers=headers)
        return r.json()

    def _request_to_csrf(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'spb.ticketland.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r: Response = self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        try:
            all_sectors: list[OutputData] = self.parse_seats()

            for sector in all_sectors:
                self.register_sector(sector.sector_name, sector.tickets)
        except IndexError:
            return
