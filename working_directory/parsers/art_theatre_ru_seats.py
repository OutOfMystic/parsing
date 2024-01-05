from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Gorkovo(SeatsParser):
    event = 'art-theatre.ru'
    url_filter = lambda url: 'art-theatre.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, a_sectors):
        for sector in a_sectors:
            if sector['name'] == 'VIP Партер':
                sector['name'] = 'VIP-партер'

    def parse_seats(self):
        total_sector = []
        all_sector = {}
        json_data = self.request_parser()
        json_data_place = json_data['canvas_data']['active']

        for place in json_data_place:
            price = place.get('price')
            sector = place.get('section_name')
            row = place.get('row')
            seat = place.get('seat')

            if 'Ложа' in sector:
                side = place.get('section_side')
                if 'лев' in side:
                    side = 'левая сторона'
                elif 'пр' in side:
                    side = 'правая сторона'
                sector = sector + ' ' + row + ' ' + side
                row = '1'

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

    def request_parser(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            # 'referer': 'https://art-theatre.ru/afisha/2023/05/?date=1680296400388&page=1',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        event_id = self.url.split('=')[-1]
        url = f'https://sold-out.tech/9a5ff36b1b791638a0de57595960bd91/data/get-performance?event_id={event_id}'
        r = self.session.get(url, headers=headers)
        return r.json()

    def body(self):
        all_sectors = self.parse_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
