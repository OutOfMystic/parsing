import json
import time

from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils.parse_utils import double_split, lrsplit, contains_class, class_names_to_xpath
from parse_module.utils import utils


class BiletServisParser(AsyncSeatsParser):
    url_filter = lambda url: 'biletservis.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, sectors):
        for sector in sectors:
            if self.scene == 'Историческая сцена':
                sector['name'] = sector['name'].replace('.', '')
                if 'Балкон 3 яруса' in sector['name']:
                    sector['name'] = 'Балкон 3 яруса'
            elif self.scene == 'Новая сцена':
                sector['name'] = sector['name'].replace('.', ',')
                sector['name'] = sector['name'].replace(', Ложа', ' Ложа')
                sector['name'] = sector['name'].replace('1 ярус', 'Первый ярус')
                if sector['name'] == 'Бенуар, Левая сторона Ложа 1':
                    sector['name'] = 'Бенуар,  Левая сторона Ложа 1'

    def reformat_row(self, row, seat, sector_name):
        loz_row = row
        if not row or row == '0' or row == 'None':
            loz_row = '1'
        if 'Ложа' in sector_name:
            if 'Бенуар' in sector_name:
                if seat in ['1', '3', '5']:
                    loz_row = '1'
                else:
                    loz_row = '2'
            elif 'Бельэтаж' in sector_name:
                if seat in ['1', '3', '5']:
                    loz_row = '1'
                elif seat in ['2', '4', '6']:
                    loz_row = '2'
                else:
                    loz_row = '3'
            elif '1 ярус' in sector_name:
                if '1 ярус Левая сторона Ложа № 1' == sector_name or '1 ярус Правая сторона Ложа № 1' == sector_name:
                    if seat in ['1', '2', '3', '5', '7']:
                        loz_row = '1'
                    elif seat in ['4', '6', '8']:
                        loz_row = '2'
                elif '№ 10' in sector_name or '№ 11' in sector_name:
                    if seat in ['1', '3', '5']:
                        loz_row = '1'
                    elif seat in ['2', '4', '6']:
                        loz_row = '2'
                    else:
                        loz_row = '3'
                elif '№ 12' in sector_name:
                    pass
                else:
                    if seat in ['1', '3', '5']:
                        loz_row = '1'
                    else:
                        loz_row = '2'
            elif '2 ярус' in sector_name:
                if '№ 7' in sector_name or '№ 8' in sector_name or '№ 9' in sector_name:
                    if seat in ['1', '3', '5']:
                        loz_row = '1'
                    else:
                        loz_row = '2'
        return loz_row

    async def body(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,i'
                      'mage/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'biletservis.ru',
            'referer': self.url,
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        url = f'https://biletservis.ru/widget/index.php?action' \
              f'=get_svg&widget=1&date={self.sec_date}&event_id' \
              f'={self.event_id_cfg}&place_id={self.place_id}&' \
              f'hall_id={self.hall_id}&part_id='
              
        r_text = await self.session.get_text(url, headers=headers)

        elements = lrsplit(r_text, '<circle elem="true"', '/>', generator=True)
        a_elements = (elem for elem in elements if 'ticket-id' in elem)
        params = ['place-name', 'row', ' place', 'price']
        parsed_a_elems = (get_params(circle, params) for circle in a_elements)

        a_sectors = []
        sectors = utils.groupby(parsed_a_elems, lambda elem: elem[0])
        for sector_name, seats in sectors:
            a_seats = {}
            for _, row, seat, price in seats:
                row = self.reformat_row(row, seat, sector_name)
                key = (row, seat,)
                a_seats[key] = int(price)
            a_sector = {'name': sector_name, 'seats': a_seats}
            a_sectors.append(a_sector)

        self.reformat(a_sectors)
        for sector in a_sectors:
            self.register_sector(sector['name'], sector['seats'])


def get_params(circle, params):
    return [get_param(circle, param) for param in params]


def get_param(circle, param):
    return double_split(circle, f'{param}="', '"')
