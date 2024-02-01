from bs4 import BeautifulSoup
import ssl

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.utils.parse_utils import double_split


class Icetickets(AsyncSeatsParser):
    proxy_check = NormalConditions()
    event = 'icetickets.ru'
    url_filter = lambda url: 'icetickets.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, a_sectors):
        kreml_reformat_dict = {
            'Ложа балкона левая': 'Ложа балкона, левая сторона',
            'Ложа балкона правая': 'Ложа балкона, правая сторона',
            'Балкон прав.ст. откидное': 'Балкон, правая сторона (откидные)',
            'Балкон лев.ст. откидное': 'Балкон, левая сторона (откидные)',
            'Балкон-середина': 'Балкон, середина',
            'Балкон правая сторона': 'Балкон, правая сторона',
            'Балкон левая сторона': 'Балкон, левая сторона',
            'Амфитеатр правая сторона': 'Амфитеатр, правая сторона',
            'Амфитеатр левая сторона': 'Амфитеатр, левая сторона',
            'Амфитеатр-середина': 'Амфитеатр, середина',
            'Партер середина': 'Партер, середина',
            'Партер левая сторона': 'Партер, левая сторона',
            'Партер правая сторона': 'Партер, правая сторона',
            'Малый зал ГКД': 'Партер',
            '6-й этаж': 'Партер'
        }
        ref_dict = {'Малый зал ГКД': 'Партер',
                    '6-й этаж': 'Партер'}
        if 'кремлёвский дворец' in self.venue.lower():
            ref_dict = kreml_reformat_dict

        for sector in a_sectors:
            if 'мегаспорт' in self.venue.lower():
                if 'С' in sector['name'].split()[1]:
                    sector['name'] = sector['name'].split()[0] + ' ' + sector['name'].split()[1].replace('С', 'C')
                elif 'В' in sector['name'].split()[1]:
                    sector['name'] = sector['name'].replace('В', 'B')
                elif 'Ложа' in sector['name']:
                    sector['name'] = sector['name'].replace('№ ', '')
            else:
                sector['name'] = ref_dict.get(sector['name'], sector['name'])

    async def parse_seats(self, soup):
        total_sector = []

        all_sectors = soup.select('#sectors_list li')
        if len(all_sectors) == 0:
            guid = self.url.split('=')[-1]
            url = f'https://icetickets.ru/lib/custom_ajax.php?oper=get_sectors&guid={guid}'
            soup = await self.request_parser(url)
            all_sectors = soup.select('li')

        for sector in all_sectors:
            sector_name_and_data_to_requests = sector.find('span')
            sector_name = sector_name_and_data_to_requests.text.strip()
            data_to_requests = sector_name_and_data_to_requests.get('onclick')

            url = 'https://icetickets.ru/lib/custom_ajax.php'
            data_to_requests = double_split(data_to_requests, ";readtickets('", ',)"').replace("'", '').split(',')
            aid = data_to_requests[0]
            sid = data_to_requests[1]
            data = {
                'oper': 'get_tickets',
                'aid': aid,
                'sid': sid,
                's': '1'
            }
            soup_for_sector = await self.get_data(url, data)

            all_place_in_sector = {}
            all_free_seats = soup_for_sector.find_all('div', class_='ticlist')
            for free_seats in all_free_seats:
                seat_and_row = free_seats.find('div', class_='name').text.strip()
                row = double_split(seat_and_row, 'р.', ' м.')
                seat = seat_and_row[seat_and_row.index('м. ')+3:]

                price = int(free_seats.find('nobr').text.strip().split()[0])

                all_place_in_sector[(row, seat,)] = price

            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": all_place_in_sector
                }
            )

        return total_sector

    async def get_data(self, url, data):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'content-length': '102',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://icetickets.ru',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = await self.session.post(url, data=data, headers=headers, ssl=self.ssl_context)
        return BeautifulSoup(r.text, 'lxml')

    async def second_requests_parser(self, url):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = await self.session.get(url, headers=headers, ssl=self.ssl_context)
        return BeautifulSoup(r.text, 'lxml')

    async def request_parser(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers, ssl=self.ssl_context)
        return BeautifulSoup(r.text, 'lxml')

    async def get_seats(self):
        soup = await self.request_parser(url=self.url)

        a_events = await self.parse_seats(soup)

        return a_events

    async def body(self):
        all_sectors = await self.get_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            #self.info(sector)
            self.register_sector(sector['name'], sector['tickets'])