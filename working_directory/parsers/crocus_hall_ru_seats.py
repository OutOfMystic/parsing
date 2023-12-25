from requests.exceptions import ProxyError, JSONDecodeError
import re

from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split


class CrocusHall(SeatsParser):
    event = 'crocus-hall.ru'
    url_filter = lambda url: 'crocus2.kassir.ru' in url
    #proxy_check = SpecialConditions(url='https://crocus2.kassir.ru/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.widget_key = re.search(r'(?<=key\=)[\w\-]*', self.url)[0]
        self.event_id = re.search(r'(?<=eventId\=)\d+', self.url)[0]
        self.get_configuration_id = None
        self.count_error = 0

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, all_sectors):
        for sector in all_sectors:
            if 'VIP ЛОЖА' in sector['name'].upper():
                # if 'на' in sector['name'] and 'персон' in sector['name']:
                #     continue
                if 'VIP ЛОЖА SILVER 1' in sector['name'].upper() or 'VIP ЛОЖА SILVER №1' in sector['name'].upper():
                    sector['name'] = 'SILVER 1'
                elif 'VIP ЛОЖА SILVER 2' in sector['name'].upper() or 'VIP ЛОЖА SILVER №2' in sector['name'].upper():
                    sector['name'] = 'SILVER 2'
                elif 'VIP ЛОЖА SILVER 3' in sector['name'].upper() or 'VIP ЛОЖА SILVER №3' in sector['name'].upper():
                    sector['name'] = 'SILVER 3'
                elif 'VIP ЛОЖА PLATINUM 4' in sector['name'].upper() or 'VIP ЛОЖА PLATINUM №4' in sector['name'].upper():
                    sector['name'] = 'PLATINUM 4 '
                elif 'VIP ЛОЖА PLATINUM 5A' in sector['name'].upper() or 'VIP ЛОЖА PLATINUM №5A' in sector['name'].upper():
                    sector['name'] = 'PLATINUM'
                elif 'VIP ЛОЖА PLATINUM 5B' in sector['name'].upper() or 'VIP ЛОЖА PLATINUM №5B' in sector['name'].upper():
                    sector['name'] = 'PLATINUM 5'
                elif 'VIP ЛОЖА GOLD 6' in sector['name'].upper() or 'VIP ЛОЖА GOLD №6' in sector['name'].upper():
                    sector['name'] = 'GOLD 6'
                elif 'VIP ЛОЖА GOLD 7' in sector['name'].upper() or 'VIP ЛОЖА GOLD №7' in sector['name'].upper():
                    sector['name'] = 'GOLD 7'
                elif 'VIP ЛОЖА GOLD 8' in sector['name'].upper() or 'VIP ЛОЖА GOLD №8' in sector['name'].upper():
                    sector['name'] = 'GOLD 8'

    def reformat_sector(self, sector_name, sector_id):
        data_of_sector = {
            'd05d5dd9-431d-b7a6-d9e2-d37a9a169ac8': {
                '1': 'VIP партер 3',
                '157': 'VIP партер 2',
                '492': 'VIP партер 1',
                '1122': 'Партер 8',
                '794': 'Партер 7',
                '648': 'Партер 6',
                '959': 'Партер 5',
                '1288': 'Партер 4',
                '1454': 'Партер 3',
                '1631': 'Партер 2',
                '1942': 'Партер 1',
                '2782': 'Бельэтаж 5',
                '2435': 'Бельэтаж 4',
                '2119': 'Бельэтаж 3',
                '2612': 'Бельэтаж 2',
                '2978': 'Бельэтаж 1',
                '5083': 'Балкон 5',
                '4587': 'Балкон 4',
                '3730': 'Балкон 3',
                '3254': 'Балкон 2',
                '5641': 'Балкон 1',
                '3423': 'Партер 8',
                '3095': 'Партер 7',
                '2949': 'Партер 6',
                '3260': 'Партер 5',
                '3589': 'Партер 4',
                '3755': 'Партер 3',
                '3932': 'Партер 2',
                '4243': 'Партер 1',
                # '2782': 'Бельэтаж 5',
                '4736': 'Бельэтаж 4',
                '4420': 'Бельэтаж 3',
                '4913': 'Бельэтаж 2',
                '5279': 'Бельэтаж 1',
                # '5083': 'Балкон 5',
                # '4587': 'Балкон 4',
                # '3730': 'Балкон 3',
                # '3254': 'Балкон 2',
                # '2388': 'Балкон 1',
                # '5083': 'Бельэтаж 5',
                '1830': 'Балкон 5',
                '1334': 'Балкон 4',
                '477': 'Балкон 3',
                # '1': 'Балкон 2',
                '2388': 'Балкон 1',
                '664': 'Бельэтаж 5',
                '317': 'Бельэтаж 4',
                # '1': 'Бельэтаж 3',
                '494': 'Бельэтаж 2',
                '860': 'Бельэтаж 1',
                '2965': 'Балкон 5',
                '2469': 'Балкон 4',
                '1612': 'Балкон 3',
                '1136': 'Балкон 2',
                '3523': 'Балкон 1',
                '4084': 'VIP партер 3',
                '4240': 'VIP партер 2',
                '4575': 'VIP партер 1',
                '4731': 'Партер 8',
                '4823': 'Партер 7',
                '4917': 'Партер 6',
                '5063': 'Партер 5',
                '5156': 'Партер 4',
                '5248': 'Партер 3',
                '5417': 'Партер 2',
                '5714': 'Партер 1',
                '': ''
            },
            'bf88b4cd-6182-e26a-bebe-bcf3fd5a952a': {
                '4145': 'PLATINUM 5',
                '4166': 'PLATINUM',
                '4181': 'PLATINUM 4',
                '664': 'Бельэтаж 5',
                '317': 'Бельэтаж 4',
                '1': 'Бельэтаж 3',
                '494': 'Бельэтаж 2',
                '860': 'Бельэтаж 1',
                '2965': 'Балкон 5',
                '2469': 'Балкон 4',
                '1612': 'Балкон 3',
                '1136': 'Балкон 2',
                '3523': 'Балкон 1',
                '10643': 'PLATINUM 5',
                '10644': 'PLATINUM',
                '10645': 'PLATINUM 4',
                '6073': 'Бельэтаж 5',
                '5726': 'Бельэтаж 4',
                '5410': 'Бельэтаж 3',
                '5903': 'Бельэтаж 2',
                '6269': 'Бельэтаж 1',
                '8374': 'Балкон 5',
                '7878': 'Балкон 4',
                '7021': 'Балкон 3',
                '6545': 'Балкон 2',
                '8932': 'Балкон 1',
                '5409': 'VIP партер',
                '3612': 'Бельэтаж 5',
                '3265': 'Бельэтаж 4',
                '2949': 'Бельэтаж 3',
                '3442': 'Бельэтаж 2',
                '3808': 'Бельэтаж 1',
                '1830': 'Балкон 5',
                '1334': 'Балкон 4',
                '477': 'Балкон 3',
                # '1': 'Балкон 2',
                '2388': 'Балкон 1',
                '1181': 'Бельэтаж 5',
                '834': 'Бельэтаж 4',
                '518': 'Бельэтаж 3',
                '1011': 'Бельэтаж 2',
                '1377': 'Бельэтаж 1',
                '3482': 'Балкон 5',
                '2986': 'Балкон 4',
                '2129': 'Балкон 3',
                '1653': 'Балкон 2',
                '4040': 'Балкон 1',
            },
            '3166df32-f9f2-e729-a9de-db7b70d39c68': {
                '5641': 'Балкон 1',
                '3254': 'Балкон 2',
                '3730': 'Балкон 3',
                '4587': 'Балкон 4',
                '5083': 'Балкон 5',
                '2978': 'Бельэтаж 1',
                '2612': 'Бельэтаж 2',
                '2119': 'Бельэтаж 3',
                '2435': 'Бельэтаж 4',
                '2782': 'Бельэтаж 5',
                '492': 'VIP партер 1',
                '157': 'VIP партер 2',
                '1': 'VIP партер 3',
                '1942': 'Партер 1',
                '1631': 'Партер 2',
                '1454': 'Партер 3',
                '1288': 'Партер 4',
                '959': 'Партер 5',
                '648': 'Партер 6',
                '794': 'Партер 7',
                '1122': 'Партер 8',
            }
        }
        if 'Диваны на 6 персон' == sector_name:
            sector_name = 'Диваны на 6 персон'
        elif 'Стол на 4 персоны' == sector_name:
            sector_name = 'Столы на 4 персоны'
        else:
            get_widget = data_of_sector.get(self.widget_key)
            if get_widget is None:
                sector_name = sector_name
            else:
                old_sector_name = sector_name
                sector_name = get_widget.get(sector_id, old_sector_name)
                if old_sector_name == 'Балкон' and sector_name == 'VIP партер 3':
                    sector_name = 'Балкон 2'
                elif old_sector_name == 'Балкон' and sector_name == 'Бельэтаж 3':
                    sector_name = 'Балкон 2'
                elif old_sector_name == 'Бельэтаж' and sector_name == 'VIP партер 3':
                    sector_name = 'Бельэтаж 3'
                elif old_sector_name == 'Бельэтаж' and sector_name == 'Балкон 5':
                    sector_name = 'Бельэтаж 5'
        return sector_name

    def parse_seats(self, json_data):
        total_sector = []

        sector_dance_floor = {}
        sectors_data = []
        all_sectors = json_data.get('sectors')
        for sector in all_sectors:
            sectors_tariffs_id = list(sector.get('availableQuantityByTariffs').keys())
            if len(sectors_tariffs_id) > 0 and \
                    (sector['name'] == 'Танцевальный партер' or sector['name'] == 'Фан зона'):
                sectors_tariffs_id = sector.get('availableQuantityByTariffs')
                for tariff_id, amount in sectors_tariffs_id.items():
                    sector_dance_floor[sector['name']] = (tariff_id, amount)
            [sectors_data.append(tariff_id) for tariff_id in sectors_tariffs_id]

        tariffs_data = {}
        all_tariffs = json_data.get('tariffs')
        for tariff in all_tariffs:
            tariff_id = str(tariff.get('id'))
            tariff_available_seats = tariff.get('availableSeats')
            if len(tariff_available_seats) == 0:
                tariff_available_seats = [tariff.get('id')]
            tariff_price = tariff.get('price')
            tariffs_data[tariff_id] = (tariff_price, tariff_available_seats,)

        for sector_name, data in sector_dance_floor.items():
            continue
            """ Фанзона, Танцевальный партер """
            tariff_id, amount = data
            price = tariffs_data[tariff_id]
            self.register_dancefloor(sector_name, price, amount)

        url = f'https://crocus2.kassir.ru/api/v1/halls/configurations/{self.get_configuration_id}?language=ru&phpEventId={self.event_id}'
        get_all_seats = self.request_parser(url)
        if get_all_seats is None:
            return []

        all_id_seat = {}
        all_seats_in_sector = get_all_seats.get('data').get('sectors')
        for seats_in_sector in all_seats_in_sector:
            sector_name = seats_in_sector.get('name')
            sector_id = str(seats_in_sector.get('id'))
            rows = seats_in_sector.get('rows')
            if rows is None:
                continue
            sector_name = self.reformat_sector(sector_name, sector_id)
            for row in rows:
                row_number = row.get('name')
                seats_in_row = row.get('seats')
                for seat in seats_in_row:
                    seat_id = seat.get('id')
                    seat_number = seat.get('number')
                    if sector_name == 'Диваны на 6 персон 2':
                        seat_number = f'Диван {seat_number}'
                    all_id_seat[seat_id] = {sector_name: (str(row_number), str(seat_number),)}

        final_data = {}
        for tariff_id in sectors_data:
            price, seats_list_is_real = tariffs_data.get(tariff_id)
            for seat_id in seats_list_is_real:
                this_seat_data = all_id_seat.get(seat_id)
                if this_seat_data is None:
                    continue
                sector_name = list(this_seat_data.keys())[0]
                row_and_seat = tuple(this_seat_data.values())[0]
                real_place_in_sector = {row_and_seat: int(price)}
                if final_data.get(sector_name):
                    this_sector = final_data[sector_name]
                    this_sector[row_and_seat] = int(price)
                    final_data[sector_name] = this_sector
                else:
                    final_data[sector_name] = real_place_in_sector

        for sector_name, total_seats_row_prices in final_data.items():
            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def request_parser(self, url):
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'referer': self.url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'Host': 'crocus2.kassir.ru',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-widget-key': self.widget_key
        }
        r = self.session.get(url, headers=headers)
        if r.status_code == 500:
            return None
        try:
            return r.json()
        except JSONDecodeError:
            message = f"<b>crocus_seats json_error {r.status_code} {self.url = }</b>"
            self.send_message_to_telegram(message)
            return None

    def get_seats(self):
        url = f'https://crocus2.kassir.ru/api/v1/events/{self.event_id}?language=ru'
        get_configuration_id = self.request_parser(url)
        if get_configuration_id is None:
            return []
        self.get_configuration_id = get_configuration_id.get('meta')
        if self.get_configuration_id is None:
            return []
        self.get_configuration_id = self.get_configuration_id.get('trHallConfigurationId')

        url = f'https://crocus2.kassir.ru/api/v1/events/{self.event_id}/seats?language=ru&phpEventId={self.event_id}'
        json_data = self.request_parser(url)
        if json_data is None:
            return []

        json_data = json_data.get('data')
        if json_data is None and self.count_error < 10:
            self.count_error += 1
            raise ProxyError('crocus_seats error: json_data is None')
        elif json_data is None and self.count_error == 10:
            self.count_error = 0
            raise Exception('crocus_seats error: json_data is None')
        self.count_error = 0

        all_sectors = self.parse_seats(json_data)

        return all_sectors

    def body(self):
        all_sectors = self.get_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
