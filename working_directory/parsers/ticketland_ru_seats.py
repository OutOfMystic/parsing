import re

from requests.exceptions import JSONDecodeError, ProxyError
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.utils.logger import track_coroutine
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.utils import provision


class LenkomParser(AsyncSeatsParser):
    event = 'ticketland.ru'
    proxy_check = SpecialConditions(url='https://www.ticketland.ru/')
    url_filter = lambda url: 'ticketland.ru' in url and 'lenkom' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.limit = None
        self.is_special_sale = None
        self.performance_id = None
        self.tl_csrf_no_f = None
        self.delay = 1200
        self.driver_source = None
        self.venue = 'Ленком'
        self.count_error = 0

    @track_coroutine
    async def get_tl_csrf_and_data(self):
        result = await self.multi_try(self._get_tl_csrf_and_data, tries=5, raise_exc=False)
        if result == provision.TryError:
            print(' provision.TryError:')
            result = None
        return result

    @track_coroutine
    async def _get_tl_csrf_and_data(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp'
                      ',image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        # r = self.session.get(self.url, headers=headers)
        r_text, r_json = await self.multi_try(self.request_to_ticketland, tries=5, args=[self.url, headers])
        if r_text is None and r_json is None or 'CDbException' in r_text: 
            self.count_error += 1
            if self.count_error == 50:
                await self.change_proxy(report=True)
                raise ProxyError('ticketland seats parser except ProxyError')
            await self.change_proxy()
            return await self._get_tl_csrf_and_data()
        try:
            soup = BeautifulSoup(r_text, 'lxml')
            tl_csrf = soup.find('meta', attrs={'name':'csrf-token'}).get('content')
            #tl_csrf = double_split(r_text, '<meta name="csrf-token" content="', '"')
        except Exception as ex:
            self.error(f'Error finding csrf-token {ex} {r_text} {self.url}  {r_json}')
            self.count_error += 1
            await self.change_proxy()
            return await self._get_tl_csrf_and_data()
            #tl_csrf = double_split(r_text, '<meta name="csrf-token" content="', '"')

        if 'performanceId:' not in r_text:
            return None
        performance_id = double_split(r_text, 'performanceId: ', ',')
        if 'maxTicketCount' not in r_text:
            return None

        limit = double_split(r_text, 'maxTicketCount: ', ',')
        is_special_sale = double_split(r_text, "isSpecialSale: '", "'")

        return tl_csrf.replace('=', '%3D'), performance_id, limit, is_special_sale

    @track_coroutine
    async def before_body(self):
        self.session = AsyncProxySession(self)
        await self._get_init_vars_if_not_given()

    @track_coroutine
    async def _get_init_vars_if_not_given(self):
        if self.performance_id:
            return True
        event_vars = await self.get_tl_csrf_and_data()
        if event_vars:
            self.tl_csrf_no_f, self.performance_id, self.limit, self.is_special_sale = event_vars
            return True
        else:
            self.info('Waiting event vars')
            return False

    @track_coroutine
    async def request_to_ticketland(self, url, headers=None):
        try:
            r = await self.session.get(url, headers=headers, verify=False)
        except ProxyError:
            return None, None
        if '<div id="id_spinner" class="container"><div class="load">Loading...</div>' in r.text:
            raise Exception('Запрос с загрузкой')
        try:
            return r.text, r.json()
        except:
            return r.text, None

    def get_scene(self):
        pass

    def reformat(self, sectors, scene):
        for sector in sectors:
            if 'неудоб' in sector['name'].lower():
                sector['name'] = sector['name'].replace(' (неудобное)', '')

    def reformat_seat(self, sector_name, row, seat, price, ticket):
        return sector_name, row, seat, price

    @track_coroutine
    async def body(self):
        if not await self._get_init_vars_if_not_given():
            return False
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
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        # r = self.session.get(url, headers=headers)
        r_text, r_json = await self.multi_try(self.request_to_ticketland, tries=5, args=[url, headers])
        if r_text is None and r_json is None or 'CDbException' in r_text or 'Технические работы' in r_text:
            self.count_error += 1
            if self.count_error == 50:
                await self.change_proxy(report=True)
                raise ProxyError('ticketland seats parser except ProxyError')
            await self.change_proxy()
            return await self._get_tl_csrf_and_data()

        if '"Unable to verify your data submission."' in r_text:
            await self.change_proxy()
        if 'CDbException' in r_text:
            await self.change_proxy()
        if '""' in r_text:
            await self.change_proxy()
        if isinstance(r_json, str):
            self.error(f'Error {r_json} {self.url} {r_text} ')
            return
        if r_json is None:
            self.error(f'(1-st step)r_json is None == True {r_json} {self.url}')
            try:
                self.count_error += 1
                await self.change_proxy()
                return await self._get_tl_csrf_and_data()
            except:
                self.error(f'(2-nd step r_json is None == True {r_json} {self.url}')
            return
        try:
            all_tickets = r_json.get('places')
        except AttributeError as err:
            self.debug(f'AttributeError{self.url} {r_json} {r_text}')
            raise err

        a_sectors = []
        for ticket in all_tickets:
            row = ticket['row']
            seat = ticket['place']
            cost = int(ticket['price'])
            sector_name = ticket['section']['name']
            sector_name, row, seat, cost = self.reformat_seat(sector_name, row, seat, cost, ticket)
            if sector_name is None:
                continue

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
            #self.info(sector['name'], len(sector['tickets']) )
            self.register_sector(sector['name'], sector['tickets'])
        #self.check_sectors()


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
                    self.debug(sector['name'].split()[:-1])
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
                    sector['name'] = sector['name'] + ' Нету на схеме'

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


class MalyyParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'malyy' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        maly_ref = {
            'Ложа 1-го яруса №1 правая': 'Ложа первого яруса №1, правая сторона',
            'Ложа 1-го яруса №2 правая': 'Ложа первого яруса №2, правая сторона',
            'Ложа 1-го яруса №3 правая': 'Ложа первого яруса №3, правая сторона',
            'Ложа 1-го яруса №4 правая': 'Ложа первого яруса №4, правая сторона',
            'Ложа 1-го яруса №5 правая': 'Ложа первого яруса №5, правая сторона',
            'Ложа 1-го яруса №6 правая': 'Ложа первого яруса №6, правая сторона',
            'Ложа 1-го яруса №1 левая': 'Ложа первого яруса №1, левая сторона',
            'Ложа 1-го яруса №2 левая': 'Ложа первого яруса №2, левая сторона',
            'Ложа 1-го яруса №3 левая': 'Ложа первого яруса №3, левая сторона',
            'Ложа 1-го яруса №4 левая': 'Ложа первого яруса №4, левая сторона',
            'Ложа 1-го яруса №5 левая': 'Ложа первого яруса №5, левая сторона',
            'Ложа 1-го яруса №6 левая': 'Ложа первого яруса №6, левая сторона',
            'Ложа бельэтажа №1 левая': 'Ложа бельэтажа №1, левая сторона',
            'Ложа бельэтажа №2 левая': 'Ложа бельэтажа №2, левая сторона',
            'Ложа бельэтажа №3 левая': 'Ложа бельэтажа №3, левая сторона',
            'Ложа бельэтажа №4 левая': 'Ложа бельэтажа №4, левая сторона',
            'Ложа бельэтажа №5 левая': 'Ложа бельэтажа №5, левая сторона',
            'Ложа бельэтажа №6 левая': 'Ложа бельэтажа №6, левая сторона',
            'Ложа бельэтажа №1 правая': 'Ложа бельэтажа №1, правая сторона',
            'Ложа бельэтажа №2 правая': 'Ложа бельэтажа №2, правая сторона',
            'Ложа бельэтажа №3 правая': 'Ложа бельэтажа №3, правая сторона',
            'Ложа бельэтажа №4 правая': 'Ложа бельэтажа №4, правая сторона',
            'Ложа бельэтажа №5 правая': 'Ложа бельэтажа №5, правая сторона',
            'Ложа бельэтажа №6 правая': 'Ложа бельэтажа №6, правая сторона',
            'Ложа бенуара №1 правая': 'Ложа бенуара №1, правая сторона',
            'Ложа бенуара №2 правая': 'Ложа бенуара №2, правая сторона',
            'Ложа бенуара №3 правая': 'Ложа бенуара №3, правая сторона',
            'Ложа бенуара №4 правая': 'Ложа бенуара №4, правая сторона',
            'Ложа бенуара №1 левая': 'Ложа бенуара №1, левая сторона',
            'Ложа бенуара №2 левая': 'Ложа бенуара №2, левая сторона',
            'Ложа бенуара №3 левая': 'Ложа бенуара №3, левая сторона',
            'Ложа бенуара №4 левая': 'Ложа бенуара №4, левая сторона',
            'Балкон 2-й ярус': 'Балкон второго яруса',
            'Балкон 1-й ярус': 'Балкон первого яруса',
            'Ложа бельэтажа левая №1': 'Ложа бельэтажа 1 левая сторона',
            'Ложа бельэтажа левая №2': 'Ложа бельэтажа 2 левая сторона',
            'Ложа бельэтажа левая №3': 'Ложа бельэтажа 3 левая сторона',
            'Ложа бельэтажа правая №1': 'Ложа бельэтажа 1 правая сторона',
            'Ложа бельэтажа правая №2': 'Ложа бельэтажа 2 правая сторона',
            'Ложа бельэтажа правая №3': 'Ложа бельэтажа 3 правая сторона',
            'Ложа бенуара левая №1': 'Ложа бенуара 1 левая сторона',
            'Ложа бенуара левая №2': 'Ложа бенуара 2 левая сторона',
            'Ложа бенуара левая №3': 'Ложа бенуара 3 левая сторона',
            'Ложа бенуара левая №4': 'Ложа бенуара 4 левая сторона',
            'Ложа бенуара правая №1': 'Ложа бенуара 1 правая сторона',
            'Ложа бенуара правая №2': 'Ложа бенуара 2 правая сторона',
            'Ложа бенуара правая №3': 'Ложа бенуара 3 правая сторона',
            'Ложа бенуара правая №4': 'Ложа бенуара 4 правая сторона',
        }
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ')
            sector['name'] = sector['name'].strip()
            if sector['name'] in maly_ref:
                sector['name'] = maly_ref.get(sector['name'])

            elif sector['name'] == 'Балкон 2 ярус':
                sector['name'] = "Балкон второго яруса"
            elif sector['name'] == 'Балкон 1 ярус':
                sector['name'] = "Балкон первого яруса"
            elif '№' in sector['name']:
                sector['name'] = sector['name'].replace('№ ', '№')
                sector['name'] = sector['name'].replace(' правая сторона', ', правая сторона')
                sector['name'] = sector['name'].replace(' левая сторона', ', левая сторона')

                if 'Ложа 1 яруса' in sector['name']:
                    sector['name'] = sector['name'].replace('Ложа 1 яруса', 'Ложа первого яруса')

            elif ' левая №' in sector['name']:
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


# class NaciyParser(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'ticketlanzd.ru' in url and 'naciy' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             sector['name'] = sector['name'].replace('  ', ' ')

#             if 'ложи' in sector['name'].lower():
#                 sector['name'] = sector['name'].capitalize()

#     async def body(self):
#         super().body()


# class OperettyParser(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'ticketlanzd.ru' in url and 'operetty' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             sector['name'] = sector['name'].replace('  ', ' ')

#     async def body(self):
#         super().body()


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

            if 'Бельэтаж ложа' in sector['name']:
                sector_name = sector['name'].split()
                sector['name'] = sector_name[0] + ', ' + ' '.join(sector_name[1:])
            elif 'VIP Партер' == sector['name']:
                sector['name'] = 'VIP-партер'
            elif 'Высокий партер' == sector['name']:
                sector['name'] = 'Партер'

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


# class SatireParser(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'ticketland.ru' in url and 'teatr-satiry' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             seats_change_row = {}
#             sector['name'] = sector['name'].replace('  ', ' ')
#             sector_name_low = sector['name'].lower()

#             # Основная сцена
#             if 'партер' in sector_name_low or 'амфитеатр' in sector_name_low:
#                 sector['name'] = sector['name'].replace(' правая сторона', '').replace(' левая сторона', '')

#             elif 'ложа правая' == sector_name_low or 'правая ложа' == sector_name_low\
#                     or 'правая Ложа' in sector_name_low or 'левая ложа' in sector_name_low:
#                 sector['name'] = 'Ложа'

#                 for row, seat in sector['tickets']:
#                     seats_change_row[row, seat] = sector['tickets'][row, seat]

#             for row, seat in seats_change_row:
#                 del sector['tickets'][row, seat]

#                 true_row = {
#                     '1 2 3 4 5 ': '1',
#                     '6 6отк. 7 8 ': '2',
#                     '9 9отк. 10 ': '3',
#                     '11 12': '4',
#                     '13': '5',
#                 }

#                 row_ = ''
#                 for seats in true_row:
#                     if seat in seats:
#                         row_ = true_row[seats]
#                         break

#                 sector['tickets'][row_, seat] = seats_change_row[row, seat]

#     async def body(self):
#         super().body()


# class OperettaParser(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'ticketland.ru' in url and 'teatr-operetty' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             sector['name'] = sector['name'].replace('  ', ' ')

#     async def body(self):
#         super().body()


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


# class MkhatGorkyParser(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'ticketland.ru' in url and 'mkhat-im-m-gorkogo' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             sector['name'] = sector['name'].replace('  ', ' ').capitalize()
#             sec_name_low = sector['name'].lower()

#             # TODO С сайта приходят данные о местах в этом секторе, при это на самом сайте их выбрать нельзя
#             # TODO сектор отрезан на схеме как бы
#             sector['name'] = sector['name'].replace('1-й', 'Первый')

#             # TODO Ложа А и Д не настроены
#             if 'vip партер' in sec_name_low:
#                 sector['name'] = 'VIP-партер'
#             elif ' ложа' in sec_name_low:
#                 sector['name'] = sector['name'].replace(' ложа', ', ложа')
#             elif 'Высокий партер' == sector['name']:
#                 sector['name'] = 'Партер'

#     async def body(self):
#         super().body()


# class VernadskogoCirk(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'ticketland.ru' in url and 'bolshoy-moskovskiy-cirk' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             sector['name'] = sector['name'].title()

#     async def body(self):
#         super().body()


# class MtsLiveKhollMoskva(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'ticketland.ru' in url and 'mts-live-kholl-moskva' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             sector_name = sector['name'].split()
#             if 'танцевальный партер' in sector['name'].lower():
#                 sector['name'] = 'Танцпол'
#             elif 'meet&greet' == sector['name'].lower():
#                 sector['name'] = ' Meet & Greet'
#             elif 'vip dance' == sector['name'].lower():
#                 sector['name'] = 'VIP Dance'
#             elif 'vip lounge' == sector['name'].lower():
#                 sector['name'] = 'VIP Lounge'
#             elif 'vip' in sector['name'].lower():
#                 if 'vip' in sector_name[0].lower():
#                     sector_name[0] = sector_name[0].upper()
#                     sector['name'] = ' '.join(sector_name)
#                 elif 'vip' in sector_name[1].lower():
#                     sector_name[0] = sector_name[0].title()
#                     sector_name[1] = sector_name[1].upper()
#                     if len(sector_name) == 2:
#                         sector['name'] = ' '.join(sector_name[:2]) + ', центр'
#                     else:
#                         sector_name[2] = sector_name[2].lower()
#                         sector_name[3] = sector_name[3].lower()
#                         sector['name'] = ' '.join(sector_name[:2]) + ', ' + ' '.join(sector_name[2:])

#     async def body(self):
#         super().body()


class AleksandrinskiyTeatr(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'spb.ticketland.ru' in url and 'aleksandrinskiy-teatr' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            if 'Ложа бельэтажа' in sector['name']:
                sector_nm = re.findall(r'\d+', sector['name'])[-1]
                row_number = 'Ложа ' + sector_nm 
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = 'Бельэтаж'

            elif '1 ярус' in sector['name'] or 'Ярус 1' in sector['name']:
                tickets = sector['tickets']
                if '.' in sector['name']:
                    row_name = sector['name'].split('.')[0]
                    #'Ложа 1. Ярус 2 (место с ограниченным'
                else:
                    row_name = re.search(r'яруса \d+', sector['name'])[0]
                    row_number = row_name.split()[-1]
                    row_name = f'Ложа {row_number}'
                    #'Ложа 1 яруса 4 (место с ограниченным'
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_name, seat)] = price
                sector['name'] = '1 ярус'

            elif '2 ярус' in sector['name'] or 'Ярус 2' in sector['name']:
                tickets = sector['tickets']
                if '.' in sector['name']:
                    row_name = sector['name'].split('.')[0]
                else:
                    row_name = re.search(r'яруса \d+', sector['name'])[0]
                    row_number = row_name.split()[-1]
                    row_name = f'Ложа {row_number}'
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_name, seat)] = price
                sector['name'] = '2 ярус'

            elif '3 ярус' in sector['name'] or 'Ярус 3' in sector['name']:
                tickets = sector['tickets']
                if '.' in sector['name']:
                    row_name = sector['name'].split('.')[0]
                else:
                    row_name = re.search(r'яруса \d+', sector['name'])[0]
                    row_number = row_name.split()[-1]
                    row_name = f'Ложа {row_number}'
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_name, seat)] = price
                sector['name'] = '3 ярус'

            elif '4 ярус' in sector['name'] or 'Ярус 4' in sector['name']:
                tickets = sector['tickets']
                if '.' in sector['name']:
                    row_name = sector['name'].split('.')[0]
                else:
                    row_name = re.search(r'яруса \d+', sector['name'])[0]
                    row_number = row_name.split()[-1]
                    row_name = f'Ложа {row_number}'
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_name, seat)] = price
                sector['name'] = '4 ярус'

            elif 'Балкон 3-го яруса' in sector['name']:
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    row, seat = ticket_row_and_seat
                    sector['tickets'][(row, seat)] = price
                sector['name'] = 'Балкон 3го яруса'

            elif 'Царская ложа' in sector['name']:
                row_number = '1'
                tickets = sector['tickets']
                sector['tickets'] = {}
                for ticket_row_and_seat, price in tickets.items():
                    _, seat = ticket_row_and_seat
                    sector['tickets'][(row_number, seat)] = price
                sector['name'] = 'Царская ложа'
        
    def reformat_seat(self, sector_name, row, seat, price, ticket):
        if 'Сцена' in sector_name:
            return None, row, seat, price
        return sector_name, row, seat, price


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


class UgolokDedushkiDurova(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'www.ticketland.ru' in url and 'teatr-ugolok-dedushki-durova' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        ...


# class SovremennikTeatr(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'www.ticketland.ru' in url and 'moskovskiy-teatr-sovremennik' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         for sector in sectors:
#             if 'Ложа бельэтажа' in sector['name']:
#                 sector['name'] = f'{sector["name"].split()[-1].title()} ложа бельэтажа'
#             if 'Сектора А, В, C' in self.scheme.name:
#                 sector['name'] = sector['name'].replace('Партер', 'Сектор')

#     async def body(self):
#         super().body()


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
            sector_name = 'Партер'
        elif 'Партер' in sector_name and 'Гардероб' in sector_name:
            sector_name = 'Партер'
        elif 'бельэтаж' in sector_name.lower() and 'ложа' not in sector_name.lower():
            sector_name = 'Балкон бельэтажа'
        elif 'Балкон' in sector_name:
            if '3го яруса' in sector_name or '3-го яруса' in sector_name:
                sector_name = 'Балкон третьего яруса'
        elif 'Партер-трибуна' in sector_name:
            sector_name = 'Кресла партера'
        elif 'Галерея 3го яр.' in sector_name or 'Галерея 3-го яруса' in sector_name or\
                'Галерея третьего яруса' in sector_name:
            row = ''
            if 'правая' in sector_name.lower() or 'пр. ст.' in sector_name.lower():
                sector_name = 'Галерея третьего яруса. Правая сторона'
            else:
                sector_name = 'Галерея третьего яруса. Левая сторона'
        elif 'Места за креслами' in sector_name:
            sector_name = 'Места за креслами'
        elif 'Партер' in sector_name:
            sector_name = 'Кресла партера'
        elif 'ложи' in sector_name or 'ложа' in sector_name.lower():
            if '№' in sector_name:
                number_lozha = sector_name.split()[1].replace('№', '')
                if not number_lozha.isnumeric():
                    index_number = sector_name.index('№') + 1
                    number_lozha = sector_name[index_number:index_number + 1]
                    if not number_lozha.isnumeric():
                        number_lozha = sector_name[index_number]
            elif sector_name.split()[1] in ['А', 'Б', 'В', 'Г']:
                number_lozha = sector_name.split()[1]
            else:
                number_lozha = sector_name.split()[-1]
            if 'бельэтаж' in sector_name.lower():
                new_sector_name = 'Бельэтаж'
            elif 'бенуар' in sector_name.lower():
                new_sector_name = 'Бенуар'
            elif '2-го яруса' in sector_name.lower():
                new_sector_name = 'Второй ярус'
            else:
                new_sector_name = sector_name
            x_coordinate = ticket['x']
            if x_coordinate < 700:
                sector_name = f'{new_sector_name}. Левая сторона, ложа ' + number_lozha
            else:
                sector_name = f'{new_sector_name}. Правая сторона, ложа ' + number_lozha
        elif sector_name == 'Свободная рассадка':
            sector_name = None

        return sector_name, row, seat, price


class BdtKamennoostrovskiyTeatr(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'kamennoostrovskiy-teatr' in url 

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        for sector in sectors:
            if 'ложа' in sector['name'].lower():
                number_lozha = sector['name'].split('№')[-1]
                if '1 яруса' in sector['name']:
                    sector['name'] = 'Первый ярус, ложа ' + number_lozha
                elif 'бельэтаж' in sector['name'].lower():
                    sector['name'] = 'Бельэтаж, ложа ' + number_lozha
                elif 'бенуар' in sector['name'].lower():
                    sector['name'] = 'Бенуар, ложа ' + number_lozha
                new_tickets = {}
                tickets = sector['tickets']
                for row_and_seat, price in tickets.items():
                    new_tickets[('1', row_and_seat[1])] = price
                sector['tickets'] = new_tickets
            elif 'Партер свободная рассадка' == sector['name']:
                sector['name'] = 'Партер'
            elif 'Ложи' in sector['name']:
                if '1 Яруса' in sector['name']:
                    sector['name'] = 'Ложи первого яруса'
                elif 'бельэт' in sector['name']:
                    sector['name'] = 'Ложи бельэтажа'
                else:
                    sector['name'] = 'Ложи бенуара'
                new_tickets = {}
                tickets = sector['tickets']
                for row_and_seat, price in tickets.items():
                    new_tickets[('1', row_and_seat[1])] = price
                sector['tickets'] = new_tickets


class MikhailovskyTeatr(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'spb.ticketland.ru' in url and 'mikhaylovskiy-teatr' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat(self, sectors, scene):
        ...

    def reformat_seat(self, sector_name, row, seat, price, ticket):
        if 'Партер' in sector_name:
            sector_name = 'Партер'
        elif 'Ложа' in sector_name:
            if 'бельэтажа' in sector_name:
                sector_name = 'Ложи бельэтажа'
            elif 'бенуара' in sector_name:
                sector_name = 'Ложи бенуара'
            elif '1-го яруса' in sector_name:
                sector_name = 'Ложи 1 яруса'
            elif '2-го яруса' in sector_name:
                sector_name = 'Ложи 2 яруса'
            elif '3-го яруса' in sector_name:
                sector_name = 'Ложи 3 яруса'
        elif 'ЛОЖА' in sector_name:
            sector_name = 'Ложа' + ' ' + sector_name.split()[-1]
        elif '1-й ярус' in sector_name or '1-Й Ярус' in sector_name:
            sector_name = '1 ярус'
        elif '2-й ярус' in sector_name or '2-Й Ярус' in sector_name:
            sector_name = '2 ярус'
        elif '3-й ярус' in sector_name or '3-Й Ярус' in sector_name:
            sector_name = '3 ярус'
        elif 'Кресла Бенуар' in sector_name:
            sector_name = 'Бенуар'
        elif 'Кресла Бельэтаж' in sector_name:
            sector_name = 'Бельэтаж'

        return sector_name, row, seat, price


# class TicketlandVdnh(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'www.ticketland.ru' in url and 'vystavochnye-centry' in url and 'vdnh' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         ...

#     async def body(self):
#         super().body()


# class TeatrArmii(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'www.ticketland.ru' in url and 'teatr-rossiyskoy-armii' in url

#     def __init__(self, *args, **extra):
#         super().__init__(*args, **extra)

#     def reformat(self, sectors, scene):
#         ...

#     async def body(self):
#         super().body()


# class TeatrErmolovoy(LenkomParser):
#     event = 'ticketland.ru'
#     url_filter = lambda url: 'www.ticketland.ru' in url and 'teatr-im-ermolovoy' in url

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     def reformat(self, sectors, scene):
#         ...

#     async def body(self):
#         super().body()


class RAMT(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'www.ticketland.ru' in url and 'ramt' in url

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def reformat(self, sectors, scene):
        ramt_ref = {
            'Бельэтаж - правая сторона': 'Бельэтаж, правая сторона',
            'Бельэтаж - левая сторона': 'Бельэтаж, левая сторона',
            'Бельэтаж - середина': 'Бельэтаж, середина',
            'Партер - правая сторона': 'Партер, правая сторона',
            'Партер -  левая сторона': 'Партер, левая сторона',
            'Партер - левая сторона': 'Партер, левая сторона',
            'Партер - середина': 'Партер, середина',
            '1-й ярус - середина': '1 ярус, середина',
            '1 ярус-лев.ст. неудобное место': '1 ярус, левая сторона, места с ограниченной видимостью',
            '1-й ярус - лев. ст. ограниченная вид': '1 ярус, левая сторона, места с ограниченной видимостью',
            '1-й ярус - прав. ст. ограниченная вид': '1 ярус, правая сторона, места с ограниченной видимостью',
            '1 ярус-прав.ст. неудобное место': '1 ярус, правая сторона, места с ограниченной видимостью',
            '1-й ярус - прав. ст. ограниченная ви': '1 ярус, правая сторона, места с ограниченной видимостью',
            '1 ярус, левая сторона, места с огран': '1 ярус, левая сторона, места с ограниченной видимостью',
            '1 ярус, правая сторона, места с огра': '1 ярус, правая сторона, места с ограниченной видимостью',
            '1 ярус, левая сторона, неудобные мес': '1 ярус, левая сторона, места с ограниченной видимостью',
            '1 ярус, правая сторона, неудобные ме': '1 ярус, правая сторона, места с ограниченной видимостью',
            'Партер - прав.ст. ограниченная видим': 'Партер, правая сторона',
            'Партер - лев.ст. ограниченная видимо': 'Партер, левая сторона',
        }
        for sector in sectors:
            sector['name'] = sector['name'].strip()
            if sector['name'] in ramt_ref:
                sector['name'] = ramt_ref.get(sector['name'])


class TeatrGogolya(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'www.ticketland.ru' in url and 'teatr-im-nvgogolya' in url
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def reformat(self, sectors, scene):
        ...


class Kreml(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'www.ticketland.ru' in url and 'kremlevskiy-dvorec/novogodnee-predstavlenie' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)

    def reformat_seat(self, sector_name, row, seat, price, ticket):
        ref_kreml = {
            'Партер середина': 'Партер, середина',
            'Партер левая сторона': 'Партер, левая сторона',
            'Партер правая сторона': 'Партер, правая сторона',
            'Балкон правая сторона': 'Балкон, правая сторона',
            'Балкон-середина': 'Балкон, середина',
            'Балкон левая сторона': 'Балкон, левая сторона',
            'Амфитеатр-середина': 'Амфитеатр, середина',
            'Амфитеатр левая сторона': 'Амфитеатр, левая сторона',
            'Амфитеатр правая сторона': 'Амфитеатр, правая сторона',
            'Ложа балкона левая': 'Ложа балкона, левая сторона',
            'Ложа балкона правая': 'Ложа балкона, правая сторона',
            'Балкон лев.ст. откидное': 'Балкон, левая сторона (откидные)',
            'Балкон прав.ст. откидное': 'Балкон, правая сторона (откидные)'
        }
        sector_name = ref_kreml.get(sector_name, sector_name)
        return sector_name, row, seat, price
    
    def reformat(self, sectors, scene):
        pass
