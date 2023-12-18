import time

from parse_module.drivers.queue_to_big_theatre import queue_big_theatre, result_json
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession


class BolshoiParser(SeatsParser):
    proxy_check = SpecialConditions(url='https://ticket.bolshoi.ru/')
    event = 'ticket.bolshoi.ru'
    url_filter = lambda url: 'ticket.bolshoi.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, a_sectors):
        bolshoi_tickets_reformat_dict = {
            # Историческая сцена
            'Партер, левая сторона': 'Партер Левая сторона',
            'Партер, правая сторона': 'Партер Правая сторона',
            'Балкон 4 яруса, левая сторона': 'Балкон 4 яруса Левая сторона',
            'Балкон 4 яруса, правая сторона': 'Балкон 4 яруса Правая сторона',
            'Балкон 3 яруса, левая сторона': 'Балкон 3 яруса',
            'Балкон 3 яруса, правая сторона': 'Балкон 3 яруса',
            'Балкон 2 яруса, левая сторона': 'Балкон 2 яруса Левая сторона',
            'Балкон 2 яруса, правая сторона': 'Балкон 2 яруса Правая сторона',
            '3 ярус, левая сторона Ложа № 1': '3 ярус Левая сторона Ложа № 1',
            '3 ярус, левая сторона Ложа № 2': '3 ярус Левая сторона Ложа № 2',
            '3 ярус, левая сторона Ложа № 3': '3 ярус Левая сторона Ложа № 3',
            '3 ярус, левая сторона Ложа № 4': '3 ярус Левая сторона Ложа № 4',
            '3 ярус, левая сторона Ложа № 5': '3 ярус Левая сторона Ложа № 5',
            '3 ярус, левая сторона Ложа № 6': '3 ярус Левая сторона Ложа № 6',
            '3 ярус, левая сторона Ложа № 7': '3 ярус Левая сторона Ложа № 7',
            '3 ярус, левая сторона Ложа № 8': '3 ярус Левая сторона Ложа № 8',
            '3 ярус, левая сторона Ложа № 9': '3 ярус Левая сторона Ложа № 9',
            '3 ярус, правая сторона Ложа № 1': '3 ярус Правая сторона Ложа № 1',
            '3 ярус, правая сторона Ложа № 2': '3 ярус Правая сторона Ложа № 2',
            '3 ярус, правая сторона Ложа № 3': '3 ярус Правая сторона Ложа № 3',
            '3 ярус, правая сторона Ложа № 4': '3 ярус Правая сторона Ложа № 4',
            '3 ярус, правая сторона Ложа № 5': '3 ярус Правая сторона Ложа № 5',
            '3 ярус, правая сторона Ложа № 6': '3 ярус Правая сторона Ложа № 6',
            '3 ярус, правая сторона Ложа № 7': '3 ярус Правая сторона Ложа № 7',
            '3 ярус, правая сторона Ложа № 8': '3 ярус Правая сторона Ложа № 8',
            '3 ярус, правая сторона Ложа № 9': '3 ярус Правая сторона Ложа № 9',
            '2 ярус, левая сторона Ложа № 1': '2 ярус Левая сторона Ложа № 1',
            '2 ярус, левая сторона Ложа № 2': '2 ярус Левая сторона Ложа № 2',
            '2 ярус, левая сторона Ложа № 3': '2 ярус Левая сторона Ложа № 3',
            '2 ярус, левая сторона Ложа № 4': '2 ярус Левая сторона Ложа № 4',
            '2 ярус, левая сторона Ложа № 5': '2 ярус Левая сторона Ложа № 5',
            '2 ярус, левая сторона Ложа № 6': '2 ярус Левая сторона Ложа № 6',
            '2 ярус, левая сторона Ложа № 7': '2 ярус Левая сторона Ложа № 7',
            '2 ярус, левая сторона Ложа № 8': '2 ярус Левая сторона Ложа № 8',
            '2 ярус, левая сторона Ложа № 9': '2 ярус Левая сторона Ложа № 9',
            '2 ярус, правая сторона Ложа № 1': '2 ярус Правая сторона Ложа № 1',
            '2 ярус, правая сторона Ложа № 2': '2 ярус Правая сторона Ложа № 2',
            '2 ярус, правая сторона Ложа № 3': '2 ярус Правая сторона Ложа № 3',
            '2 ярус, правая сторона Ложа № 4': '2 ярус Правая сторона Ложа № 4',
            '2 ярус, правая сторона Ложа № 5': '2 ярус Правая сторона Ложа № 5',
            '2 ярус, правая сторона Ложа № 6': '2 ярус Правая сторона Ложа № 6',
            '2 ярус, правая сторона Ложа № 7': '2 ярус Правая сторона Ложа № 7',
            '2 ярус, правая сторона Ложа № 8': '2 ярус Правая сторона Ложа № 8',
            '2 ярус, правая сторона Ложа № 9': '2 ярус Правая сторона Ложа № 9',
            '1 ярус, левая сторона Ложа № 1': '1 ярус Левая сторона Ложа № 1',
            '1 ярус, левая сторона Ложа № 2': '1 ярус Левая сторона Ложа № 2',
            '1 ярус, левая сторона Ложа № 3': '1 ярус Левая сторона Ложа № 3',
            '1 ярус, левая сторона Ложа № 4': '1 ярус Левая сторона Ложа № 4',
            '1 ярус, левая сторона Ложа № 5': '1 ярус Левая сторона Ложа № 5',
            '1 ярус, левая сторона Ложа № 6': '1 ярус Левая сторона Ложа № 6',
            '1 ярус, левая сторона Ложа № 7': '1 ярус Левая сторона Ложа № 7',
            '1 ярус, левая сторона Ложа № 8': '1 ярус Левая сторона Ложа № 8',
            '1 ярус, левая сторона Ложа № 9': '1 ярус Левая сторона Ложа № 9',
            '1 ярус, левая сторона Ложа № 10': '1 ярус Левая сторона Ложа № 10',
            '1 ярус, левая сторона Ложа № 11': '1 ярус Левая сторона Ложа № 11',
            '1 ярус, левая сторона': '1 ярус Левая сторона Ложа № 12',
            '1 ярус, правая сторона Ложа № 1': '1 ярус Правая сторона Ложа № 1',
            '1 ярус, правая сторона Ложа № 2': '1 ярус Правая сторона Ложа № 2',
            '1 ярус, правая сторона Ложа № 3': '1 ярус Правая сторона Ложа № 3',
            '1 ярус, правая сторона Ложа № 4': '1 ярус Правая сторона Ложа № 4',
            '1 ярус, правая сторона Ложа № 5': '1 ярус Правая сторона Ложа № 5',
            '1 ярус, правая сторона Ложа № 6': '1 ярус Правая сторона Ложа № 6',
            '1 ярус, правая сторона Ложа № 7': '1 ярус Правая сторона Ложа № 7',
            '1 ярус, правая сторона Ложа № 8': '1 ярус Правая сторона Ложа № 8',
            '1 ярус, правая сторона Ложа № 9': '1 ярус Правая сторона Ложа № 9',
            '1 ярус, правая сторона Ложа № 10': '1 ярус Правая сторона Ложа № 10',
            '1 ярус, правая сторона Ложа № 11': '1 ярус Правая сторона Ложа № 11',
            '1 ярус, правая сторона': '1 ярус Правая сторона Ложа № 12',
            'Бельэтаж, левая сторона Ложа № 1': 'Бельэтаж Левая сторона Ложа № 1',
            'Бельэтаж, левая сторона Ложа № 2': 'Бельэтаж Левая сторона Ложа № 2',
            'Бельэтаж, левая сторона Ложа № 3': 'Бельэтаж Левая сторона Ложа № 3',
            'Бельэтаж, левая сторона Ложа № 4': 'Бельэтаж Левая сторона Ложа № 4',
            'Бельэтаж, левая сторона Ложа № 5': 'Бельэтаж Левая сторона Ложа № 5',
            'Бельэтаж, левая сторона Ложа № 6': 'Бельэтаж Левая сторона Ложа № 6',
            'Бельэтаж, левая сторона Ложа № 7': 'Бельэтаж Левая сторона Ложа № 7',
            'Бельэтаж, левая сторона Ложа № 8': 'Бельэтаж Левая сторона Ложа № 8',
            'Бельэтаж, левая сторона Ложа № 9': 'Бельэтаж Левая сторона Ложа № 9',
            'Бельэтаж, левая сторона Ложа № 10': 'Бельэтаж Левая сторона Ложа № 10',
            'Бельэтаж, левая сторона Ложа № 11': 'Бельэтаж Левая сторона Ложа № 11',
            'Бельэтаж, левая сторона Ложа № 12': 'Бельэтаж Левая сторона Ложа № 12',
            'Бельэтаж, левая сторона Ложа № 13': 'Бельэтаж Левая сторона Ложа № 13',
            'Бельэтаж, левая сторона Ложа № 14': 'Бельэтаж Левая сторона Ложа № 14',
            'Бельэтаж, левая сторона Ложа № 15': 'Бельэтаж Левая сторона Ложа № 15',
            'Бельэтаж, правая сторона Ложа № 1': 'Бельэтаж Правая сторона Ложа № 1',
            'Бельэтаж, правая сторона Ложа № 2': 'Бельэтаж Правая сторона Ложа № 2',
            'Бельэтаж, правая сторона Ложа № 3': 'Бельэтаж Правая сторона Ложа № 3',
            'Бельэтаж, правая сторона Ложа № 4': 'Бельэтаж Правая сторона Ложа № 4',
            'Бельэтаж, правая сторона Ложа № 5': 'Бельэтаж Правая сторона Ложа № 5',
            'Бельэтаж, правая сторона Ложа № 6': 'Бельэтаж Правая сторона Ложа № 6',
            'Бельэтаж, правая сторона Ложа № 7': 'Бельэтаж Правая сторона Ложа № 7',
            'Бельэтаж, правая сторона Ложа № 8': 'Бельэтаж Правая сторона Ложа № 8',
            'Бельэтаж, правая сторона Ложа № 9': 'Бельэтаж Правая сторона Ложа № 9',
            'Бельэтаж, правая сторона Ложа № 10': 'Бельэтаж Правая сторона Ложа № 10',
            'Бельэтаж, правая сторона Ложа № 11': 'Бельэтаж Правая сторона Ложа № 11',
            'Бельэтаж, правая сторона Ложа № 12': 'Бельэтаж Правая сторона Ложа № 12',
            'Бельэтаж, правая сторона Ложа № 13': 'Бельэтаж Правая сторона Ложа № 13',
            'Бельэтаж, правая сторона Ложа № 14': 'Бельэтаж Правая сторона Ложа № 14',
            'Бельэтаж, правая сторона Ложа № 15': 'Бельэтаж Правая сторона Ложа № 15',
            'Амфитеатр, левая сторона': 'Амфитеатр Левая сторона',
            'Амфитеатр, правая сторона': 'Амфитеатр Правая сторона',
            'Бенуар, левая сторона Ложа № 1': 'Бенуар Левая сторона Ложа № 1',
            'Бенуар, левая сторона Ложа № 2': 'Бенуар Левая сторона Ложа № 2',
            'Бенуар, левая сторона Ложа № 3': 'Бенуар Левая сторона Ложа № 3',
            'Бенуар, левая сторона Ложа № 4': 'Бенуар Левая сторона Ложа № 4',
            'Бенуар, левая сторона Ложа № 5': 'Бенуар Левая сторона Ложа № 5',
            'Бенуар, левая сторона Ложа № 6': 'Бенуар Левая сторона Ложа № 6',
            'Бенуар, левая сторона Ложа № 7': 'Бенуар Левая сторона Ложа № 7',
            'Бенуар, левая сторона Ложа № 8': 'Бенуар Левая сторона Ложа № 8',
            'Бенуар, правая сторона Ложа № 1': 'Бенуар Правая сторона Ложа № 1',
            'Бенуар, правая сторона Ложа № 2': 'Бенуар Правая сторона Ложа № 2',
            'Бенуар, правая сторона Ложа № 3': 'Бенуар Правая сторона Ложа № 3',
            'Бенуар, правая сторона Ложа № 4': 'Бенуар Правая сторона Ложа № 4',
            'Бенуар, правая сторона Ложа № 5': 'Бенуар Правая сторона Ложа № 5',
            'Бенуар, правая сторона Ложа № 6': 'Бенуар Правая сторона Ложа № 6',
            'Бенуар, правая сторона Ложа № 7': 'Бенуар Правая сторона Ложа № 7',
            'Бенуар, правая сторона Ложа № 8': 'Бенуар Правая сторона Ложа № 8'
        }
        bolshoi_tickets_reformat_dict_new_scene = {
            # Новая сцена
            'Партер, левая сторона': 'Партер, левая сторона',
            'Партер, правая сторона': 'Партер, правая сторона',
            'Амфитеатр, левая сторона': 'Амфитеатр, левая сторона',
            'Амфитеатр, правая сторона': 'Амфитеатр, правая сторона',
            'Бенуар, левая сторона Ложа 1': 'Бенуар,  левая сторона Ложа 1',
            'Бенуар, правая сторона Ложа 1': 'Бенуар, правая сторона Ложа 1',
            'Бенуар, левая сторона': 'Бенуар, левая сторона',
            'Бенуар, правая сторона': 'Бенуар, правая сторона',
            'Бельэтаж, правая сторона Ложа 1': 'Бельэтаж, правая сторона Ложа 1',
            'Бельэтаж, левая сторона': 'Бельэтаж, левая сторона',
            'Бельэтаж, правая сторона': 'Бельэтаж, правая сторона',
            '1 ярус, левая сторона Ложа 1': 'Первый ярус, левая сторона Ложа 1',
            '1 ярус, правая сторона Ложа 1': 'Первый ярус, правая сторона Ложа 1',
            '1 ярус, левая сторона': 'Первый ярус, левая сторона',
            '1 ярус, правая сторона': 'Первый ярус, правая сторона'
        }

        ref_dict = {}
        if 'большой театр' in self.venue.lower():
            if "Новая сцена" in self.scene:
                ref_dict = bolshoi_tickets_reformat_dict_new_scene
            else:
                ref_dict = bolshoi_tickets_reformat_dict

        for sector in a_sectors:
            sector['name'] = ref_dict.get(sector['name'], sector['name'])

    def reformat_row(self, row, seat, sector_name):
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
                if '1 ярус Левая сторона Ложа № 1' == sector_name:
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
                else:
                    loz_row = '1'
            elif '3 ярус' in sector_name:
                loz_row = '1'
        if self.scene == 'Новая сцена':
            if 'Бенуар' in sector_name:
                loz_row = '1'
        return loz_row

    def get_json(self):
        queue_big_theatre.put((self.proxy, self.url))

        start_time = time.time()
        ready_json = False
        while ready_json is False:
            ready_json = result_json.get(self.url, False)
            if time.time() - start_time > 1200:
                ready_json = None
                break
            if ready_json is False:
                time.sleep(5)
            elif isinstance(ready_json, str):
                message = f'<b>ticket_bolshoi_ru_seats error is {ready_json}</b>'
                self.send_message_to_telegram(message)
                ready_json = None
                del result_json[self.url]
                break
            else:
                del result_json[self.url]

        if ready_json is None:
            return self.get_json()
        return ready_json

    def parse_seats(self):
        ready_json = self.get_json()
        if not ready_json:
            return
        if isinstance(ready_json, str):
            ready_json = eval(ready_json)

        total_sector = []
        all_sector = {}
        for seats in ready_json:
            price = seats.get('ticketPrice')
            if price:
                sector_first_part = seats.get('hallRegionName')
                sector_second_part = seats.get('hallSideName')
                if sector_first_part is None:
                    sector_first_part = ''
                if sector_second_part is None:
                    sector_second_part = ''
                sector = sector_first_part + ', ' + sector_second_part.lower()

                seats_row = seats.get('seatRow')
                seats_number = seats.get('seatNumber')
                if seats_row is None:
                    seats_row = seats.get('hallSectionName')

                if self.scene == 'Новая сцена' and sector_first_part == 'Бельэтаж'\
                        and seats_row is not None and seats.get('hallSectionName') is not None:
                    sector += ' ' + seats.get('hallSectionName')

                if "Ложа" in seats_row:
                    sector += ' ' + seats_row

                seats_row = self.reformat_row(seats_row, seats_number, sector)

                if all_sector.get(sector):
                    dict_sector = all_sector[sector]
                    dict_sector[(seats_row, seats_number,)] = price
                else:
                    all_sector[sector] = {(seats_row, seats_number,): price}

        for sector, total_seats_row_prices in all_sector.items():
            total_sector.append(
                {
                    "name": sector,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def body(self):
        if 'https://ticket.bolshoi.ru/show/5101' == self.url and 'война и мир' in self.name.lower():
            return
        if not hasattr(self, 'scene'):
            return

        a_sectors = self.parse_seats()

        if not a_sectors:
            return

        self.reformat(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
