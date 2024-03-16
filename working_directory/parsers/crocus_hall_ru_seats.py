from requests.exceptions import ProxyError, JSONDecodeError
import re

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.manager.proxy.sessions import AsyncProxySession


class CrocusHall(AsyncSeatsParser):
    url_filter = lambda url: 'crocus2.kassir.ru' in url
    #proxy_check = SpecialConditions(url='https://crocus2.kassir.ru/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.widget_key = re.search(r'(?<=key\=)[\w\-]*', self.url)[0]
        self.event_id_ = re.search(r'(?<=eventId\=)\d+', self.url)[0]
        self.get_configuration_id = None
        self.count_error = 0

    async def before_body(self):
        self.session = AsyncProxySession(self)


    def reformat_sector_new(self, sector_name, sector_id=0):
        data_of_sector = {
            'd05d5dd9-431d-b7a6-d9e2-d37a9a169ac8': {
                '1': 'VIP-партер',
                '157': 'VIP-партер',
                '492': 'VIP-партер',
                '1122': 'Партер',
                '794': 'Партер',
                '648': 'Партер',
                '959': 'Партер',
                '1288': 'Партер',
                '1454': 'Партер',
                '1631': 'Партер',
                '1942': 'Партер',
                '2782': 'Бельэтаж',
                '2435': 'Бельэтаж',
                '2119': 'Бельэтаж',
                '2612': 'Бельэтаж',
                '2978': 'Бельэтаж',
                '5083': 'Балкон',
                '4587': 'Балкон',
                '3730': 'Балкон',
                '3254': 'Балкон',
                '5641': 'Балкон',
                '3423': 'Партер',
                '3095': 'Партер',
                '2949': 'Партер',
                '3260': 'Партер',
                '3589': 'Партер',
                '3755': 'Партер',
                '3932': 'Партер',
                '4243': 'Партер',
                # '2782': 'Бельэтаж',
                '4736': 'Бельэтаж',
                '4420': 'Бельэтаж',
                '4913': 'Бельэтаж',
                '5279': 'Бельэтаж',
                # '5083': 'Балкон',
                # '4587': 'Балкон',
                # '3730': 'Балкон',
                # '3254': 'Балкон',
                # '2388': 'Балкон',
                # '5083': 'Бельэтаж',
                '1830': 'Балкон',
                '1334': 'Балкон',
                '477': 'Балкон',
                # '1': 'Балкон',
                '2388': 'Балкон',
                '664': 'Бельэтаж',
                '317': 'Бельэтаж',
                # '1': 'Бельэтаж',
                '494': 'Бельэтаж',
                '860': 'Бельэтаж',
                '2965': 'Балкон',
                '2469': 'Балкон',
                '1612': 'Балкон',
                '1136': 'Балкон',
                '3523': 'Балкон',
                '4084': 'VIP-партер',
                '4240': 'VIP-партер',
                '4575': 'VIP-партер',
                '4731': 'Партер',
                '4823': 'Партер',
                '4917': 'Партер',
                '5063': 'Партер',
                '5156': 'Партер',
                '5248': 'Партер',
                '5417': 'Партер',
                '5714': 'Партер',
                '': ''
            },
            'bf88b4cd-6182-e26a-bebe-bcf3fd5a952a': {
                '4145': 'PLATINUM 5',
                '4166': 'PLATINUM',
                '4181': 'PLATINUM 4',
                '664': 'Бельэтаж',
                '317': 'Бельэтаж',
                '1': 'Бельэтаж',
                '494': 'Бельэтаж',
                '860': 'Бельэтаж',
                '2965': 'Балкон',
                '2469': 'Балкон',
                '1612': 'Балкон',
                '1136': 'Балкон',
                '3523': 'Балкон',
                '10643': 'PLATINUM 5',
                '10644': 'PLATINUM',
                '10645': 'PLATINUM 4',
                '6073': 'Бельэтаж',
                '5726': 'Бельэтаж',
                '5410': 'Бельэтаж',
                '5903': 'Бельэтаж',
                '6269': 'Бельэтаж',
                '8374': 'Балкон',
                '7878': 'Балкон',
                '7021': 'Балкон',
                '6545': 'Балкон',
                '8932': 'Балкон',
                '5409': 'VIP-партер',
                '3612': 'Бельэтаж',
                '3265': 'Бельэтаж',
                '2949': 'Бельэтаж',
                '3442': 'Бельэтаж',
                '3808': 'Бельэтаж',
                '1830': 'Балкон',
                '1334': 'Балкон',
                '477': 'Балкон',
                # '1': 'Балкон',
                '2388': 'Балкон',
                '1181': 'Бельэтаж',
                '834': 'Бельэтаж',
                '518': 'Бельэтаж',
                '1011': 'Бельэтаж',
                '1377': 'Бельэтаж',
                '3482': 'Балкон',
                '2986': 'Балкон',
                '2129': 'Балкон',
                '1653': 'Балкон',
                '4040': 'Балкон',
            },
            '3166df32-f9f2-e729-a9de-db7b70d39c68': {
                '5641': 'Балкон',
                '3254': 'Балкон',
                '3730': 'Балкон',
                '4587': 'Балкон',
                '5083': 'Балкон',
                '2978': 'Бельэтаж',
                '2612': 'Бельэтаж',
                '2119': 'Бельэтаж',
                '2435': 'Бельэтаж',
                '2782': 'Бельэтаж',
                '492': 'VIP-партер',
                '157': 'VIP-партер',
                '1': 'VIP-партер',
                '1942': 'Партер',
                '1631': 'Партер',
                '1454': 'Партер',
                '1288': 'Партер',
                '959': 'Партер',
                '648': 'Партер',
                '794': 'Партер',
                '1122': 'Партер',
            }
        }
        if 'SILVER' in sector_name:
            sector_name = sector_name.replace('SILVER', 'Silver')
        if 'PLATINUM' in sector_name:
            sector_name = sector_name.replace('PLATINUM', 'Platinum')
        if 'GOLD' in sector_name:
            sector_name = sector_name.replace('GOLD', 'Gold')
        if 'VIP Ложа' in sector_name:
            sector_name = sector_name.replace('VIP Ложа', 'VIP-ложа')
        if 'VIP партер' in sector_name:
            sector_name = sector_name.replace('VIP партер', 'VIP-партер')
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
                if old_sector_name == 'Балкон' and sector_name == 'VIP-партер':
                    sector_name = 'Балкон'
                elif old_sector_name == 'Балкон' and sector_name == 'Бельэтаж':
                    sector_name = 'Балкон'
                elif old_sector_name == 'Бельэтаж' and sector_name == 'VIP-партер':
                    sector_name = 'Бельэтаж'
                elif old_sector_name == 'Бельэтаж' and sector_name == 'Балкон':
                    sector_name = 'Бельэтаж'
        return sector_name

    async def parse_seats(self, json_data):
        total_sector = []

        sector_dance_floor = {}
        sectors_data = []
        all_sectors = json_data.get('sectors')
        for sector in all_sectors:
            sectors_tariffs_id = list(sector.get('availableQuantityByTariffs').keys())
            vip_dance_floors = any([i in sector['name'] for i in ['SILVER', 'PLATINUM', 'GOLD']])
            if len(sectors_tariffs_id) > 0 and \
                    (sector['name'] == 'Танцевальный партер' or sector['name'] == 'Фан зона' or
                     vip_dance_floors is True):
                sector_name = self.reformat_sector_new(sector['name'])
                #print(sector_name, 'dancefloors_')
                sectors_tariffs_id = sector.get('availableQuantityByTariffs')
                for tariff_id, amount in sectors_tariffs_id.items():
                    sector_dance_floor[sector_name] = (tariff_id, amount)
            else:
                [sectors_data.append(tariff_id) for tariff_id in sectors_tariffs_id]
        #print(sectors_data, 'sectors_data')

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
            #continue
            """ Фанзона, Танцевальный партер """
            tariff_id, amount = data
            price = tariffs_data[tariff_id]
            if isinstance(price, tuple):
                price = price[0]
            if 'Танцевальный партер' in sector_name:
                sector_name = 'Танцпол'
            #self.info(sector_name, price, amount, 'sector_name, price, amount dance_floor', sep=',')
            self.register_dancefloor(sector_name, price, amount)

        url = f'https://crocus2.kassir.ru/api/v1/halls/configurations/{self.get_configuration_id}?language=ru&phpEventId={self.event_id_}'
        get_all_seats = await self.request_parser(url)
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
            sector_name = self.reformat_sector_new(sector_name, sector_id)
            for row in rows:
                row_number = row.get('name')
                seats_in_row = row.get('seats')
                for seat in seats_in_row:
                    seat_id = seat.get('id')
                    seat_number = seat.get('number')
                    if 'Диваны на 6 персон' in sector_name:
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

    async def request_parser(self, url):
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
        
        r = await self.session.get(url, headers=headers)
        
        if r.status_code == 500:
            return None
        try:
            return r.json()
        except JSONDecodeError:
            message = f"<b>crocus_seats json_error {r.status_code} {self.url = }</b>"
            self.error(message)
            return None        

    async def get_seats(self):
        url = f'https://crocus2.kassir.ru/api/v1/events/{self.event_id_}?language=ru'
        get_configuration_id = await self.request_parser(url)
        if get_configuration_id is None:
            return []
        self.get_configuration_id = get_configuration_id.get('meta')
        if self.get_configuration_id is None:
            return []
        self.get_configuration_id = self.get_configuration_id.get('trHallConfigurationId')

        url = f'https://crocus2.kassir.ru/api/v1/events/{self.event_id_}/seats?language=ru&phpEventId={self.event_id_}'
        json_data = await self.request_parser(url)
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

        all_sectors = await self.parse_seats(json_data)

        return all_sectors

    async def body(self):
        all_sectors = await self.get_seats()

        for sector in all_sectors:
            #self.info(sector['name'],  len(sector['tickets']), 'for sector in all_sectors:')
            self.register_sector(sector['name'], sector['tickets'])
