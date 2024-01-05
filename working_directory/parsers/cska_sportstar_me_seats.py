import json
from typing import NamedTuple

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class CskaSportstar(SeatsParser):
    url_filter = lambda url: 'cska.sportstar.me' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = int(self.url.split('/')[-1])

    def before_body(self):
        self.session = ProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        if 'ПСБ' in sector_name:
            sector_name = 'ПСБ'
        elif 'Сектор' in sector_name:
            index_sector = sector_name.index('Сектор')
            sector_name = sector_name[index_sector:]
        elif 'Ложа' in sector_name:
            index_sector = sector_name.index('Ложа')
            sector_name = sector_name[index_sector:]
        if 'Лужники' in self.scheme.name:
            if 'Сектор' in sector_name:
                sector_name = sector_name.split()
                sector_name = sector_name[0] + ' ' + sector_name[1][0] + ' ' + sector_name[1][1:]

        return sector_name

    def _parse_seats(self) -> OutputData:
        json_data = self._request_to_get_free_sectors()

        sectors = self._get_sectors_from_json_data(json_data)

        output_data = self._get_output_data(sectors)

        return output_data

    def _get_output_data(self, sectors: list[dict]) -> OutputData:
        for sector in sectors:
            is_busy = sector['quantity']
            if is_busy is None:
                continue
            sector_name = sector['name']
            sector_name = self._reformat(sector_name)
            sector_id = sector['sectorId']
            sector_key = sector['key']

            json_data_about_places = self._request_to_places(sector_id, sector_key)

            yield self._get_output_data_from_json(sector_name, json_data_about_places)

    def _get_output_data_from_json(self, sector_name: str, json_data_about_place) -> OutputData:
        tickets = {}

        all_row = self._get_all_row_from_json_data(json_data_about_place)
        for row in all_row:
            place_row, all_place = self._get_all_place_from_row(row)
            for place in all_place:
                place_price = place['price']
                if place_price is None:
                    continue
                place_seat = str(place['seat'])
                tickets[(place_row, place_seat, )] = place_price

        return OutputData(sector_name=sector_name, tickets=tickets)

    def _get_all_place_from_row(self, row: dict) -> tuple[str, list[dict]]:
        all_place = row['seats']
        place_row = str(row['row'])
        return place_row, all_place

    def _get_all_row_from_json_data(self, json_data: json) -> list[dict]:
        all_row = json_data['data']['eventSectorSeats']
        return all_row

    def _get_sectors_from_json_data(self, json_data: json) -> list[dict]:
        sectors = json_data['data']['eventSectors']
        return sectors

    def _request_to_places(self, sector_id: int, sector_key: str) -> BeautifulSoup:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-length': '572',
            'content-type': 'application/json',
            'host': 'cska.sportstar.me',
            'origin': 'https://cska.sportstar.me',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-session-id': 'P35gJyZ7VW6BON-M'
        }
        data = {
            'operationName': 'eventSectorSeats',
            'query': "query eventSectorSeats($eventId: Int!, $sectorId: Int!, $sectorKey: String) {\n  eventSectorSeats(eventId: $eventId, sectorId: $sectorId, sectorKey: $sectorKey) {\n    ...eventSectorRow\n    __typename\n  }\n}\n\nfragment eventSectorRow on EventSectorRow {\n  row\n  seats {\n    ...eventSectorSeat\n    __typename\n  }\n  __typename\n}\n\nfragment eventSectorSeat on EventSectorSeat {\n  seatId\n  name\n  row\n  seat\n  price\n  isReserved\n  __typename\n}\n",
            'variables': {
                'eventId': self.event_id,
                'sectorId': sector_id,
                'sectorKey': sector_key
            }
        }
        url = 'https://cska.sportstar.me/graphql'
        r = self.session.post(url, json=data, headers=headers)
        return r.json()

    def _request_to_get_free_sectors(self) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-length': '859',
            'content-type': 'application/json',
            'host': 'cska.sportstar.me',
            'origin': 'https://cska.sportstar.me',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        data = {
            'operationName': 'eventSectors',
            'query': "query eventSectors($eventId: Int!, $sectorId: [Int!]) {\n  eventSectors(eventId: $eventId, sectorId: $sectorId) {\n    ...eventSector\n    __typename\n  }\n}\n\nfragment eventSector on EventSector {\n  key\n  name\n  quantity\n  category\n  isSectorSaleEnabled\n  discountAvailableSlots\n  discountSectorPrice {\n    ...eventSectorPrice\n    __typename\n  }\n  eventSectorPrice {\n    ...eventSectorPrice\n    __typename\n  }\n  loyaltyDiscount {\n    ...loyaltyDiscount\n    __typename\n  }\n  sectorId\n  rotation\n  __typename\n}\n\nfragment eventSectorPrice on EventSectorPrice {\n  priceCategoryId\n  priceMin\n  priceMax\n  priceDiscount\n  __typename\n}\n\nfragment loyaltyDiscount on LoyaltyDiscount {\n  order {\n    id\n    __typename\n  }\n  discountPercent\n  __typename\n}\n",
            'variables': {'eventId': self.event_id}
        }
        url = 'https://cska.sportstar.me/graphql'
        r = self.session.post(url, json=data, headers=headers)
        return r.json()

    def body(self) -> None:
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
