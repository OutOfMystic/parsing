from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split
from bs4 import BeautifulSoup
import re


class Parser(SeatsParser):
    event = 'tickets-star.com'
    url_filter = lambda event: 'tickets-star.com' in event
    proxy_check_url = 'https://www.tickets-star.com/'

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def get_f_sectors(self, sectors, get_f_name=None, add_sec=False):
        to_del = []
        to_add = []

        for i, sector in enumerate(sectors):
            sector['name'] = sector['name'].replace('  ', ' ')
            sector['name'] = sector['name'].capitalize()

            if get_f_name:
                if not add_sec:
                    f_name = get_f_name(sector, sector['name'], sector['seats'], self.scene)
                else:
                    f_name, new_secs = get_f_name(sectors, sector['name'], sector['seats'], self.scene)
                    to_add += new_secs

                if f_name is False:
                    to_del.append(i)
                    continue
                else:
                    sector['name'] = f_name

        for i in to_del[::-1]:
            del sectors[i]

        sectors += to_add

    def reformat(self, a_sectors, theatre):
        get_f_name = False
        add_sec = False

        if 'ленком' in theatre:
            missing_sectors = []

            for sector in a_sectors:
                sector['name'] = sector['name'].capitalize()

                # if sector['name'] == 'Бельэтаж':
                #     missing_uncomfy_seats = {}
                #     for row, seat in sector['seats'].keys():
                #         if row in [1, 2] and seat in [1, 2, 17, 18]:
                #             missing_uncomfy_seats[row, seat] = sector['seats'][row, seat]
                #
                #     for row_seat in missing_uncomfy_seats.keys():
                #         del sector['seats'][row_seat]
                #
                #     missing_sectors.append({
                #         'name': 'Бельэтаж (неудобное) 2',
                #         'seats': missing_uncomfy_seats
                #     })

                if 'Бельэтаж (неудоб' in sector['name']:
                    missing_uncomfy_seats = {}
                    for row, seat in sector['seats'].keys():
                        if row in [1, 2] and seat in [1, 2, 17, 18]:
                            missing_uncomfy_seats[row, seat] = sector['seats'][row, seat]

                    for row_seat in missing_uncomfy_seats.keys():
                        del sector['seats'][row_seat]

                    missing_sectors.append({
                        'name': 'Бельэтаж',
                        'seats': missing_uncomfy_seats
                    })

            for missing_sector in missing_sectors:
                a_sectors.append(missing_sector)

        elif 'фоменко' in theatre:
            # TODO балкон отсутствует на нашей схеме
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Старая Сцена, Зеленый Зал (2 ряда)
                if 'партер' in sector_name_l:
                    f_sector_name = sector_name.replace(' правый', '').replace(' левый', '')
                if 'ложа балкона левая' in sector_name_l:
                    f_sector_name = 'Правая ложа балкона'
                if 'ложа балкона правая' in sector_name_l:
                    f_sector_name = 'Левая ложа балкона'

                return f_sector_name

        elif 'станиславского' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Основная сцена
                if 'ложа' in sector_name_l:
                    if 'бенуара' in sector_name_l:
                        lozha_num = sector_name.split()[-1]
                        f_sector_name = f'Ложа {lozha_num}'

                return f_sector_name

        elif 'мхт' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Основная сцена
                # TODO не все сектора проверены ввиду отсутствия билетов на сайте
                # TODO (все откидные; Бельэтаж кроме лож, Балкон лев и прав не оттестированы)
                if 'бенуар' in sector_name_l:
                    if 'ложа' in sector_name_l:
                        if 'прав' in sector_name:
                            f_sector_name = 'Бенуар, ложа правая'
                        elif 'лев' in sector_name:
                            f_sector_name = 'Бенуар, ложа левая'

                        self.set_tickets_row(sector, '0')

                elif 'бельэтаж' in sector_name_l:
                    if 'ложа' in sector_name_l:
                        if 'прав' in sector_name:
                            f_sector_name = 'Бельэтаж, ложа правая'
                        elif 'лев' in sector_name:
                            f_sector_name = 'Бельэтаж, ложа левая'

                        self.set_tickets_row(sector, '1')

                elif 'балк' in sector_name_l:
                    if 'серед' in sector_name_l:
                        f_sector_name = 'Балкон, середина'
                    elif 'лев' in sector_name_l:
                        f_sector_name = 'Балкон, левая сторона'
                    elif 'прав' in sector_name_l:
                        f_sector_name = 'Балкон, правая сторона'

                # Малая сцена (2)
                elif 'сектор' in sector_name_l:
                    f_sector_name = sector_name[:-1] + sector_name[-1].upper()

                elif 'стол' in sector_name_l:
                    # TODO обсудить
                    return False

                # Малая сцена (XXX)
                # TODO не все сектора проверены ввиду отсутствия билетов на сайте (Галерея)

                return f_sector_name

        elif 'мхат' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Основная сцена
                if 'бельэтаж середина' in sector_name_l:
                    f_sector_name = 'Бельэтаж'
                if 'vip' in str(sector.get('seats')).lower():
                    f_sector_name = 'VIP-партер'

                return f_sector_name

        elif 'малый' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                if 'основн' in self.scene.lower():
                    # Основная сцена
                    # TODO (Страфонтен; Ложи бельэтажа)
                    if 'балкон' in sector_name_l:
                        if '1' in sector_name_l:
                            f_sector_name = 'Балкон первого яруса'
                        elif '2' in sector_name_l:
                            f_sector_name = 'Балкон второго яруса'
                    elif 'ложа' in sector_name_l:
                        side = ''
                        if 'лс' in sector_name_l:
                            side = 'левая сторона'
                        elif 'пс' in sector_name_l:
                            side = 'правая сторона'

                        lozha_num = sector_name_l.split()[-1] if not side else sector_name_l.split()[-2]
                        if 'бельэтаж' in sector_name_l:
                            f_sector_name = f'Ложа бельэтажа №{lozha_num}, {side}'
                        elif 'бенуар' in sector_name_l:
                            f_sector_name = f'Ложа бенуара №{lozha_num}, {side}'
                        elif '1 яруса' in sector_name_l:
                            lozha_num = lozha_num.replace('№', '')
                            f_sector_name = f'Ложа первого яруса №{lozha_num}, {side}'

                    elif '1-й ярус' == sector_name_l:
                        f_sector_name = 'Балкон первого яруса' if 'основ' in scene.lower() else 'Балкон 1 яруса'
                    elif '2-й ярус' == sector_name_l:
                        f_sector_name = 'Балкон второго яруса'

                elif 'ордынк' in self.scene.lower():
                    # Сцена на ордынке
                    # TODO Ложи бельэтажа и 1 яруса
                    if 'ложа' in sector_name_l:
                        side = ''
                        if 'лс' in sector_name_l:
                            side = 'левая сторона'
                        elif 'пс' in sector_name_l:
                            side = 'правая сторона'

                        lozha_num = sector_name_l.split()[-1] if not side else sector_name_l.split()[-2]
                        lozha_num = lozha_num.replace(',', '')
                        if 'бенуар' in sector_name_l:
                            f_sector_name = f'Ложа бенуара {lozha_num} {side}'
                        elif 'бельэтаж' in sector_name_l:
                            f_sector_name = f'Ложа бельэтажа {lozha_num} {side}'
                        elif '1 ярус' in sector_name_l:
                            f_sector_name = f'Ложа балкона {lozha_num} {side}'

                return f_sector_name

        elif 'вахтангов' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Основная сцена
                if 'ложа' in sector_name_l:
                    side = 'левая сторона' if 'лев' in sector_name_l else 'правая сторона'
                    lozha_num = sector_name_l.split()[-1]
                    sec_name = sector_name_l.split()[-2]

                    f_sector_name = f'Ложа {sec_name} {lozha_num} {side}'

                return f_sector_name

        elif 'сатир' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Основная сцена
                if sector_name_l == 'правая ложа' or sector_name_l == 'левая ложа':
                    f_sector_name = 'Ложа'

                return f_sector_name

        elif 'цветном' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                if 'ложа' in sector_name_l:
                    if 'партер' in sector_name_l:
                        f_sector_name = 'Ложа партера'
                    elif 'амфитеатр' in sector_name_l:
                        f_sector_name = 'Ложа амфитеатра'

                else:
                    side = 'side_not_present'
                    if 'лев' in sector_name_l:
                        side = 'левая сторона'
                    elif 'прав' in sector_name_l:
                        side = 'правая сторона'

                    sec = 'sector_not_present'
                    if 'партер' in sector_name_l:
                        sec = 'Партер'
                    elif 'амфитеатр' in sector_name_l:
                        sec = 'Амфитеатр'

                    f_sector_name = f'{sec} {side}'

                return f_sector_name

        elif 'большой' in theatre:
            if 'новая' in self.scene.lower():
                def get_f_name(sectors, sector_name, sector_seats, scene):
                    f_sector_name = sector_name
                    sector_name_l = sector_name.lower()

                    to_append = []

                    if sector_name_l in ['партер', 'амфитеатр', 'бельэтаж', '1-й ярус']:
                        f_sector_name = False
                        sector_name = sector_name.replace('1-й ярус', 'Первый ярус')
                        to_append = self.divide_sector(sector_name, sector_seats, new_scene=True)

                    elif 'правая ложа бельэтажа' in sector_name_l:
                        f_sector_name = 'Бельэтаж, правая сторона Ложа 1'

                    elif 'ложа бенуара, пс' in sector_name_l:
                        f_sector_name = 'Бенуар, правая сторона Ложа 1'
                    elif 'ложа бенуара, лс' in sector_name_l:
                        f_sector_name = 'Бенуар,  левая сторона Ложа 1'
                    elif 'левая ложа 1-го яруса' in sector_name_l:
                        f_sector_name = 'Первый ярус, левая сторона Ложа 1'
                    elif 'правая ложа 1-го яруса' in sector_name_l:
                        f_sector_name = 'Первый ярус, правая сторона Ложа 1'

                    return f_sector_name, to_append

                add_sec = True
            else:
                def get_f_name(sectors, sector_name, sector_seats, scene):
                    f_sector_name = sector_name
                    sector_name_l = sector_name.lower()

                    to_append = []

                    if sector_name_l in ['партер', 'амфитеатр']:
                        f_sector_name = False
                        to_append = self.divide_sector(sector_name, sector_seats)

                    if 'ложа' in sector_name_l:
                        if 'ложа 12' not in sector_name_l:
                            f_sector_name = False

                            f_sec_name = 'unset'
                            if 'яруса' in sector_name_l:
                                yarus_num = sector_name_l.split()[1]
                                f_sec_name = f'{yarus_num} ярус'
                            elif 'бельэтаж' in sector_name_l:
                                f_sec_name = 'Бельэтаж'
                            elif 'бенуар' in sector_name_l:
                                f_sec_name = 'Бенуар'

                            to_append = self.divide_lozha(sector_name, f_sec_name, sector_seats)
                        else:
                            if 'лс' in sector_name_l:
                                f_sector_name = '1 ярус Левая сторона Ложа № 12'
                            else:
                                f_sector_name = '1 ярус Правая сторона Ложа № 12'

                    if 'балкон' in sector_name_l:
                        bal_num = double_split(sector_name_l, ' ', '-й')
                        side = ''

                        if 'лс' in sector_name_l:
                            side = ' Левая сторона'
                        elif 'пс' in sector_name_l:
                            side = ' Правая сторона'

                        f_sector_name = f'Балкон {bal_num} яруса{side}'

                        if f_sector_name == 'Балкон 4 яруса':  # TODO ИСПРАВИТЬ ПОФИКСИТЬ СНАЧАЛА СХЕМУ ПОТОМ ТУТ!!!
                            f_sector_name = False

                    return f_sector_name, to_append

                add_sec = True

        elif 'зарядье' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name.replace('-', '')
                sector_name_l = sector_name.lower()

                if 'бельэтаж левая сторона' in sector_name_l:
                    f_sector_name = 'Бельэтаж, левая сторона'
                elif 'бельэтаж правая сторона' in sector_name_l:
                    f_sector_name = 'Бельэтаж, правая сторона'
                elif 'бельэтаж сцена левая сторона' in sector_name_l:
                    f_sector_name = 'Бельэтаж сцена, левая сторона'
                elif 'бельэтаж сцена правая сторона' in sector_name_l:
                    f_sector_name = 'Бельэтаж сцена, правая сторона'
                elif 'балкон 1 ярус середина' in sector_name_l:
                    f_sector_name = 'Балкон 1-го яруса, середина'
                elif 'балкон 1 ярус левая сторона' in sector_name_l:
                    f_sector_name = 'Балкон 1-го яруса, левая сторона'
                elif 'балкон 1 ярус правая сторона' in sector_name_l:
                    f_sector_name = 'Балкон 1-го яруса, правая сторона'
                elif 'балкон 2 ярус правая сторона' in sector_name_l:
                    f_sector_name = 'Балкон 1-го яруса, правая сторона'
                elif 'балкон 2 ярус правая сторона' in sector_name_l:
                    f_sector_name = 'Балкон 1-го яруса, правая сторона'
                elif 'балкон 2 ярус правая сторона' in sector_name_l:
                    f_sector_name = 'Балкон 1-го яруса, правая сторона'

                return f_sector_name

        elif 'мегаспорт' in theatre:
            def get_f_name(sector, sector_name, sector_seats, scene):
                f_sector_name = sector_name.replace('-', '')
                sector_name_l = sector_name.lower()

                if 'трибуна' in sector_name_l:
                    f_sector_name = f_sector_name.replace('трибуна', 'Сектор').replace('Трибуна', 'Сектор')
                if 'фанзона' in sector_name_l:
                    f_sector_name = 'Фан-зона'
                if 'танцевальный партер' in sector_name_l:
                    f_sector_name = 'Танцпол'

                return f_sector_name

        elif 'цска арена' in theatre:
            # only capitalize needed
            pass

        elif 'крокус' in theatre:
            # only capitalize needed
            pass

        self.get_f_sectors(a_sectors, get_f_name, add_sec)

    def set_tickets_row(self, sector, new_row):
        to_del = []

        for row, seat in sector['seats']:
            to_del.append((row, seat))

        for row, seat in to_del:
            sector['seats'][new_row, seat] = sector['seats'][row, seat]
            del sector['seats'][row, seat]

    def divide_lozha(self, sector_name, f_sec_name, sector_seats):
        new_secs = {}

        side = 'Левая сторона' if 'лс' in sector_name else 'Правая сторона'
        for row, seat in sector_seats:
            lozha_num = row.split()[-1]
            lozha_name = f'{f_sec_name} {side} Ложа № {lozha_num}'

            if lozha_name not in new_secs:
                new_secs[lozha_name] = {
                    'name': lozha_name,
                    'seats': {}
                }

            loz_row = self.reformat_row('', seat, lozha_name)
            new_secs[lozha_name]['seats'][loz_row, seat] = sector_seats[row, seat]

        new_secs = [sec for sec in new_secs.values()]

        return new_secs

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

    def divide_sector(self, sector_name, sector_seats, new_scene=False):
        left_side = {
            'name': f'{sector_name} Левая сторона',
            'seats': {}
        }
        right_side = {
            'name': f'{sector_name} Правая сторона',
            'seats': {}
        }

        for row, seat in sector_seats:
            if 'Левая' in self.bt_get_ticket_side(sector_name, row, seat, new_scene=new_scene):
                left_side['seats'][row, seat] = sector_seats[row, seat]
            else:
                right_side['seats'][row, seat] = sector_seats[row, seat]

        if new_scene:
            left_side['name'] = left_side['name'].replace(' Лев', ', лев')
            right_side['name'] = right_side['name'].replace(' Прав', ', прав')

        return [left_side, right_side]

    def bt_get_ticket_side(self, sector_name, row, seat, new_scene=False):
        sector_sides = {
            'Партер': {
                '1': 16,
                '2': 16,
                '3': 16,
                '4': 16,
                '5': 16,
                '6': 16,
                '7': 16,
                '8': 16,
                '9': 16,
                '10': 16,
                '11': 16,
                '12': 14,
                '13': 14,
                '14': 13,
                '15': 11,
                '16': 8,
                '17': 4
            },

            'Амфитеатр': {
                '1': 13,
                '2': 14,
                '3': 18
            }
        }

        if new_scene:
            sector_sides = {
                'Партер': {
                    '1': 14,
                    '2': 14,
                    '3': 14,
                    '4': 14,
                    '5': 14,
                    '6': 14,
                    '7': 14,
                    '8': 14,
                    '9': 14,
                    '10': 13,
                    '11': 12,
                    '12': 11,
                    '13': 9,
                    '14': 5
                },

                'Амфитеатр': {
                    '1': 25,
                    '2': 21,
                    '3': 23
                },

                'Бельэтаж': {
                    '1': 24,
                    '2': 24,
                    '3': 26
                },

                'Первый ярус': {
                    '1': 27,
                    '2': 28,
                    '3': 22,
                    '4': 16,
                    '5': 18
                }
            }

        side = 'Левая сторона' if int(seat) >= sector_sides[sector_name][row] else 'Правая сторона'

        return side

    def get_range(self, diaposon):
        if '-' not in diaposon or '+' in diaposon:
            return [diaposon]

        split_ = [int(seat_id) for seat_id in diaposon.split('-')]
        range_ = range(split_[0], split_[1] + 1)

        return range_

    def reformat_table_in_crocus_hall(self, sector, row):
        new_row = sector.split()[-1]
        sector = f'Grand партер (ряд {row})'
        return sector, new_row

    def place_map(self, soup):
        s = []
        place1 = soup.find_all('div', class_='place1')
        for place in place1:
            t = place.get('title').translate({ord(i): None for i in '<strong><br/>'})
            # print(t)
            sector = t.split('ряд')[0].strip()
            row = (' '.join(re.findall(r'ряд([^<>]+),', t))).strip()

            if 'ряд' not in t:
                sector = double_split(place.get("title"), "<strong>", "</strong>").strip()
                row = double_split(place.get("title"), "<br />", ",").strip()

            seat = (' '.join(re.findall(r'место([^<>]+) Стоимость', t))).strip()
            price = (' '.join(re.findall(r'Стоимость:([^<>]+) руб.', t))).strip()

            if 'танцпол' in sector or 'фан-зона' in sector:
                continue
                self.register_dancefloor(sector, price)
            else:
                if 'Крокус Сити Холл' in self.venue:
                    if 'Стол' in sector:
                        sector, row = self.reformat_table_in_crocus_hall(sector, row)
                s.append([sector, row, seat, price])
        return s

    def place_btn(self, soup):
        seats = []
        btns = soup.find_all('a', class_='btn')
        btns = [btn for btn in btns if btn.text == 'выбрать билеты']

        for btn in btns:
            table_row = btn.parent.parent
            seats_info = [cell.text.strip() for cell in table_row.find_all('td', class_='table_border')]
            sector, row, places, price, btn_text = seats_info
            price = price.replace(' ', '')

            for diaposon in places.split(', '):
                for seat in self.get_range(diaposon):
                    seat = str(seat)
                    if 'танцпол' in sector or 'фан-зона' in sector:
                        continue
                        self.register_dancefloor(sector, price)
                    if 'Крокус Сити Холл' == self.venue:
                        sector, row = self.reformat_sectors_crocus(row, seat, sector)
                        if 'Стол' in sector:
                            sector, row = self.reformat_table_in_crocus_hall(sector, row)
                    seats.append([sector, row, seat, price])

        return seats

    def reformat_sectors_crocus(self, row, seat, r_sector_name):
        r_sector_name = r_sector_name.title()
        if 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name:
            if 'Vip-партер' == r_sector_name:
                if row == '12':
                    if int(seat) <= 17:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 53:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                if row == '11':
                    if int(seat) <= 17:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 53:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '10':
                    if int(seat) <= 16:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 58:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '9':
                    if int(seat) <= 15:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 57:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                if row == '8':
                    if int(seat) <= 15:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 57:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '7':
                    if int(seat) <= 13:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 41:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '6':
                    if int(seat) <= 13:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 41:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '5':
                    if int(seat) <= 11:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 35:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '4':
                    if int(seat) <= 11:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 35:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '3':
                    if int(seat) <= 11:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 35:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '2':
                    if int(seat) <= 9:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 29:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '1':
                    if int(seat) <= 8:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 26:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
        if ('Крокус Сити Холл-Столы' in self.scheme.name and 'в 4 ряда' not in self.scheme.name)\
                or 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name:
            if 'Партер' == r_sector_name:
                if row == '8':
                    if int(seat) <= 25:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 61:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '7':
                    if int(seat) <= 23:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 60:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '6':
                    if int(seat) <= 23:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 57:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '5':
                    if int(seat) <= 22:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 56:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '4':
                    if int(seat) <= 22:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 66:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '3':
                    if int(seat) <= 21:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 65:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '2':
                    if int(seat) <= 19:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 63:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '1':
                    if int(seat) <= 18:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 60:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
            if 'Амфитеатр' == r_sector_name or 'Партер' == r_sector_name:
                if (row == '6' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '14':
                    if row == '6':
                        row = '14'
                    if int(seat) <= 17:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 33:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 50:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '5' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '13':
                    if row == '5':
                        row = '13'
                    if int(seat) <= 17:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 33:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 65:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 81:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '4' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '12':
                    if row == '4':
                        row = '12'
                    if int(seat) <= 16:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 32:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 64:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 80:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '3' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '11':
                    if row == '3':
                        row = '11'
                    if int(seat) <= 16:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 31:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 62:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 77:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '2' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '10':
                    if row == '2':
                        row = '10'
                    if int(seat) <= 15:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 30:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 60:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 75:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '1' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '9':
                    if row == '1':
                        row = '9'
                    if int(seat) <= 10:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 24:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 44:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 58:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
        if 'Бельэтаж' == r_sector_name:
            if row == '8':
                if int(seat) <= 27:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 50:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 93:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 117:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '7':
                if int(seat) <= 27:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 49:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 90:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 113:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '6':
                if int(seat) <= 27:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 48:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 89:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 112:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '5':
                if int(seat) <= 25:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 48:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 86:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 108:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '4':
                if int(seat) <= 25:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 46:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 85:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 107:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '3':
                if int(seat) <= 24:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 44:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 83:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 104:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '2':
                if int(seat) <= 24:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 44:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 81:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 102:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '1':
                if int(seat) <= 23:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 42:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 70:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 98:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
        elif 'Балкон' == r_sector_name:
            if row == '17':
                if int(seat) <= 38:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 69:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 129:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 162:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '16':
                if int(seat) <= 38:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 71:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 130:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 164:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '15':
                if int(seat) <= 3:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 70:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 129:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 163:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '14':
                if int(seat) <= 37:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 69:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 127:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 161:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '13':
                if int(seat) <= 37:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 69:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 126:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 159:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '12':
                if int(seat) <= 36:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 68:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 122:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 154:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '11':
                if int(seat) <= 36:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 67:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 122:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 154:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '10':
                if int(seat) <= 35:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 65:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 120:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 151:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '9':
                if int(seat) <= 34:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 63:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 147:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            if row == '8':
                if int(seat) <= 34:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 63:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 147:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '7':
                if int(seat) <= 33:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 61:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 112:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 141:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '6':
                if int(seat) <= 29:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 54:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 97:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 123:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '5':
                if int(seat) <= 29:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 53:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 96:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 121:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '4':
                if int(seat) <= 25:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 51:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 92:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '3':
                if int(seat) <= 28:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 51:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 92:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '2':
                if int(seat) <= 28:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 49:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 88:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 111:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '1':
                if int(seat) <= 24:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 43:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 76:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 97:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
        if 'vip партер' == r_sector_name.lower() or 'vip-партер' == r_sector_name.lower():
            r_sector_name = 'VIP партер'
        return r_sector_name, row

    def reformat_row_MXAT(self, all_sector):
        total_sector = []
        sector_parter = {'name': 'Партер', 'seats': {}}
        for sector in all_sector:
            sector_name = sector.get('name')
            if sector_name == 'VIP-партер':
                sector_seats = sector.get('seats')
                sector = {'name': sector_name, 'seats': {}}
                for row_and_seat, price in sector_seats.items():
                    row, seat = row_and_seat
                    if 'vip' not in row.lower():
                        sector_parter['seats'][(row, seat)] = price
                        continue
                    row = row.lower().split('v')[0]
                    sector['seats'][(row, seat)] = price
            total_sector.append(sector)
        if sector_parter.get('seats'):
            total_sector.append(sector_parter)
        return total_sector

    def get_places(self):
        resp = self.session.get(self.url, headers={'user-agent': 'Custom'})
        soup = BeautifulSoup(resp.text, 'lxml')
        map_s = soup.find_all('div', class_='Map')
        if map_s:
            s = self.place_map(soup)
        else:
            s = self.place_btn(soup)

        theatre = soup.find('div', class_='d_link').find('a').getText().strip().lower()

        return s, theatre

    def body(self):
        skip_events = [
            'https://www.tickets-star.com/cat/245/EventId/249417912/',  # Акварель 11.03 14:30
            'https://www.tickets-star.com/cat/245/EventId/249417909/',  # Акварель 11.03 18:00
            'https://www.tickets-star.com/cat/245/EventId/249417911/',  # Акварель 12.03 14:30
            'https://www.tickets-star.com/cat/245/EventId/249417910/',  # Акварель 12.03 18:00
            'https://www.tickets-star.com/cat/245/EventId/250021315/',  # Акварель 19.03 14:30
            'https://www.tickets-star.com/cat/245/EventId/252042851/',  # Акварель 19.03 18:00
            'https://www.tickets-star.com/cat/245/EventId/250541551/',  # Акварель 25.03 14:30
            'https://www.tickets-star.com/cat/245/EventId/250541552/',  # Акварель 25.03 18:00
            'https://www.tickets-star.com/cat/245/EventId/250541550/',  # Акварель 26.03 14:30
            'https://www.tickets-star.com/cat/245/EventId/250541553/',  # Акварель 26.03 18:00
            'https://www.tickets-star.com/cat/245/EventId/260783064/',  # Хоккей. ЦСКА (Москва) - Ак Барс (Казань) 27.04
        ]

        if self.url in skip_events:
            return None

        sector = []
        places, theatre = self.get_places()

        if 'вернадского' in theatre:
            return None

        for place in places:
            if place[0] not in sector:
                sector.append(place[0])

        a_sectors = []
        for each_sector in sector:
            seats = {}
            for place in places:
                section, row, seat, price = place
                if '+' in seat:
                    if 'ленком' in theatre:
                        place[2] = seat
                    else:
                        place[2] = seat.replace('+', '')

                try:
                    row = str(row)
                except ValueError:
                    print(f'row-->{row}<--')
                    pass

                try:
                    seat = str(seat)
                except ValueError:
                    print(f'seat-->{seat}<--')
                    pass

                try:
                    price = int(price)
                except ValueError:
                    print(f'price-->{price}<--')
                    pass

                if each_sector == section:
                    seats[row, seat] = price

            a_sectors.append({'name': each_sector, 'seats': seats})

        if 'Крокус Сити Холл' != self.venue:
            self.reformat(a_sectors, theatre)

        if 'мхат' in theatre:
            a_sectors = self.reformat_row_MXAT(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['seats'])