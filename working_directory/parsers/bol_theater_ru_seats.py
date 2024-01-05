from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split, lrsplit
from bs4 import BeautifulSoup
import re


class BolTheaterParser(SeatsParser):
    url_filter = lambda event: 'bol-theater.ru' in event

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

        self.csrf = ''

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, a_sectors, place_name):
        main_scene_reformat_dict = {
            'Партер. Левая сторона': 'Партер Левая сторона',
            'Партер. Правая сторона': 'Партер Правая сторона',
            '': 'Балкон 4 яруса Левая сторона',
            '': 'Балкон 4 яруса Правая сторона',
            '3 ярус. Левая сторона. Ложа № 1': '3 ярус Левая сторона Ложа № 1',
            '3 ярус. Левая сторона. Ложа № 2': '3 ярус Левая сторона Ложа № 2',
            '3 ярус. Левая сторона. Ложа № 3': '3 ярус Левая сторона Ложа № 3',
            '3 ярус. Левая сторона. Ложа № 4': '3 ярус Левая сторона Ложа № 4',
            '3 ярус. Левая сторона. Ложа № 5': '3 ярус Левая сторона Ложа № 5',
            '3 ярус. Левая сторона. Ложа № 6': '3 ярус Левая сторона Ложа № 6',
            '3 ярус. Левая сторона. Ложа № 7': '3 ярус Левая сторона Ложа № 7',
            '3 ярус. Левая сторона. Ложа № 8': '3 ярус Левая сторона Ложа № 8',
            '3 ярус. Левая сторона. Ложа № 9': '3 ярус Левая сторона Ложа № 9',
            'Балкон 3 яруса. Левая сторона': 'Балкон 3 яруса',
            'Балкон 3 яруса. Правая сторона': 'Балкон 3 яруса',
            '3 ярус. Правая сторона. Ложа № 1': '3 ярус Правая сторона Ложа № 1',
            '3 ярус. Правая сторона. Ложа № 2': '3 ярус Правая сторона Ложа № 2',
            '3 ярус. Правая сторона. Ложа № 3': '3 ярус Правая сторона Ложа № 3',
            '3 ярус. Правая сторона. Ложа № 4': '3 ярус Правая сторона Ложа № 4',
            '3 ярус. Правая сторона. Ложа № 5': '3 ярус Правая сторона Ложа № 5',
            '3 ярус. Правая сторона. Ложа № 6': '3 ярус Правая сторона Ложа № 6',
            '3 ярус. Правая сторона. Ложа № 7': '3 ярус Правая сторона Ложа № 7',
            '3 ярус. Правая сторона. Ложа № 8': '3 ярус Правая сторона Ложа № 8',
            '3 ярус. Правая сторона. Ложа № 9': '3 ярус Правая сторона Ложа № 9',
            '2 ярус. Левая сторона. Ложа № 1': '2 ярус Левая сторона Ложа № 1',
            '2 ярус. Левая сторона. Ложа № 2': '2 ярус Левая сторона Ложа № 2',
            '2 ярус. Левая сторона. Ложа № 3': '2 ярус Левая сторона Ложа № 3',
            '2 ярус. Левая сторона. Ложа № 4': '2 ярус Левая сторона Ложа № 4',
            '2 ярус. Левая сторона. Ложа № 5': '2 ярус Левая сторона Ложа № 5',
            '2 ярус. Левая сторона. Ложа № 6': '2 ярус Левая сторона Ложа № 6',
            '2 ярус. Левая сторона. Ложа № 7': '2 ярус Левая сторона Ложа № 7',
            '2 ярус. Левая сторона. Ложа № 8': '2 ярус Левая сторона Ложа № 8',
            '2 ярус. Левая сторона. Ложа № 9': '2 ярус Левая сторона Ложа № 9',
            'Балкон 2 яруса. Левая сторона': 'Балкон 2 яруса Левая сторона',
            '2 ярус. Правая сторона. Ложа № 1': '2 ярус Правая сторона Ложа № 1',
            '2 ярус. Правая сторона. Ложа № 2': '2 ярус Правая сторона Ложа № 2',
            '2 ярус. Правая сторона. Ложа № 3': '2 ярус Правая сторона Ложа № 3',
            '2 ярус. Правая сторона. Ложа № 4': '2 ярус Правая сторона Ложа № 4',
            '2 ярус. Правая сторона. Ложа № 5': '2 ярус Правая сторона Ложа № 5',
            '2 ярус. Правая сторона. Ложа № 6': '2 ярус Правая сторона Ложа № 6',
            '2 ярус. Правая сторона. Ложа № 7': '2 ярус Правая сторона Ложа № 7',
            '2 ярус. Правая сторона. Ложа № 8': '2 ярус Правая сторона Ложа № 8',
            '2 ярус. Правая сторона. Ложа № 9': '2 ярус Правая сторона Ложа № 9',
            'Балкон 2 яруса. Правая сторона': 'Балкон 2 яруса Правая сторона',
            '1 ярус. Левая сторона. Ложа № 1': '1 ярус Левая сторона Ложа № 1',
            '1 ярус. Левая сторона. Ложа № 2': '1 ярус Левая сторона Ложа № 2',
            '1 ярус. Левая сторона. Ложа № 3': '1 ярус Левая сторона Ложа № 3',
            '1 ярус. Левая сторона. Ложа № 4': '1 ярус Левая сторона Ложа № 4',
            '1 ярус. Левая сторона. Ложа № 5': '1 ярус Левая сторона Ложа № 5',
            '1 ярус. Левая сторона. Ложа № 6': '1 ярус Левая сторона Ложа № 6',
            '1 ярус. Левая сторона. Ложа № 7': '1 ярус Левая сторона Ложа № 7',
            '1 ярус. Левая сторона. Ложа № 8': '1 ярус Левая сторона Ложа № 8',
            '1 ярус. Левая сторона. Ложа № 9': '1 ярус Левая сторона Ложа № 9',
            '1 ярус. Левая сторона. Ложа № 10': '1 ярус Левая сторона Ложа № 10',
            '1 ярус. Левая сторона. Ложа № 11': '1 ярус Левая сторона Ложа № 11',
            '1 ярус. Левая сторона. Ложа № 12': '1 ярус Левая сторона Ложа № 12',
            '1 ярус. Правая сторона. Ложа № 1': '1 ярус Правая сторона Ложа № 1',
            '1 ярус. Правая сторона. Ложа № 2': '1 ярус Правая сторона Ложа № 2',
            '1 ярус. Правая сторона. Ложа № 3': '1 ярус Правая сторона Ложа № 3',
            '1 ярус. Правая сторона. Ложа № 4': '1 ярус Правая сторона Ложа № 4',
            '1 ярус. Правая сторона. Ложа № 5': '1 ярус Правая сторона Ложа № 5',
            '1 ярус. Правая сторона. Ложа № 6': '1 ярус Правая сторона Ложа № 6',
            '1 ярус. Правая сторона. Ложа № 7': '1 ярус Правая сторона Ложа № 7',
            '1 ярус. Правая сторона. Ложа № 8': '1 ярус Правая сторона Ложа № 8',
            '1 ярус. Правая сторона. Ложа № 9': '1 ярус Правая сторона Ложа № 9',
            '1 ярус. Правая сторона. Ложа № 10': '1 ярус Правая сторона Ложа № 10',
            '1 ярус. Правая сторона. Ложа № 11': '1 ярус Правая сторона Ложа № 11',
            '1 ярус. Правая сторона. Ложа № 12': '1 ярус Правая сторона Ложа № 12',
            'Бельэтаж. Левая сторона. Ложа № 1': 'Бельэтаж Левая сторона Ложа № 1',
            'Бельэтаж. Левая сторона. Ложа № 2': 'Бельэтаж Левая сторона Ложа № 2',
            'Бельэтаж. Левая сторона. Ложа № 3': 'Бельэтаж Левая сторона Ложа № 3',
            'Бельэтаж. Левая сторона. Ложа № 4': 'Бельэтаж Левая сторона Ложа № 4',
            'Бельэтаж. Левая сторона. Ложа № 5': 'Бельэтаж Левая сторона Ложа № 5',
            'Бельэтаж. Левая сторона. Ложа № 6': 'Бельэтаж Левая сторона Ложа № 6',
            'Бельэтаж. Левая сторона. Ложа № 7': 'Бельэтаж Левая сторона Ложа № 7',
            'Бельэтаж. Левая сторона. Ложа № 8': 'Бельэтаж Левая сторона Ложа № 8',
            'Бельэтаж. Левая сторона. Ложа № 9': 'Бельэтаж Левая сторона Ложа № 9',
            'Бельэтаж. Левая сторона. Ложа № 10': 'Бельэтаж Левая сторона Ложа № 10',
            'Бельэтаж. Левая сторона. Ложа № 11': 'Бельэтаж Левая сторона Ложа № 11',
            'Бельэтаж. Левая сторона. Ложа № 12': 'Бельэтаж Левая сторона Ложа № 12',
            'Бельэтаж. Левая сторона. Ложа № 13': 'Бельэтаж Левая сторона Ложа № 13',
            'Бельэтаж. Левая сторона. Ложа № 14': 'Бельэтаж Левая сторона Ложа № 14',
            'Бельэтаж. Левая сторона. Ложа № 15': 'Бельэтаж Левая сторона Ложа № 15',
            'Бельэтаж. Правая сторона. Ложа № 1': 'Бельэтаж Правая сторона Ложа № 1',
            'Бельэтаж. Правая сторона. Ложа № 2': 'Бельэтаж Правая сторона Ложа № 2',
            'Бельэтаж. Правая сторона. Ложа № 3': 'Бельэтаж Правая сторона Ложа № 3',
            'Бельэтаж. Правая сторона. Ложа № 4': 'Бельэтаж Правая сторона Ложа № 4',
            'Бельэтаж. Правая сторона. Ложа № 5': 'Бельэтаж Правая сторона Ложа № 5',
            'Бельэтаж. Правая сторона. Ложа № 6': 'Бельэтаж Правая сторона Ложа № 6',
            'Бельэтаж. Правая сторона. Ложа № 7': 'Бельэтаж Правая сторона Ложа № 7',
            'Бельэтаж. Правая сторона. Ложа № 8': 'Бельэтаж Правая сторона Ложа № 8',
            'Бельэтаж. Правая сторона. Ложа № 9': 'Бельэтаж Правая сторона Ложа № 9',
            'Бельэтаж. Правая сторона. Ложа № 10': 'Бельэтаж Правая сторона Ложа № 10',
            'Бельэтаж. Правая сторона. Ложа № 11': 'Бельэтаж Правая сторона Ложа № 11',
            'Бельэтаж. Правая сторона. Ложа № 12': 'Бельэтаж Правая сторона Ложа № 12',
            'Бельэтаж. Правая сторона. Ложа № 13': 'Бельэтаж Правая сторона Ложа № 13',
            'Бельэтаж. Правая сторона. Ложа № 14': 'Бельэтаж Правая сторона Ложа № 14',
            'Бельэтаж. Правая сторона. Ложа № 15': 'Бельэтаж Правая сторона Ложа № 15',
            'Амфитеатр. Левая сторона': 'Амфитеатр Левая сторона',
            'Амфитеатр. Правая сторона': 'Амфитеатр Правая сторона',
            'Бенуар. Левая сторона. Ложа № 1': 'Бенуар Левая сторона Ложа № 1',
            'Бенуар. Левая сторона. Ложа № 2': 'Бенуар Левая сторона Ложа № 2',
            'Бенуар. Левая сторона. Ложа № 3': 'Бенуар Левая сторона Ложа № 3',
            'Бенуар. Левая сторона. Ложа № 4': 'Бенуар Левая сторона Ложа № 4',
            'Бенуар. Левая сторона. Ложа № 5': 'Бенуар Левая сторона Ложа № 5',
            'Бенуар. Левая сторона. Ложа № 6': 'Бенуар Левая сторона Ложа № 6',
            'Бенуар. Левая сторона. Ложа № 7': 'Бенуар Левая сторона Ложа № 7',
            'Бенуар. Левая сторона. Ложа № 8': 'Бенуар Левая сторона Ложа № 8',
            'Бенуар. Правая сторона. Ложа № 1': 'Бенуар Правая сторона Ложа № 1',
            'Бенуар. Правая сторона. Ложа № 2': 'Бенуар Правая сторона Ложа № 2',
            'Бенуар. Правая сторона. Ложа № 3': 'Бенуар Правая сторона Ложа № 3',
            'Бенуар. Правая сторона. Ложа № 4': 'Бенуар Правая сторона Ложа № 4',
            'Бенуар. Правая сторона. Ложа № 5': 'Бенуар Правая сторона Ложа № 5',
            'Бенуар. Правая сторона. Ложа № 6': 'Бенуар Правая сторона Ложа № 6',
            'Бенуар. Правая сторона. Ложа № 7': 'Бенуар Правая сторона Ложа № 7',
            'Бенуар. Правая сторона. Ложа № 8': 'Бенуар Правая сторона Ложа № 8',
        }

        new_scene_reformat_dict = {
            'Партер. Правая сторона': 'Партер, правая сторона',
            'Партер. Левая сторона': 'Партер, левая сторона',
            'Бенуар. Правая сторона. Ложа 1': 'Бенуар, правая сторона Ложа 1',
            'Бенуар. Левая сторона. Ложа 1': 'Бенуар,  левая сторона Ложа 1',
            'Амфитеатр. Правая сторона': 'Амфитеатр, правая сторона',
            'Амфитеатр. Левая сторона': 'Амфитеатр, левая сторона',
            'Бельэтаж. Правая сторона': 'Бельэтаж, правая сторона',
            'Бельэтаж. Правая сторона. Ложа 1': 'Бельэтаж, правая сторона Ложа 1',
            'Бельэтаж. Левая сторона': 'Бельэтаж, левая сторона',
            '1 ярус. Правая сторона': 'Первый ярус, правая сторона',
            '1 ярус. Левая сторона': 'Первый ярус, левая сторона',
            '1 ярус. Правая сторона. Ложа 1': 'Первый ярус, правая сторона Ложа 1',
            '1 ярус. Левая сторона. Ложа 1': 'Первый ярус, левая сторона Ложа 1',
        }

        ref_dict = {}
        if 'историч' in self.scene.lower():
            ref_dict = main_scene_reformat_dict
        elif 'новая' in self.scene.lower():
            ref_dict = new_scene_reformat_dict

        for sector in a_sectors:
            sector['name'] = ref_dict.get(sector['name'], sector['name'])

            if 'историч' in self.scene.lower() and 'Ложа' in sector['name']:
                self.reformat_bt_lozha_rows(sector)

    def reformat_bt_lozha_rows(self, sector):
        new_tickets = {}
        for row, seat in sector['tickets']:
            f_row = self.get_bt_lozha_row('', seat, sector['name'])
            new_tickets[f_row, seat] = sector['tickets'][row, seat]

        sector['tickets'] = new_tickets

    def get_bt_lozha_row(self, row, seat, sector_name):
        loz_row = row
        if not row or row == 'None':
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

    def get_event_seats(self):
        self.headers = {
            'authority': 'www.bileter.ru',
            'accept': 'text/html, */*; q=0.01',
            'accept-language': 'ru,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'referer': 'https://www.bileter.ru/afisha',
            'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-pjax': 'true',
            'x-pjax-container': '#js_id_afisha_performances_grid',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        r = self.session.get(self.url, headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')

        seats = []
        for ticket in soup.find_all('circle', class_='tickets_avail'):
            seats.append({
                'row': ticket.get('row'),
                'seat': ticket.get('place'),
                'price': ticket.get('price'),
                'sector_name': ticket.get('place-name')
            })

        return seats

    def body(self):
        seats = self.get_event_seats()

        a_sectors = []
        for ticket in seats:
            row = str(ticket['row'])
            seat = str(ticket['seat'])
            price = int(float(ticket['price']))
            sector_name = ticket['sector_name']
            for sector in a_sectors:
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': sector_name,
                    'tickets': {(row, seat): price}
                })

        self.reformat(a_sectors, '')

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])

