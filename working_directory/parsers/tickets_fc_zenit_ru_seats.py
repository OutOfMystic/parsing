import json
from typing import NamedTuple

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class TicketsFcZenit(AsyncSeatsParser):
    event = 'tickets.fc-zenit.ru'
    url_filter = lambda url: 'tickets.fc-zenit.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        tribuna = ''
        if 'Сектор A Газпромбанк Блок A106, Silver Club' == sector_name:
            sector_name = 'Сектор A106 Business club'
        elif 'Сектор A Газпромбанк Блок A107, Winline Diamond Club' == sector_name:
            sector_name = 'Сектор A107 Diamond club'
        elif 'Сектор A Газпромбанк Блок A108, Silver Club' == sector_name:
            sector_name = 'Сектор A108 Business club'
        elif 'Сектор C Winline Блок C108, Gold Club 1' == sector_name:
            sector_name = 'Сектор A108 Business club'
        elif 'Сектор C Winline Ложа 62' == sector_name:
            sector_name = 'Ложа 62 "Зенит"'
        elif 'Сектор' in sector_name:
            tribuna = sector_name.split()[1]
            index_sector = sector_name.index('Сектор')
            sector_name = sector_name[index_sector:]
            sector_name = sector_name.split()
            sector_name = f'{sector_name[0]} {sector_name[-1]}'
        if 'Фан-зона + Танцпол' in self.scheme.name:
            if 'Сектор' in sector_name:
                sector_name = sector_name.split()
                sector_name = f'{sector_name[0]} {tribuna}{sector_name[-1]}'
        else:
            if 'Сектор A107' == sector_name:
                sector_name = 'Сектор A107 Silver club'
            elif 'Сектор A108' == sector_name:
                sector_name = 'Сектор A108 Business club'
            elif 'Сектор C107' == sector_name:
                sector_name = 'Сектор C107 Gold'
            elif 'Сектор C108' == sector_name:
                sector_name = 'Сектор C108 Gold'
            elif 'Сектор A106' == sector_name:
                sector_name = 'Сектор A106 Business club'
            elif 'Сектор A105' == sector_name:
                sector_name = 'Сектор A105 Silver club'

        return sector_name

    def _parse_seats(self) -> OutputData:
        soup = self._request_to_json_data()

        json_data = self._get_json_data_from_soup(soup)

        price_data = self._get_price_zone_from_json_data(json_data)

        sectors_data = self._get_sectors_from_json_data(json_data)

        output_data = self._get_output_data(sectors_data, price_data)

        return output_data

    def _get_output_data(self, sectors_data: dict[int, str], price_data: dict[int, int]) -> OutputData:
        event_id = self.url.split('=')[1]
        for sector_id, sector_name in sectors_data.items():
            sector_name = self._reformat(sector_name)
            all_place_in_sector = {}

            url = f'https://tickets.fc-zenit.ru/api/internal/v1/page/map/{event_id}/sector/{sector_id}?'
            json_data = self._request_to_place(url)

            try:
                rows = json_data['payload']['sectorMap']['rows']
            except TypeError:  # Танцпол и фан зона
                continue
            for row in rows:
                row_number = row['number']
                if row_number == '':
                    continue

                seats = row['cells']
                for seat in seats:
                    if seat['type'] == 'seat':
                        seat = seat['seat']
                        if seat['isAvailable']:

                            seat_number = seat['number']
                            price_zone_id = seat['zoneId']
                            price = price_data[price_zone_id]
                            all_place_in_sector[(row_number, seat_number,)] = price

            yield OutputData(sector_name=sector_name, tickets=all_place_in_sector)

    def _get_sectors_from_json_data(self, json_data: json) -> dict[int, str]:
        output_sectors_data = {}

        all_sectors = json_data['stadiumMapAreas']
        for sector in all_sectors:
            is_available = sector['isAvailable']
            if is_available:
                sector_id = sector['bitrixSectorIds'][0]
                sector_name = sector['name']
                output_sectors_data[sector_id] = sector_name

        return output_sectors_data

    def _get_price_zone_from_json_data(self, json_data: json) -> dict[int, int]:
        output_price_data = {}

        all_price_zone = json_data['zones']
        for price_zone in all_price_zone:
            price_zone_id = price_zone['id']
            if price_zone_id == 999999999:
                continue
            price_for_this_price_zone = price_zone['prices'][0]['price']['value']
            output_price_data[price_zone_id] = price_for_this_price_zone

        return output_price_data

    def _get_json_data_from_soup(self, soup: BeautifulSoup) -> json:
        js_data_from_script_in_page = soup.select('main script')[0].text
        index_start = js_data_from_script_in_page.index('=') + 2
        json_data_from_script_in_page = js_data_from_script_in_page[index_start:]
        return json.loads(json_data_from_script_in_page)

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
            'connection': 'keep-alive',
            'host': 'tickets.fc-zenit.ru',
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
        r = self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self):
        skip_sector = [
            'Сектор ADIAMOND',
            'Сектор A236',
            'Сектор C117'
        ]
        for sector in list(self._parse_seats()):
            if sector.sector_name in skip_sector:
                continue
            self.register_sector(sector.sector_name, sector.tickets)
