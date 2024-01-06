import json
import time

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class CskaHockeyParser(AsyncSeatsParser):
    event = 'tickets.cska-hockey.ru'
    url_filter = lambda event: 'tickets.cska-hockey.ru' in event

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

        self.csrf = ''

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, a_sectors, place_name):
        cska_arena_reformat_dict = {
            '': 'Ложа 401',
            '': 'Ложа 402',
            '': 'Ложа 403',
            '': 'Ложа 404',
            '': 'Ложа 405',
            '': 'Ложа 406',
            '': 'Ложа 407',
            '': 'Ложа 408',
            '': 'Ложа 409',
            '': 'Ложа 410',
            '': 'Ложа 411',
            '': 'Ложа 412',
            '': 'Ложа 413',
            '': 'Ложа 414',
            '': 'Ложа 415',
            '': 'Ложа 416',
            '': 'Ложа 417',
            '': 'Ложа 418',
            '': 'Ложа 419',
            '': 'Ложа 420',
            '': 'Ложа 421',
            '': 'Ложа 422',
            '': 'Ложа 423',
            '': 'Ложа 424',
            '': 'Ложа 425',
            '': 'Ложа 426',
            '': 'Ложа 427',
            '': 'Ложа 428',
            '': 'Ложа 429',
            '': 'Ложа 430',
            '': 'Ложа 431',
            '': 'Ложа 432',
            '': 'Ложа 433',
            '': 'Ложа 434',
            '': 'Ложа 435',
            '': 'Ложа 436',
            '': 'Ложа 301',
            '': 'Ложа 302',
            '': 'Ложа 303',
            '': 'Ложа 304',
            '': 'Ложа 305',
            '': 'Ложа 306',
            '': 'Ложа 307',
            '': 'Ложа 308',
            '': 'Ложа 309',
            '': 'Ложа 310',
            '': 'Ложа 311',
            '': 'Ложа 312',
            '': 'Ложа 313',
            '': 'Ложа 314',
            '': 'Ложа 315',
            '': 'Ложа 316',
            '': 'Ложа 317',
            '': 'Ложа 318',
            '': 'Ложа 319',
            '': 'Ложа 320',
            '': 'Ложа 321',
            '': 'Ложа 322',
            '': 'Ложа 323',
            '': 'Ложа 324',
            '': 'Ложа 325',
            '': 'Ложа 326',
            '': 'Ложа 327',
            '': 'Ложа 328',
            '': 'Ложа 329',
            '': 'Ложа 330',
            '': 'Ложа 331',
            '': 'Ложа 332',
            '': 'Ложа 333',
            '': 'Ложа 334',
            '': 'Ложа 335',
            '': 'Ложа 336',
            '': 'Ложа 337',
            '': 'Ложа 338',
            '': 'Ложа 339',
            '': 'Ложа 340',
            '': 'Ложа 341',
            '501': 'Сектор 501',
            '502': 'Сектор 502',
            '503': 'Сектор 503',
            '504': 'Сектор 504',
            '505': 'Сектор 505',
            '506': 'Сектор 506',
            '507': 'Сектор 507',
            '508': 'Сектор 508',
            '509': 'Сектор 509',
            '510': 'Сектор 510',
            '511': 'Сектор 511',
            '512': 'Сектор 512',
            '513': 'Сектор 513',
            '514': 'Сектор 514',
            '201': 'Сектор 201',
            '202': 'Сектор 202',
            '203': 'Сектор 203',
            '204': 'Сектор 204',
            '205': 'Сектор 205',
            '206': 'Сектор 206',
            '207': 'Сектор 207',
            '208': 'Сектор 208',
            '209': 'Сектор 209',
            '210': 'Сектор 210',
            '211': 'Сектор 211',
            '212': 'Сектор 212',
            '213': 'Сектор 213',
            '214': 'Сектор 214',
        }

        ref_dict = {}
        if 'цска арена' in self.venue.lower():
            ref_dict = cska_arena_reformat_dict

        for sector in a_sectors:
            sector['name'] = ref_dict.get(sector['name'], sector['name'])

    async def skip_queue(self, id_queue):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://cska-hockey.queue.infomatika.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        params = [
            ('x-accel-expires', '0')
        ]
        url = 'https://cska-hockey.queue.infomatika.ru/api/users/' + id_queue
        while True:
            r = await self.session.get(url, data=params, headers=headers, verify=False)
            get_data = r.json()
            expired_at = get_data.get('expired_at')
            if expired_at is None:
                time.sleep(10)
            else:
                break
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://cska-hockey.queue.infomatika.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        url = 'https://tickets.cska-hockey.ru/?queue=' + id_queue
        r = await self.session.get(url, headers=headers, verify=False)
        if r.url == 'https://tickets.cska-hockey.ru/':
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru-RU,ru;q=0.9',
                'referer': 'https://tickets.cska-hockey.ru/',
                'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.user_agent,
            }
            r = await self.session.get(self.url, headers=headers, verify=False)
        return BeautifulSoup(r.text, 'lxml'), r

    async def get_event_data(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'referer': 'https://tickets.cska-hockey.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
        }
        r = await self.session.get(self.url, headers=headers, verify=False)
        soup = BeautifulSoup(r.text, 'lxml')
        if 'https://cska-hockey.queue.infomatika.ru/' in r.url:
            get_id = soup.select('body script')[0].text
            get_id = double_split(get_id, '}}("', '",')
            soup, r = await self.skip_queue(get_id)

        self.csrf = double_split(r.text, '<meta name="csrf-token" content="', '"')
        event_id = self.url.split('=')[-1]
    
        g = [sector for sector in soup.find_all('g', {'view_id': True}) if sector.get('free') != '0']
        sectors_info = {}

        for sector in g:
            sectors_info.update({
                    sector.get('view_id'):{
                        'name': sector.get('sector_name'), 'price': sector.get('price_max', 0)
                    }
                })
        return event_id, sectors_info

    async def get_all_sector_seats(self, event_id, sector_id):
        url = 'https://tickets.cska-hockey.ru/event/get-svg-places'
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'content-length': '130',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://tickets.cska-hockey.ru',
            'referer': self.url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-csrf-token': self.csrf,
            'x-requested-with': 'XMLHttpRequest',
        }
        data = {
            'event_id': event_id,
            'view_id': sector_id,
            '_csrf-frontend': self.csrf,
        }
        r = await self.session.post(url, headers=headers, data=data, verify=False)

        all_seats = {}
        for seat_zone, seats in r.json()['places'].items():
            for seat_id in seats:
                seat_id_f = seat_id + '[end]'
                row = double_split(seat_id_f, 'r', 'p')
                place = double_split(seat_id_f, 'p', '[end]')
                try:
                    price = [zone['price'] for zone in r.json()['zones'] if str(zone['zone']) == seat_zone][0]
                except IndexError:
                    continue
               
                all_seats[seat_id] = {
                    'row': row,
                    'place': place,
                    'price': price
                }

        return all_seats

    async def get_a_sector_seats(self, sector_id, event_id, sector_price):
        url = 'https://tickets.cska-hockey.ru/event/get-actual-places'
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://tickets.cska-hockey.ru',
            'referer': self.url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-csrf-token': self.csrf,
            'x-requested-with': 'XMLHttpRequest',
        }
        data = {
            'event_id': event_id,
            'view_id': sector_id,
            'clear_cache': 'false',
            '_csrf-frontend': self.csrf,
        }
        r = await self.session.post(url, headers=headers, data=data, verify=False)
        type_ = r.json()['places']['type']

        all_seats = await self.get_all_sector_seats(event_id, sector_id)
        a_seats = {} if type_ == 'free' else all_seats.copy()
        for seat in r.json()['places']['values']:
            if type_ == 'free':
                a_seats[seat['id']] = all_seats[seat['id']]
            else:
                del a_seats[seat['id']]

        return a_seats

    async def body(self):
        event_id, sectors_info = await self.get_event_data()

        a_sectors = []
        for sector_id, sector_info in sectors_info.items():
            sector_name = sector_info['name']
            sector_price = sector_info['price']
            seats = await self.get_a_sector_seats(sector_id, event_id, sector_price)

            for ticket in seats.values():
                row = str(ticket['row'])
                seat = str(ticket['place'])
                price = int(float(ticket['price']))
                for sector in a_sectors:
                    if sector_name == sector['name']:
                        sector['tickets'][row, seat] = price
                        break
                else:
                    a_sectors.append({
                        'name': sector_name,
                        'tickets': {(row, seat): price}
                    })

        self.reformat(a_sectors, self.venue)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
        #self.check_sectors()
