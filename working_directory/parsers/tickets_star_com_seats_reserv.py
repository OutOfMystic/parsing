from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from bs4 import BeautifulSoup
import re


class Parser(SeatsParser):
    event = 'tickets-star.com'
    url_filter = lambda event: 'tickets-star.com' in event

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 60
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def get_f_sectors(self, sectors, get_f_name=None):
        to_del = []

        for i, sector in enumerate(sectors):
            sector['name'] = sector['name'].replace('  ', ' ')
            sector['name'] = sector['name'].capitalize()

            if get_f_name:
                f_name = get_f_name(sector['name'], sector['seats'])

                if f_name is False:
                    to_del.append(i)
                    continue
                else:
                    sector['name'] = f_name

        for i in to_del[::-1]:
            del sectors[i]

    def reformat(self, a_sectors, theatre):
        if 'ленком' in theatre:
            missing_sectors = []

            for sector in a_sectors:
                sector['name'] = sector['name'].capitalize()

                if sector['name'] == 'Бельэтаж':
                    missing_uncomfy_seats = {}
                    for row, seat in sector['seats'].keys():
                        if row in [1, 2] and seat in [1, 2, 17, 18]:
                            missing_uncomfy_seats[row, seat] = sector['seats'][row, seat]

                    for row_seat in missing_uncomfy_seats.keys():
                        del sector['seats'][row_seat]

                    missing_sectors.append({
                        'name': 'Бельэтаж (неудобное) 2',
                        'seats': missing_uncomfy_seats
                    })

            for missing_sector in missing_sectors:
                a_sectors.append(missing_sector)

        elif 'мхт' in theatre:
            def get_f_name(sector_name, sector_seats):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Основная сцена
                # TODO не все сектора проверены ввиду отсутствия билетов на сайте
                # TODO (все откидные; Бельэтаж кроме лож, весь Балкон)
                if 'бенуар' in sector_name_l:
                    if 'ложа' in sector_name_l:
                        if 'прав' in sector_name:
                            f_sector_name = 'Бенуар, ложа правая'
                        elif 'лев' in sector_name:
                            f_sector_name = 'Бенуар, ложа левая'

                # Малая сцена (2)
                elif 'сектор' in sector_name_l:
                    f_sector_name = sector_name[:-1] + sector_name[-1].upper()

                elif 'стол' in sector_name_l:
                    # TODO обсудить
                    return False

                # Малая сцена (XXX)
                # TODO не все сектора проверены ввиду отсутствия билетов на сайте (Галерея)

                return f_sector_name

            self.get_f_sectors(a_sectors, get_f_name)

        elif 'малый' in theatre:
            def get_f_name(sector_name, sector_seats):
                f_sector_name = sector_name
                sector_name_l = sector_name.lower()

                # Основная сцена
                # TODO не все сектора проверены ввиду отсутствия билетов на сайте
                # TODO (Страфонтен; Ложи бенуара/бельэтажа/первого яруса номерные;)
                # TODO Разобраться че за сектор '2-й ярус'
                if 'балкон' in sector_name_l:
                    if '1' in sector_name_l:
                        f_sector_name = 'Балкон первого яруса'
                    elif '2' in sector_name_l:
                        f_sector_name = 'Балкон второго яруса'

                # Сцена на ордынке
                # TODO На этой сцене сектор называется "Балкон 1 яруса" а на основной "Балкон первого яруса"
                # TODO Придумать как избежать конфликта (переименовать просто?)

                # TODO не все сектора проверены ввиду отсутствия билетов на сайте
                # TODO (Все кроме партера)

                return f_sector_name

            self.get_f_sectors(a_sectors)

        elif 'наций' in theatre:
            self.get_f_sectors(a_sectors)

        elif 'оперетт' in theatre:
            self.get_f_sectors(a_sectors)

        elif 'вахтангов' in theatre:
            self.get_f_sectors(a_sectors)

    def place_map(self, soup):
        s = []
        place1 = soup.find_all('div', class_='place1')
        for place in place1:
            t = place.get('title').translate({ord(i): None for i in '<strong><br/>'})
            # print(t)
            sector = t.split('ряд')[0].strip()
            row = (' '.join(re.findall(r'ряд([^<>]+),', t))).strip()
            seat = (' '.join(re.findall(r'место([^<>]+) Стоимость', t))).strip()
            price = (' '.join(re.findall(r'Стоимость:([^<>]+) руб.', t))).strip()

            s.append([sector, row, seat, price])
        return s

    def place_btn(self,soup):
        s = []
        btns = soup.find_all('a', class_='btn')
        for btn in btns:
            if btn.text == 'выбрать билеты':
                resp_btn = self.session.get('https://www.tickets-star.com' + btn.get('href'))
                soup_btn = BeautifulSoup(resp_btn.text, 'lxml')
                borders = soup_btn.find_all('td', class_='table_border')
                for border in borders:
                    s.append(border.text.strip())
        s = list(filter(lambda x: x != 'положить в корзину', s))
        s = [s[x:4 + x] for x in range(0, len(s), 4)]

        return s

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
        sector = []
        places, theatre = self.get_places()

        if 'мхт' not in theatre:
            return False

        for place in places:
            if place[0] not in sector:
                sector.append(place[0])

        a_sectors = []
        for each_sector in sector:
            seats = {}
            for section, row, seat, price in places:
                if '+' in seat:
                    # TODO сделать что-то с этим?
                    continue

                try:
                    row = int(row)
                except ValueError:
                    print(f'row-->{row}<--')
                    pass

                try:
                    seat = int(seat)
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

        self.reformat(a_sectors, theatre)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['seats'])


class MkhtParser(Parser):
    url_filter = lambda url: 'tickets-star.com' in url and 'mkht' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        to_del = []

        for i, sector in enumerate(sectors):
            if 'покой' in sector['name'].lower():
                to_del.append(i)
                continue
            elif 'бенуар правая сторона' in sector['name'].lower():
                to_del.append(i)
                continue

            sector['name'] = sector['name'].replace('  ', ' ')

            # Основная сцена

            if 'неудоб' in sector['name'].lower():
                sec_name, sec_side = sector['name'].split()[:-1]

                if 'лев' in sec_side.lower():
                    side = 'левая'
                elif 'прав' in sec_side.lower():
                    side = 'правая'
                else:
                    side = '-'

                sector['name'] = f'{sec_name.capitalize()} {side} сторона'

            # Новая сцена

        for i in to_del[::-1]:
            del sectors[i]

    def body(self):
        super().body()

