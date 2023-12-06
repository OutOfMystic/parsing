from bs4 import BeautifulSoup
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession


class VtbArena(SeatsParser):
    event = 'newticket.vtb-arena.com'
    url_filter = lambda url: 'newticket.vtb-arena.com' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.scene = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, all_sectors):
        if self.scene == 'hokey':
            tribune_1 = '. Трибуна Давыдова'
            tribune_2 = '. Трибуна Васильева'
            tribune_3 = '. Трибуна Юрзинова'
            tribune_4 = '. Трибуна Мальцева'

            for sector in all_sectors:
                if 'Ложа' not in sector['name']:
                    sector['name'] = 'Сектор ' + sector['name'].replace(' ', '')
                sector_name = sector.get('name')
                if 'Ресторан' in sector_name:
                    sector['name'] = sector_name + tribune_3
                if 'Press' in sector_name or 'VVIP' in sector_name:
                    sector['name'] = sector_name + tribune_1
                if 'Сектор' in sector_name:
                    number_sector = int(sector_name[-3:])
                    if sector_name[-4] == 'A' and 100 < number_sector <= 110:
                        sector['name'] = sector_name + tribune_1
                        continue
                    if 300 < number_sector <= 303 or 200 < number_sector <= 203 or 100 < number_sector <= 103:
                        tribune = tribune_1 if sector_name[-4] == 'A' else tribune_3
                        sector['name'] = sector_name + tribune
                    elif 304 <= number_sector <= 309 or 204 <= number_sector <= 211 or 104 <= number_sector <= 108:
                        tribune = tribune_2 if sector_name[-4] == 'A' else tribune_4
                        sector['name'] = sector_name + tribune
                    elif 310 <= number_sector < 315 or 212 <= number_sector < 215 or 109 <= number_sector < 115:
                        tribune = tribune_3 if sector_name[-4] == 'A' else tribune_1
                        sector['name'] = sector_name + tribune
                if 'Ложа' in sector_name:
                    number_sector = int(sector_name[-2:])
                    if sector_name[-4] == 'A':
                        if 1 < number_sector <= 4:
                            sector['name'] = sector_name + tribune_1
                        elif 5 <= number_sector <= 17:
                            sector['name'] = sector_name + tribune_2
                        elif 18 <= number_sector < 2:
                            sector['name'] = sector_name + tribune_3
                    else:
                        if 1 < number_sector <= 5:
                            sector['name'] = sector_name + tribune_3
                        elif 6 <= number_sector <= 18:
                            sector['name'] = sector_name + tribune_4
                        elif 19 <= number_sector < 2:
                            sector['name'] = sector_name + tribune_1
        else:
            for sector in all_sectors:
                if 'VVIP' in sector['name']:
                    sector['name'] = 'VVIP'
                elif 'Танцпол' in sector['name']:
                    sector['name'] = 'Танцпол'
                if 'Фан-зона' in sector['name']:
                    sector['name'] = 'Фан-зона'
                elif 'Press' in sector['name']:
                    continue
                elif 'Ложа' not in sector['name'] and 'Партер' not in sector['name']:
                    sector['name'] = 'Сектор ' + sector['name'].replace(' ', '')
                    if '(ММГН)' in sector['name']:
                        sector['name'] = sector['name'][:sector['name'].index('(')] + ' (места для маломобильных групп населения)'
                    if 'Лаунж' in sector['name']:
                        sector['name'] = sector['name'][:sector['name'].index('(')] + '. Лаунж'

    def parse_seats(self, json_data):
        total_sector = []

        json_data = json_data.get('response')

        price_list = {}

        all_price = json_data.get('priceList')
        for price in all_price:
            price_name = price.get('zonename')
            price_count = int(price.get('price'))
            price_list[price_name] = price_count

        svg_data = json_data.get('blob')
        svg_data = BeautifulSoup(svg_data, 'xml')

        sector_with_seats_dict = {}

        if svg_data.find_all('ellipse'):
            self.scene = 'hokey'

        all_sector = svg_data.select('g[sector]')
        for g in all_sector:
            sector_name = g.get('data-sector')
            rows = g.find_all('g')
            for row in rows:
                seats_in_row = row.find_all('circle')
                row = row.get('data-row')
                for seat in seats_in_row:
                    price = seat.get('class')
                    if price != 'cat_1':
                        seat_in_row = seat.get('data-seat')
                        price = price_list[price]
                        if sector_with_seats_dict.get(sector_name):
                            dict_sector = sector_with_seats_dict[sector_name]
                            dict_sector[(row, seat_in_row,)] = price
                        else:
                            sector_with_seats_dict[sector_name] = {(row, seat_in_row,): price}

        for sector, total_seats_row_prices in sector_with_seats_dict.items():
            total_sector.append(
                {
                    "name": sector,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def request_parser(self, url, data):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'content-length': '61',
            'content-type': 'application/json;charset=UTF-8',
            'host': 'newticket.vtb-arena.com',
            'origin': 'https://newticket.vtb-arena.com',
            'referer': 'https://newticket.vtb-arena.com/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.post(url, headers=headers, json=data, verify=False)
        return r.json()

    def get_seats(self):
        url = 'https://newticket.vtb-arena.com/api/scheme'
        data = {
            "id": self.url.split('/')[-1],
            "lang": "ru"
        }
        json_data = self.request_parser(url=url, data=data)

        a_events = self.parse_seats(json_data)

        return a_events

    def body(self):
        all_sectors = self.get_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
