import time

from requests.exceptions import JSONDecodeError

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.utils import utils, provision


class LenkomParser(SeatsParser):
    event = 'ticketland.ru'
    proxy_check_url = 'https://www.ticketland.ru/'
    url_filter = lambda url: 'ticketland.ru' in url and 'lenkom' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.venue = 'Ленком'

    def get_tl_csrf_and_data(self):
        result = provision.multi_try(self._get_tl_csrf_and_data,
                                     name='CSRF', tries=5, raise_exc=False)
        if result == provision.TryError:
            result = None
        return result

    def _get_tl_csrf_and_data(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp'
                      ',image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        # r = self.session.get(self.url, headers=headers)
        r_text, _ = provision.multi_try(self.request_to_ticketland,
                                 name='request_to_ticketland_parser_seats', tries=5, args=[self.url, headers])

        tl_csrf = double_split(r_text, '<meta name="csrf-token" content="', '"')
        if 'performanceId:' not in r_text:
            return None
        performance_id = double_split(r_text, 'performanceId: ', ',')
        if 'maxTicketCount' not in r_text:
            return None

        limit = double_split(r_text, 'maxTicketCount: ', ',')
        is_special_sale = double_split(r_text, "isSpecialSale: '", "'")

        return tl_csrf, performance_id, limit, is_special_sale

    def before_body(self):
        self.session = ProxySession(self)
        event_vars = self.get_tl_csrf_and_data()
        while not event_vars:
            self.bprint('Waiting event vars')
            time.sleep(self.delay)
            self.last_time_body = time.time()
            event_vars = self.get_tl_csrf_and_data()
        else:
            tl_csrf, self.performance_id, self.limit, self.is_special_sale = event_vars
        self.tl_csrf_no_f = tl_csrf.replace('=', '%3D')

    def request_to_ticketland(self, url, headers=None):
        r = self.session.get(url, headers=headers)
        r_text = r.text
        if '<div id="id_spinner" class="container"><div class="load">Loading...</div>' in r_text:
            raise Exception('Запрос с загрузкой')
        try:
            return r_text, r.json()
        except JSONDecodeError:
            return r_text, None

    def get_scene(self):
        pass

    def reformat(self, sectors, scene):
        for sector in sectors:
            if 'неудоб' in sector['name'].lower():
                sector['name'] = sector['name'].replace(' (неудобное)', '')

    def reformat_seat(self, sector_name, row, seat, price, ticket):
        return sector_name, row, seat, price

    def body(self):
        json, all_ = 1, 1

        url = (f'https://{self.domain}/hallview/map/'
               f'{self.performance_id}/?json='
               f'{json}&all={all_}&isSpecialSale={self.is_special_sale}&tl-csrf='
               f'{self.tl_csrf_no_f}')

        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        # r = self.session.get(url, headers=headers)
        r_text, r_json = provision.multi_try(self.request_to_ticketland,
                                 name='request_to_ticketland_parser_seats', tries=5, args=[url, headers])
        if '"Unable to verify your data submission."' in r_text:
            self.proxy = self.controller.proxy_hub.get()
            self.before_body()
        if '""' in r_text:
            self.proxy = self.controller.proxy_hub.get()
            self.before_body()
        if isinstance(r_json, str):
            self.bprint(utils.yellow(r_text))
            return
        all_tickets = r_json.get('places')

        a_sectors = []
        for ticket in all_tickets:
            row = ticket['row']
            seat = ticket['place']
            cost = int(ticket['price'])
            sector_name = ticket['section']['name']
            sector_name, row, seat, cost = self.reformat_seat(sector_name, row, seat, cost, ticket)

            for sector in a_sectors:
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = cost
                    break
            else:
                a_sectors.append({
                    'name': sector_name,
                    'tickets': {(row, seat): cost}
                })

        self.reformat(a_sectors, self.get_scene())
        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])


class MkhtParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'mkht' in url

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

            # Новая сцена

            if 'галерея' == sector['name'].lower():
                sector['name'] = sector['name'].capitalize()
            elif 'Партер неудобное' == sector['name']:
                sector['name'] = 'Партер'

            # Основная сцена

            if 'неудоб' in sector['name'].lower():
                try:
                    sec_name, sec_side = sector['name'].split()[:-1]
                except:
                    self.lprint(sector['name'].split()[:-1])
                    return

                if 'лев' in sec_side.lower():
                    side = 'левая'
                elif 'прав' in sec_side.lower():
                    side = 'правая'
                else:
                    side = '-'

                sector['name'] = f'{sec_name.capitalize()} {side} сторона'

            if 'откид' in sector['name']:
                if 'Бельэтаж' in sector['name']:
                    if 'откидное А' in sector['name']:
                        sector['name'] = sector['name'].replace('откидное А', 'правая сторона (откидное А)')
                    elif 'откидное Б':
                        sector['name'] = sector['name'].replace('откидное Б', 'левая сторона (откидное Б)')
                elif 'Партер' in sector['name']:
                    sector['name'] = sector['name'].replace('откидное', 'откидные')

            if 'бенуар' in sector['name'].lower():
                if 'ложа' in sector['name'].lower():
                    if 'прав' in sector['name']:
                        sector['name'] = 'Бенуар ложа правая'
                    elif 'лев' in sector['name']:
                        sector['name'] = 'Бенуар ложа левая'
                else:
                    pass
                    # Бенуар правая сторона.

            if 'огран' in sector['name'] and ('Балкон' in sector['name'] or 'Бельэтаж' in sector['name']):
                if 'середина' in sector['name']:
                    sector['name'] = ' '.join(sector['name'].split()[:2])
                else:
                    sector['name'] = ' '.join(sector['name'].split()[:2]) + ' ' + 'сторона'

            if 'сектор' not in sector['name'].lower():
                sector['name'] = sector['name'].replace(' ', ', ', 1)

            if 'Партер, частично ограниченный просмот' in sector['name']:
                sector['name'] = 'Партер'

        for i in to_del[::-1]:
            del sectors[i]

    def body(self):
        super().body()


class MalyyParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'malyy' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ')

            if sector['name'] == 'Балкон 2 ярус':
                sector['name'] = "Балкон второго яруса"
            elif sector['name'] == 'Балкон 1 ярус':
                sector['name'] = "Балкон первого яруса"
            elif '№' in sector['name']:
                sector['name'] = sector['name'].replace('№ ', '№')
                sector['name'] = sector['name'].replace(' правая сторона', ', правая сторона')
                sector['name'] = sector['name'].replace(' левая сторона', ', левая сторона')

                if 'Ложа 1 яруса' in sector['name']:
                    sector['name'] = sector['name'].replace('Ложа 1 яруса', 'Ложа первого яруса')

            if ' левая №' in sector['name']:
                sec_name, sec_num = sector['name'].split(' левая №')
                if sec_name == 'Ложа 1-го яруса':
                    sec_name = 'Ложа балкона'

                sector['name'] = f'{sec_name} {sec_num} левая сторона'
            elif ' правая №' in sector['name']:
                sec_name, sec_num = sector['name'].split(' правая №')
                if sec_name == 'Ложа 1-го яруса':
                    sec_name = 'Ложа балкона'

                sector['name'] = f'{sec_name} {sec_num} правая сторона'
            elif '1-го' in sector['name']:
                sector['name'] = sector['name'].replace('1-го', '1')

    def body(self):
        super().body()


class NaciyParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketlanzd.ru' in url and 'naciy' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ')

            if 'ложи' in sector['name'].lower():
                sector['name'] = sector['name'].capitalize()

    def body(self):
        super().body()


class OperettyParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketlanzd.ru' in url and 'operetty' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ')

    def body(self):
        super().body()


class VakhtangovaParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'vakhtangova' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ')

            # Основная сцена

            sector['name'] = sector['name'].replace('N', '№')

            if ' Ложа №' in sector['name']:
                sec_name_side, sec_num = sector['name'].split(' Ложа №')
                sec_name = sec_name_side.split()[0]
                sec_name_format = sec_name.lower() + 'а'
                if 'прав' in sec_name_side:
                    side = 'правая'
                elif 'лев' in sec_name_side:
                    side = 'левая'
                else:
                    side = '-'

                row_number = '1'
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price

                sector['name'] = f'Ложа {sec_name_format} {sec_num} {side} сторона'

            if 'откид' in sector['name']:
                if 'Партер' in sector['name']:
                    sector['name'] = sector['name'].replace('откидное', 'откидные')

            # Арт-кафе

            if sector['name'].lower() == 'арт-кафе':
                sector['name'] = sector['name'].replace('-', ' ').capitalize()

    def reformat_seat(self, sector_name, row, seat, price, ticket):
        if 'основная' in self.scheme.name:
            if 'Ложа' in sector_name and 'ст.' not in sector_name:
                x_coordinate = ticket['x']
                if x_coordinate < 500:
                    side = 'правая сторона'
                else:
                    side = 'левая сторона'
                sector_name = sector_name + f' {row} {side}'
                row = '1'
        return sector_name, row, seat, price

    def body(self):
        super().body()


class SatireParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'teatr-satiry' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            seats_change_row = {}
            sector['name'] = sector['name'].replace('  ', ' ')
            sector_name_low = sector['name'].lower()

            # Основная сцена
            if 'партер' in sector_name_low or 'амфитеатр' in sector_name_low:
                sector['name'] = sector['name'].replace(' правая сторона', '').replace(' левая сторона', '')

            elif 'ложа правая' == sector_name_low or 'правая ложа' == sector_name_low\
                    or 'правая Ложа' in sector_name_low or 'левая ложа' in sector_name_low:
                sector['name'] = 'Ложа'

                for row, seat in sector['tickets']:
                    seats_change_row[row, seat] = sector['tickets'][row, seat]

            for row, seat in seats_change_row:
                del sector['tickets'][row, seat]

                true_row = {
                    '1 2 3 4 5 ': '1',
                    '6 6отк. 7 8 ': '2',
                    '9 9отк. 10 ': '3',
                    '11 12': '4',
                    '13': '5',
                }

                row_ = ''
                for seats in true_row:
                    if seat in seats:
                        row_ = true_row[seats]
                        break

                sector['tickets'][row_, seat] = seats_change_row[row, seat]

    def body(self):
        super().body()


class OperettaParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'teatr-operetty' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ')

    def body(self):
        super().body()


class FomenkoParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'fomenko' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ').capitalize()
            sec_name_low = sector['name'].lower()

            # Большой зал
            # TODO на нашей схеме на Ложе А и Ложе Б по одному месту только почему то
            # TODO Ложе А и Ложе Б ряд - null, место - Б13, (А13 на Ложе А)

            if 'лож' in sec_name_low and 'бельэтаж' in sec_name_low:
                if 'лев' in sec_name_low:
                    sector['name'] = 'Ложа бельэтажа левая'
                elif 'прав' in sec_name_low:
                    sector['name'] = 'Ложа бельэтажа правая'
                elif 'середин' in sec_name_low:
                    sector['name'] = 'Ложа бельэтажа середина'

            if 'лож' in sec_name_low and 'балк' in sec_name_low:
                if 'лев' in sec_name_low:
                    sector['name'] = 'Левая ложа балкона'
                elif 'прав' in sec_name_low:
                    sector['name'] = 'Правая ложа балкона'

            if sec_name_low in ['ложа а', 'ложа б']:
                if 'ложа а' == sec_name_low:
                    sector['name'] = sector['name'].replace(' а', ' А')
                if 'ложа б' == sec_name_low:
                    sector['name'] = sector['name'].replace(' б', ' Б')

                to_change_tickets = {}
                for row, seat in sector['tickets']:
                    to_change_tickets[row, seat] = sector['tickets'][row, seat]

                for row, seat in to_change_tickets:
                    seat_f = seat.replace('A', 'А')  # Английскую А заменяю на русскую...
                    sector['tickets']['1', seat_f] = to_change_tickets[row, seat]
                    del sector['tickets'][row, seat]

            # Новая сцена, малый зал
            if ' партер' == sec_name_low:
                sector['name'] = sector['name'].replace(' партер', 'Партер')

            # Новая сцена (партер и галерея)
            if 'партер неудобное' in sec_name_low:
                sector['name'].replace('Партер неудобное', 'Партер')
            if 'Партер рекомендовано детям от 10 лет' == sector['name']:
                sector['name'] = 'Партер'

    def body(self):
        super().body()


class MkhatParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'mkhat-im-m-gorkogo' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ').capitalize()
            sec_name_low = sector['name'].lower()

            # TODO С сайта приходят данные о местах в этом секторе, при это на самом сайте их выбрать нельзя
            # TODO сектор отрезан на схеме как бы
            sector['name'] = sector['name'].replace('1-й', 'Первый')

            # TODO Ложа А и Д не настроены
            if 'vip партер' in sec_name_low:
                sector['name'] = 'VIP-партер'
            elif ' ложа' in sec_name_low:
                sector['name'] = sector['name'].replace(' ложа', ', ложа')

    def body(self):
        super().body()


class VernadskogoCirk(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'bolshoy-moskovskiy-cirk' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector['name'] = sector['name'].title()

    def body(self):
        super().body()


class MtsLiveKhollMoskva(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'mts-live-kholl-moskva' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            sector_name = sector['name'].split()
            if 'танцевальный партер' in sector['name'].lower():
                sector['name'] = 'Танцпол'
            elif 'meet&greet' == sector['name'].lower():
                sector['name'] = ' Meet & Greet'
            elif 'vip dance' == sector['name'].lower():
                sector['name'] = 'VIP Dance'
            elif 'vip lounge' == sector['name'].lower():
                sector['name'] = 'VIP Lounge'
            elif 'vip' in sector['name'].lower():
                if 'vip' in sector_name[0].lower():
                    sector_name[0] = sector_name[0].upper()
                    sector['name'] = ' '.join(sector_name)
                elif 'vip' in sector_name[1].lower():
                    sector_name[0] = sector_name[0].title()
                    sector_name[1] = sector_name[1].upper()
                    if len(sector_name) == 2:
                        sector['name'] = ' '.join(sector_name[:2]) + ', центр'
                    else:
                        sector_name[2] = sector_name[2].lower()
                        sector_name[3] = sector_name[3].lower()
                        sector['name'] = ' '.join(sector_name[:2]) + ', ' + ' '.join(sector_name[2:])

    def body(self):
        super().body()


class AleksandrinskiyTeatr(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'spb.ticketland.ru' in url and 'aleksandrinskiy-teatr' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            if 'Ложа бельэтажа' in sector['name']:
                row_number = 'Ложа ' + sector['name'].split()[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = 'Бельэтаж'
            elif '1 ярус' in sector['name']:
                row_number = 'Ложа ' + sector['name'].split()[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = '1 ярус'
            elif '2 ярус' in sector['name']:
                row_number = 'Ложа ' + sector['name'].split()[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = '2 ярус'
            elif '3 ярус' in sector['name']:
                row_number = 'Ложа ' + sector['name'].split()[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = '3 ярус'
            elif '4 ярус' in sector['name']:
                row_number = 'Ложа ' + sector['name'].split()[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = '4 ярус'
            elif 'Балкон 3-го яруса' in sector['name']:
                row_number = 'Ложа ' + sector['name'].split()[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = 'Балкон 3го яруса'

    def body(self):
        super().body()


class ZimniyTeatrSochi(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'sochi.ticketland.ru' in url and 'zimniy-teatr-sochi' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            if 'Ложа Бельэтажа' in sector['name']:
                row_number = sector['name'].split('N')[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = 'Бельэтаж'
            elif 'Ложа Бенуар' in sector['name']:
                row_number = sector['name'].split('N')[-1]
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = 'Бенуар'

    def body(self):
        super().body()


class UgolokDedushkiDurova(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'www.ticketland.ru' in url and 'teatr-ugolok-dedushki-durova' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        ...

    def body(self):
        super().body()


class SovremennikTeatr(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'www.ticketland.ru' in url and 'moskovskiy-teatr-sovremennik' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            if 'Ложа бельэтажа' in sector['name']:
                sector['name'] = f'{sector["name"].split()[-1].title()} ложа бельэтажа'

    def body(self):
        super().body()


class BdtTeatr(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'bdt-imtovstonogova' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        ...

    def reformat_seat(self, sector_name, row, seat, price, ticket):
        if_seat_in_parter = [
            39, 40, 61, 62, 63, 64, 85, 86, 87, 88, 109, 110, 111, 112, 133, 134, 135, 136, 157, 158, 159, 160,
            181, 182, 183, 184, 205, 206, 207, 208, 229, 230, 231, 232, 253, 254, 255, 256, 277, 278, 279, 280,
            301, 302, 323
        ]
        if 'Партер' in sector_name and int(seat) in if_seat_in_parter:
            sector_name: str = 'Партер'
            # sector_name: str = 'Партер (неудобные места)'
        elif 'Партер' in sector_name and 'Гардероб' in sector_name:
            sector_name: str = 'Партер'
        elif 'Балкон' in sector_name:
            if '3го яруса' in sector_name or '3-го яруса' in sector_name:
                sector_name: str = 'Балкон третьего яруса'
        elif 'Партер-трибуна' in sector_name:
            sector_name: str = 'Кресла партера'
        elif 'Галерея 3го яр.' in sector_name or 'Галерея 3-го яруса' in sector_name:
            row: str = ''
            if 'правая' in sector_name or 'пр. ст.' in sector_name:
                sector_name: str = 'Галерея третьего яруса. Правая сторона'
            else:
                sector_name: str = 'Галерея третьего яруса. Левая сторона'
        elif 'Места за креслами' in sector_name:
            sector_name: str = 'Места за креслами'
        elif 'Партер' in sector_name:
            sector_name: str = 'Кресла партера'
        elif 'Ложа' in sector_name:
            number_lozha: str = sector_name.split()[1].replace('№', '')
            if 'бельэтажа' in sector_name:
                new_sector_name: str = 'Бельэтаж'
            elif 'бенуар' in sector_name:
                new_sector_name: str = 'Бенуар'
            elif '2-го яруса' in sector_name:
                new_sector_name: str = 'Второй ярус'
            else:
                new_sector_name: str = sector_name
            if 'правая' in sector_name:
                sector_name: str = f'{new_sector_name}. Правая сторона, ложа ' + number_lozha
            else:
                sector_name: str = f'{new_sector_name}. Левая сторона, ложа ' + number_lozha
        elif 'Бельэтаж' in sector_name:
            sector_name: str = 'Балкон бельэтажа'

        return sector_name, row, seat, price

    def body(self):
        super().body()
