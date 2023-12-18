import random

from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession


class Lenkom(SeatsParser):
    event = 'tickets.afisha.ru'
    url_filter = lambda url: 'wl/54' in url and 'tickets.afisha.ru' in url
    proxy_check = SpecialConditions(url='https://tickets.afisha.ru/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, all_sectors):
        for sector in all_sectors:
            if sector['name'] == 'Бельэтаж (неудобное)':
                sector['name'] = 'Бельэтаж'

    def parse_seats(self, data):
        all_places = data.get('places')
        if all_places is None:
            return []

        total_sector = []
        all_sector = {}

        for place in all_places:
            price = place.get('price')
            if price != 0:
                sector = place.get('sector').get('name')
                row = place.get('row')
                seat = place.get('seat')

                if all_sector.get(sector):
                    dict_sector = all_sector[sector]
                    dict_sector[(row, seat,)] = price
                else:
                    all_sector[sector] = {(row, seat,): price}

        for sector, total_seats_row_prices in all_sector.items():
            total_sector.append(
                {
                    "name": sector,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def request_parser(self, data):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'content-length': '47',
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'tickets.afisha.ru',
            'origin': 'https://tickets.afisha.ru',
            'referer': 'https://tickets.afisha.ru/wl/54/api?building_id=undefined&cat_id=undefined&gclid=991064686.1676449618&site=lenkom.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.post(self.url, headers=headers, data=data)
        if r.status_code == 499:
            return None
        elif r.status_code != 200:
            message = f"<b>lenkom_seats response.status_code {r.status_code}\n{self.event_id = }</b>"
            self.send_message_to_telegram(message)
        return r.json()

    def get_seats(self):
        data = {
            "event_id": self.event_id,
            "user_token": f"167644{random.randint(1000000, 9999999)}-{random.randint(100000, 999999)}"
            # "user_token": "1676449721616-847937"
        }

        json_data = self.request_parser(data=data)
        if json_data is None:
            return []
        a_events = self.parse_seats(json_data)

        return a_events

    def body(self):
        all_sectors = self.get_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
