from typing import NamedTuple
import time
import json

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class Lokobasket(AsyncSeatsParser):
    event = 'lokobasket.qtickets.ru'
    url_filter = lambda url: 'lokobasket.qtickets.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = self.url.split('/')[-1]

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector: OutputData) -> OutputData:
        reformat = {
            'SECTOR1': 'Сектор 1',
            'SECTOR2': 'Сектор 2',
            'SECTOR3': 'Сектор 3',
            'SECTOR4': 'Сектор 4',
            'SECTOR5': 'Сектор 5',
            'SECTOR6': 'Сектор 6',
            'SECTOR7': 'Сектор 7',
            'SECTOR8': 'Сектор 8',
            'SECTOR9': 'Сектор 9',
            'SECTOR10': 'Сектор 10',
            'SECTOR11': 'Сектор 11',
            'SECTOR12': 'Сектор 12',
            'SECTOR13': 'Сектор 13',
            'SECTOR14': 'Сектор 14',
            'SECTOR15': 'Сектор 15',
            'SECTOR16': 'Сектор 16',
            'SECTOR17': 'Сектор 17',
            'PARKET1': 'Паркет 1',
            'PARKET2': 'Паркет 2',
            'PARKET3': 'Паркет 3',
            'PARKET4': 'Паркет 4',
            'LODGE1': 'Ложа 1',
            'LODGE2': 'Ложа 2',
            'LODGE3': 'Ложа 3',
            'LODGE4': 'Ложа 4',
            'LODGE5': 'Ложа 5',
            'LODGE6': 'Ложа 6',
            'LODGE7': 'Ложа 7',
            'LODGE8': 'Ложа 8',
            'LODGE9': 'Ложа 9',
            'LODGE10': 'Ложа 10',
        }
        sector = sector._replace(sector_name=reformat.get(sector.sector_name, sector.sector_name))

        return sector

    def _parse_seats(self) -> OutputData:
        soup, reuqest_text = self._request_to_soup()

        link_to_js, link_to_busy_seats = self._get_link_to_js_and_to_busy_seats_from_soup(soup, reuqest_text)

        js_code_all_place = self._reuest_to_js_all_place(link_to_js)

        all_place = self._get_all_place_from_js(js_code_all_place)

        json_data = self._reuest_to_plase_is_busy(link_to_busy_seats)

        places_is_busy = self._get_place_is_busy_from_json_data(json_data)

        output_data = self._get_output_data(all_place, places_is_busy)

        return output_data

    def _get_output_data(self, all_place: list[list], places_is_busy: list[list[str]]) -> OutputData:
        sectors_data = {}
        for place in all_place:
            if place[5] == '0':
                continue
            is_continue = False
            for index, place_is_busy in enumerate(places_is_busy):
                if place[0] == place_is_busy[0] and str(place[2]) == place_is_busy[1] and str(place[1]) == place_is_busy[2]:
                    del places_is_busy[index]
                    is_continue = True
                    break
            if is_continue is True:
                continue

            place_sector = place[0]
            place_row = str(place[2])
            place_seat = str(place[1])
            place_price = int(place[5])
            tickets = {(place_row, place_seat): place_price}

            try:
                old_tickets = sectors_data[place_sector]
                sectors_data[place_sector] = tickets | old_tickets
            except KeyError:
                sectors_data[place_sector] = tickets

        for place_sector, tickets in sectors_data.items():
            yield OutputData(sector_name=place_sector, tickets=tickets)

    def _get_place_is_busy_from_json_data(self, json_data: json) -> list[list[str]]:
        all_places_is_busy = []
        places_is_busy = json_data['ordered_seats']
        for place in places_is_busy.keys():
            sector_name, row_and_seat = place.split('-')
            row, seat = row_and_seat.split(';')
            data_about_place = [sector_name, row, seat]
            all_places_is_busy.append(data_about_place)
        return all_places_is_busy

    def _get_all_place_from_js(self, js_code_all_seats: str) -> list[list]:
        all_data_to_seats = double_split(js_code_all_seats, '(function(cfg){var ', '\n')
        all_data_to_seats = "{'" + all_data_to_seats.replace('null', 'None').replace(',', ",'").replace('=', "':") + '}'
        all_data_to_seats = eval(all_data_to_seats)
        for key, value in all_data_to_seats.items():
            exec(f'{key} = "{value}"')

        list_place = double_split(js_code_all_seats, 'var seats=', ';')
        list_place = eval(list_place)
        return list_place

    def _get_link_to_js_and_to_busy_seats_from_soup(self, soup: BeautifulSoup, reuqest_text: str) -> tuple[str, ...]:
        src_from_script = soup.select('head script[src^="/storage/temp/bundles/"]')[0].get('src')
        link_to_js = 'https://lokobasket.qtickets.ru' + src_from_script
        link_to_busy_seats = double_split(reuqest_text, '"seats_url":"\/widget\/', '",')
        link_to_busy_seats = 'https://lokobasket.qtickets.ru/widget/' + link_to_busy_seats
        return link_to_js, link_to_busy_seats

    def _reuest_to_plase_is_busy(self, url: str) -> json:
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
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

    def _reuest_to_js_all_place(self, url: str) -> str:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'script',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        return r.text

    def _request_to_soup(self) -> tuple[BeautifulSoup, str]:
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
        data = {
            'event_id': self.event_id,
            'widget_session': 'eLdgrITSBV3mAwGoJSD8MlBUIzM5rf0n4hyoJTHz'
        }
        r = self.session.post(self.url, headers=headers, data=data)
        return BeautifulSoup(r.text, 'lxml'), r.text

    def body(self) -> None:
        for sector in self._parse_seats():
            sector = self._reformat(sector)
            self.register_sector(sector.sector_name, sector.tickets)
