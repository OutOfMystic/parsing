from bs4 import BeautifulSoup
import re

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession


class Ska(AsyncSeatsParser):
    event = 'tickets.ska.ru'
    url_filter = lambda url: 'tickets.ska.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, a_sectors):
        cska_arena_reformat_dict = {
            '401': 'Сектор 401',
            '402': 'Сектор 402',
            '403': 'Сектор 403',
            '404': 'Сектор 404',
            '405': 'Сектор 405',
            '406': 'Сектор 406',
            '407': 'Сектор 407',
            '408': 'Сектор 408',
            '409': 'Сектор 409',
            '410': 'Сектор 410',
            '411': 'Сектор 411',
            '412': 'Сектор 412',
            '413': 'Сектор 413',
            '414': 'Сектор 414',
            '415': 'Сектор 415',
            '416': 'Сектор 416',
            '301': 'Ложа 301',
            '302': 'Ложа 302',
            '303': 'Ложа 303',
            '304': 'Ложа 304',
            '305': 'Ложа 305',
            '306': 'Ложа 306',
            '307': 'Ложа 307',
            '308': 'Ложа 308',
            '309': 'Ложа 309',
            '310': 'Ложа 310',
            '311': 'Ложа 311',
            '312': 'Ложа 312',
            '313': 'Ложа 313',
            '314': 'Ложа 314',
            '315': 'Ложа 315',
            '316': 'Ложа 316',
            '317': 'Ложа 317',
            '318': 'Ложа 318',
            '319': 'Ложа 319',
            '320': 'Ложа 320',
            '321': 'Ложа 321',
            '322': 'Ложа 322',
            '323': 'Ложа 323',
            '324': 'Ложа 324',
            '325': 'Ложа 325',
            '326': 'Ложа 326',
            '327': 'Ложа 327',
            '328': 'Ложа 328',
            '329': 'Ложа 329',
            '330': 'Ложа 330',
            '331': 'Ложа 331',
            '332': 'Ложа 332',
            '333': 'Ложа 333',
            '334': 'Ложа 334',
            '335': 'Ложа 335',
            '336': 'Ложа 336',
            '337': 'Ложа 337',
            '338': 'Ложа 338',
            '339': 'Ложа 339',
            '340': 'Ложа 340',
            '341': 'Ложа 341',
            '342': 'Ложа 342',
            '343': 'Ложа 343',
            '344': 'Ложа 344',
            '345': 'Ложа 345',
            '346': 'Ложа 346',
            '347': 'Ложа 347',
            '348': 'Ложа 348',
            '349': 'Ложа 349',
            '350': 'Ложа 350',
            '351': 'Ложа 351',
            '352': 'Ложа 352',
            '353': 'Ложа 353',
            '354': 'Ложа 354',
            '355': 'Ложа 355',
            '356': 'Ложа 356',
            '357': 'Ложа 357',
            '358': 'Ложа 358',
            '359': 'Ложа 359',
            '360': 'Ложа 360',
            '361': 'Ложа 361',
            '362': 'Ложа 362',
            '363': 'Ложа 363',
            '364': 'Ложа 364',
            '365': 'Ложа 365',
            '366': 'Ложа 366',
            '367': 'Ложа 367',
            '368': 'Ложа 368',
            '369': 'Ложа 369',
            '370': 'Ложа 370',
            '371': 'Ложа 371',
            '372': 'Ложа 372',
            '373': 'Ложа 373',
            '374': 'Ложа 374',
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
            '215': 'Сектор 215',
            '216': 'Сектор 216',
        }

        if 'ледовый дворец' in self.venue.lower():
            ref_dict = cska_arena_reformat_dict
            for sector in a_sectors:
                sector['name'] = ref_dict.get(sector['name'], sector['name'])
        if 'ска арена (хкска)' in self.venue.lower():
            for sector in a_sectors:
                if 'ресторан' not in sector['name'].lower():
                    sector_main = sector['name']
                    number = re.search(r'\d+', sector_main)[0]
                    if number[0] in ('5', '4'):
                        sector['name'] = f'Ложа {number}'
                    elif number[0] in ('6', '2', '3'):
                        sector['name'] = f'Сектор {number}'
    async def parse_seats(self, soup):
        total_sector = []

        text_js = soup.find('div', class_='wrp-main').find('script').text
        no_render_data = text_js[text_js.index('['):text_js.index('];')+1]
        dict_data = eval(no_render_data.replace('null', 'None'))

        for sectors in dict_data:
            sector = sectors.get('name')
            if sector:
                sector_id = sectors.get('id')

                url_split = self.url.split("/")
                url_sector = f'seats-list/{url_split[-1]}/{sector_id}'
                url_to_sector = '/'.join(url_split[:-2]) + '/' + url_sector

                r = await self.get_html(url=url_to_sector)
                json_request = r.json()

                list_price_in_json = json_request.get('prices')[::-1]
                if len(list_price_in_json) == 0:
                    continue
                dict_prices = {}
                for price in list_price_in_json:
                    category = price.get('categoryName')
                    if category == 'Коммерческий':
                        prices_id = price.get('pricezoneId')
                        count_price = price.get('value')
                        dict_prices[prices_id] = count_price

                total_seats_row_prices = {}
                list_seat_in_json = json_request.get('seats')
                for seats in list_seat_in_json:
                    pricezon_id = seats.get('pricezoneId')
                    price_for_seat = dict_prices.get(pricezon_id)

                    if price_for_seat is None:
                        continue

                    seat_and_row = seats.get('name')
                    seat_and_row_list = seat_and_row.split()
                    seat_in_sector = seat_and_row_list[-1]
                    row_in_sector = seat_and_row_list[3]
                    if str(sector)[0] == '3':
                        row_in_sector = '1'
                    seat_and_row = (row_in_sector, seat_in_sector,)

                    total_seats_row_prices[seat_and_row] = int(price_for_seat.split('.')[0])

                total_sector.append(
                    {
                        "name": str(sector),
                        "tickets": total_seats_row_prices
                    }
                )

        return total_sector

    async def get_html(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'tickets.ska.ru',
            'sec-ch-ua': '"Chromium";v="106", "Yandex";v="22", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        return r

    async def get_seats(self):
        r = await self.get_html(url=self.url)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = await self.parse_seats(soup)

        return a_events

    async def body(self):
        all_sectors = await self.get_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            #self.debug(sector['name'], len(sector['tickets']))
            self.register_sector(sector['name'], sector['tickets'])