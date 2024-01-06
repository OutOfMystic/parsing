import json

from bs4 import BeautifulSoup
from requests.exceptions import ProxyError

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class Luzhniki(AsyncSeatsParser):
    event = 'luzhniki.ru'
    url_filter = lambda url: 'msk.kassir.ru' in url and 'frame' in url
    proxy_check = SpecialConditions(url='https://msk.kassir.ru/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.count_error = 0

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, a_sectors):
        for sector in a_sectors:
            sector_name = sector['name']
            if 'ЛОЖА' in sector_name:
                all_split_sector_name = sector_name.split()
                sector['name'] = all_split_sector_name[0].title() + ' ' + ' '.join(all_split_sector_name[1:])
                if 'пер' in sector['name']:
                    all_split_sector_name = sector['name'].split()
                    sector['name'] = ' '.join(all_split_sector_name[:2]) + ' (целиком)'
            elif 'Танцевальный партер' in sector_name:
                sector['name'] = 'Танцпол'
            elif 'Фанзона' in sector_name:
                sector['name'] = 'Фан-зона'
            elif 'Сектор' not in sector_name:
                sector['name'] = 'Сектор ' + sector_name
            if ' (VIP)' in sector['name']:
                sector['name'] = sector['name'].replace(' (VIP)', '')
            if 'Вход' in sector['name']:
                if 'Ложа' not in sector['name']:
                    sector_name = sector['name'][:sector['name'].index(' Вход')]
                    sector_name = sector_name.replace('С', 'C').replace('А', 'A')
                    sector_name = sector_name.replace('В', 'B').replace('VIP ', '')
                    sector_name = sector_name.split()
                    sector['name'] = 'Сектор ' + sector_name[1][0] + ' ' + sector_name[1][1:]
                else:
                    sector_name = sector['name'][:sector['name'].index(' Вход')].replace('Сектор ', '')
                    sector['name'] = sector_name.replace('№', '')

    def parse_seats(self):
        total_sector = []

        soup = self.request_parser_to_all_sectors()
        id_to_requests = soup.find_all('script')[-1].text
        id_to_requests = double_split(id_to_requests, '"event_id":', ',"')
        sessid_and_key = soup.find('div', class_='site-wrapper')
        sessid = sessid_and_key.get('sessid')
        key = sessid_and_key.get('data-key')

        all_sector = soup.select('a.sector-item')
        for sector in all_sector:
            sector_name = sector.find('span', class_='name').text.strip()
            sector_data = sector.get('data-sector-id')

            json_data = self.request_to_seats(sessid, key, id_to_requests, sector_data)

            r_text = json_data.get('view')
            soup = BeautifulSoup(r_text, 'lxml')
            script_with_data = soup.find('script')
            if script_with_data is None:
                continue
                """ Фанзона, Танцевальный партер """
                data_about_dance_floor = json_data['sector']
                sector_name = data_about_dance_floor['name']
                price_zones = data_about_dance_floor['price_groups']
                for price_zone in price_zones.values():
                    price = price_zone['price']
                    amount = price_zone['count']
                    self.register_dancefloor(sector_name, price, amount)
                continue
            script_with_data = script_with_data.text
            data_in_script_js = double_split(script_with_data, ' = ', script_with_data[-1]).replace(';', '')
            data_in_script_js = json.loads(data_in_script_js)

            dict_price = {}
            all_price = data_in_script_js.get('sector').get('price_groups')
            for price in all_price.values():
                id_price = price.get('priceGroupId')
                price = price.get('price')
                dict_price[id_price] = price

            total_seats_row_prices = {}
            all_id_place = data_in_script_js.get('sector').get('soes')
            for id_place, data in all_id_place.items():
                price_id = data.get('lastPriceGroupId')
                price = dict_price[price_id]

                place = soup.select(f'polygon[kh\:id="{id_place}"]')[0]
                seat = place.get('kh:number')
                row = place.get('kh:rownumber')
                if seat is None or seat == '':
                    seat = '1'
                if row is None or row == '':
                    row = '1'

                total_seats_row_prices[(row, seat, )] = price

            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def request_to_seats(self, sessid, key, id_to_requests, sector_data):
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
        url = ('https://msk.kassir.ru/ru/frame/scheme/'
               f'sector?{sessid}&key={key}&id={id_to_requests}&sector={sector_data}&key={key}')
        r = await self.session.get(url, headers=headers)
        return r.json()

    def request_parser_to_all_sectors(self):
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
        r = await self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def main_body(self):
        all_sectors = self.parse_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])

    async def body(self):
        skip_url = [
            'https://msk.kassir.ru/koncert/ok-lujniki/leningrad_2023-09-16',
            'https://msk.kassir.ru/frame/entry/index?key=55be3cc8-8788-f514-a5c0-a4e3cb622598&type=E&id=1982322',
            'https://msk.kassir.ru/frame/entry/index?key=55be3cc8-8788-f514-a5c0-a4e3cb622598&type=E&id=1739738',
        ]
        if self.url in skip_url:
            return
        try:
            self.main_body()
            self.count_error = 0
        except Exception as error:
            if self.count_error == 10:
                raise Exception(error)
            self.count_error += 1
            raise ProxyError(error)
