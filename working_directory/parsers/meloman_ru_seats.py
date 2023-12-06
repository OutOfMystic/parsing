from typing import NamedTuple, Generator
import time

from bs4 import BeautifulSoup, Tag

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class MelomanRu(SeatsParser):
    event = 'meloman.ru'
    url_filter = lambda url: 'bigbilet.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if '3 Амф' in sector_name:
            sector_name = 'Третий амфитеатр'
        elif '2 Амф' in sector_name:
            sector_name = 'Второй амфитеатр'
        elif '1 Амф' in sector_name:
            sector_name = 'Первый амфитеатр'
        elif '2 ярус' in sector_name:
            sector_name = 'Балкон второго яруса'
        elif '1 ярус' in sector_name:
            sector_name = 'Балкон первого яруса'

        return sector_name

    def _parse_seats(self) -> OutputData:
        text_data = self._request_to_soup()

        free_sectors = self._get_free_sectors_from_soup(text_data)

        output_data = self._get_output_data(free_sectors)

        return output_data

    def _get_output_data(self, free_sectors: Generator[str, None, None]) -> OutputData:
        sectors_data = {}
        for sector in free_sectors:
            place_sector, tickets = self._get_place_data(sector)
            place_sector = self._reformat(place_sector)

            try:
                old_tickets = sectors_data[place_sector]
                sectors_data[place_sector] = tickets | old_tickets
            except KeyError:
                sectors_data[place_sector] = tickets

        for place_sector, tickets in sectors_data.items():
            yield OutputData(sector_name=place_sector, tickets=tickets)

    def _get_place_data(self, sector: str) -> tuple[str, dict[tuple[str, str], int]]:
        tickets = {}
        place_sector = double_split(sector, '<b>', '</b>')
        free_rows = self._get_free_rows_from_sector(sector)
        for row in free_rows:
            place_row = row.find('strong').text.strip().split()[-1]
            free_seats = row.findAll('p', class_='b-check-place')
            for seat in free_seats:
                place_seat = seat.find('b').text.strip().split()[-1]
                place_price = seat.find('strong').text.strip().replace(u'\xa0', '')
                tickets[(place_row, place_seat,)] = int(place_price)
        return place_sector, tickets

    def _get_free_rows_from_sector(self, sector: str) -> list[Tag]:
        free_rows = []
        tag_row = '<li class="b-list-level-2">'
        len_tag = len('<li class="b-list-level-2">')
        tag_ul = '</ul>'
        while True:
            try:
                row_index_start = sector.index(tag_row)
                row_index_end = sector[row_index_start+len_tag:].index(tag_row)
                row_index_end = row_index_end + row_index_start + len_tag
                row = sector[row_index_start+len_tag:row_index_end]
                sector = sector[row_index_end:]

                row = BeautifulSoup(row, 'lxml')
                free_rows.append(row)
            except ValueError:
                row_index_start = sector.index(tag_row)
                row_index_end = sector[row_index_start+len_tag:].index(tag_ul)
                row_index_end = row_index_end + row_index_start + len_tag
                row = sector[row_index_start+len_tag:row_index_end]

                row = BeautifulSoup(row, 'lxml')
                free_rows.append(row)
                break
        return free_rows

    def _get_free_sectors_from_soup(self, text_data: str) -> Generator[str, None, None]:
        len_tag = len('<li class="b-list-level-1">')
        tag_sector = '<li class="b-list-level-1">'
        tag_div = '<div class="legend"'
        while True:
            try:
                sector_index_start = text_data.index(tag_sector)
                sector_index_end = text_data[sector_index_start+len_tag:].index(tag_sector)
                sector_index_end = sector_index_end + sector_index_start + len_tag
                sector = text_data[sector_index_start+len_tag:sector_index_end]
                text_data = text_data[sector_index_end:]
                yield sector
            except ValueError:
                sector_index_start = text_data.index(tag_sector)
                sector_index_end = text_data[sector_index_start+len_tag:].index(tag_div)
                sector_index_end = sector_index_end + sector_index_start + len_tag
                sector = text_data[sector_index_start+len_tag:sector_index_end]
                yield sector
                break

    def _request_to_soup(self) -> str:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://meloman.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        return r.text

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
