import random
from typing import NamedTuple, Optional, Union

from requests.exceptions import JSONDecodeError

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession

class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class AlexandrinskyRu(SeatsParser):
    event = 'alexandrinsky.ru'
    url_filter = lambda url: 'www.afisha.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str, place_row: str) -> tuple[str, str]:
        if 'Ложа бельэтажа' in sector_name:
            place_row = sector_name.split()[-1]
            place_row = 'Ложа ' + place_row
            sector_name = 'Бельэтаж'
        elif 'Ярус 1' in sector_name:
            place_row = sector_name.split('.')[0].split()[-1]
            place_row = 'Ложа ' + place_row
            sector_name = '1 ярус'
        elif 'Ярус 2' in sector_name:
            place_row = sector_name.split('.')[0].split()[-1]
            place_row = 'Ложа ' + place_row
            sector_name = '2 ярус'
        elif 'Ярус 3' in sector_name:
            place_row = sector_name.split('.')[0].split()[-1]
            place_row = 'Ложа ' + place_row
            sector_name = '3 ярус'
        elif 'Ярус 4' in sector_name:
            place_row = sector_name.split('.')[0].split()[-1]
            place_row = 'Ложа ' + place_row
            sector_name = '4 ярус'
        elif 'Балкон 3-го яруса' in sector_name:
            sector_name = 'Балкон 3го яруса'
        elif 'Царская ложа' == sector_name:
            place_row = '1'

        return sector_name, place_row

    def _parse_seats(self) -> Optional[Union[OutputData, list]]:
        json_data = self._request_to_all_place()
        if json_data is None:
            return []

        all_place = json_data.get('places', [])

        output_data = self._get_output_data(all_place)

        return output_data

    def _get_output_data(self, all_place: list[dict]) -> OutputData:
        sectors_data = {}
        for place in all_place:
            if place['active'] is False:
                continue
            sector_name = place['sector']['name']
            place_row = place['row']
            place_seat = place['seat']
            place_price = place['price']

            sector_name, place_row = self._reformat(sector_name, place_row)

            tickets = {(place_row, place_seat): place_price}

            try:
                old_tickets = sectors_data[sector_name]
                sectors_data[sector_name] = old_tickets | tickets
            except KeyError:
                sectors_data[sector_name] = tickets

        for sector_name, tickets in sectors_data.items():
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _request_to_all_place(self, count_error=0):
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
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        data = {
            "event_id": self.event_id,
            "user_token": f"167644{random.randint(1000000, 9999999)}-{random.randint(100000, 999999)}"
        }
        r = self.session.post(self.url, data=data, headers=headers)
        try:
            return r.json()
        except JSONDecodeError:
            if count_error == 5:
                return None
            return self._request_to_all_place(count_error=count_error+1)

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
