import random
import re
import time
import json

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession



class HockeySpartak(AsyncSeatsParser):
    event = 'moscow.qtickets.events'
    url_filter = lambda url: 'qtickets.events' in url and 'spartak' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.id = re.search(r'\d+', self.url)[0]

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def double_split(source, lstr, rstr, x=1, n=0):
        # Возвращает n-ый эелемент
        SplPage = source.split(lstr, x)[n + 1]
        SplSplPage = SplPage.split(rstr)[0]
        return SplSplPage

    async def load_event(self, url, session_key):
        #url = 'https://hk-spartak.qtickets.ru/event/80349'
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        data = {
            'event_id': self.id,
            'widget_session': session_key
        }
        r = await self.session.post(url, headers=headers, data=data)
        soup, text = BeautifulSoup(r.text, 'lxml'), r.text
        return soup, text
    
    def get_all_seats_url(self, soup):
        find_src = soup.find('script', attrs={'src': re.compile(r'.*/storage/temp/bundles/.*')})
        url_js = find_src.get('src')
        return url_js
    
    def get_busy_seats_url(self, text):
        url_seats = self.double_split(text, '"seats_url":"\/widget\/', '",')
        url_seats = f'https://hk-spartak.qtickets.ru/widget/{url_seats}'
        return url_seats
    
    @staticmethod
    def hard_work(text):
        '''dont try understand wht happend here!!!'''
        text = "{'" + text.replace('null', 'None') + '}'
        text = re.sub(r'\,(?=\w+\=)', ",'", text)
        text = text.replace('=', "':")
        text = text.replace('true', "True")
        text = text.replace('false', "False").replace('as', 'ass')
        return text
    
    @staticmethod
    def make_list_from_string(VARIABLES, seats_str):
        for key, value in VARIABLES.items():
            exec(f'{key} = "{value}"')
        seats_list = eval(seats_str)
        return seats_list

    async def get_all_seats(self, url):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'script',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        #exampleUrl1 = 'https://cdn.qtickets.tech/storage/temp/bundles/375268/3cda7f82b87ea5e3045e9b89ea573906-a8d376fc1f76fa376c5a8bccd41763e1.ru.public.js?cache_lock=on'
        r1 = await self.session.get(url, headers=headers, verify=False)
        x = len(re.findall(r'function\(cfg\)', r1.text)) #столько есть отдельных массивов с одинаковыми переменными

        text1 = self.double_split(r1.text, '(function(cfg){var ', '\n', x=1, n=0)
        VARIABLES1 = eval(self.hard_work(text1))
        seats1_str = self.double_split(r1.text, 'var seats=', ';', 1, 0 ).replace('as', 'ass')
        seats1_str = f"[{seats1_str[1:-1].replace('[', '(').replace(']', ')')}]"
        seats1_list = self.make_list_from_string(VARIABLES1, seats1_str)
        if x > 1:
            text2 = self.double_split(r1.text, '(function(cfg){var ', '\n', x=2, n=1)
            VARIABLES2 = eval(self.hard_work(text2))
            seats2_str = self.double_split(r1.text, 'var seats=', ';', 2, 1 ).replace('as', 'ass')
            seats2_str = f"[{seats2_str[1:-1].replace('[', '(').replace(']', ')')}]"
            seats2_list = self.make_list_from_string(VARIABLES2, seats2_str)
            seats1_list += seats2_list
        return seats1_list
    
    async def get_busy_seats(self, url):
        headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'ru,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': self.url,
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': self.user_agent,
        'x-requested-with': 'XMLHttpRequest'
        }
        #ExampleUrl2 = 'https://hk-spartak.qtickets.ru/widget/seats?show_id=375268&widget_session=0000000000000000000000000000000000000000&salt=ca8120baca0962c1134829ed32577af9&cache_lock=on&hash=d3f3ab6c99215101748c464134055421'
        r2 = await self.session.get(url, headers=headers, verify_ssl=False)
        # with open('TEST3.json', 'w', encoding='utf-8') as file:
        #     json.dump(r2.json(), file, indent=4, ensure_ascii=False) 
        seats = r2.json()
        all_places_is_busy = set()
        places_is_busy = seats['ordered_seats']
        for place in places_is_busy.keys():
            sector_name, row_and_seat = place.split('-')
            row, seat = row_and_seat.split(';')
            data_about_place = (sector_name, row, seat)
            all_places_is_busy.add(data_about_place)

        disabled_seats = seats.get('multiprice_disabled_seats', None) #wtf
        if isinstance(disabled_seats, dict):
            for sector, rows_and_seats in disabled_seats.items():
                for row, seats in rows_and_seats.items():
                    for seat, is_disabled in seats.items():
                        if isinstance(is_disabled, list) and is_disabled[0] == 0:
                            all_places_is_busy.add((str(sector), str(row), str(seat)))   

        return all_places_is_busy

    def main_work(self, all_seats, bad_seats):
        # with open('TEST2.json', 'w', encoding='utf-8') as file: 
        #     json.dump(sorted(bad_seats, key=lambda s: (s[0], int(s[1]), int(s[2]))), file, indent=4, ensure_ascii=False)
        a_seats = {} 
        for place in all_seats.keys():
            place_info = all_seats[place]
            if len(place_info) == 9:
                '''place_info = ['A1', 20, 3, 'True', '#009589', '0', '[None, 1552570, None]', 4294, 3919]
расшифровка  place_info ["zone_id", "place", "row", "mp_disabled", "mp_color", "mp_price", "mp_price_id", "x", "y"]'''
                if place_info[5] == '0' or place in bad_seats:
                    continue
                sector_name, row, seat = place
                price = re.search(r'\d+',place_info[5])[0]

            elif len(place_info) == 10:
                '''place_info = ['D3', 1, 2, 1, 'True', '#009589', '0', '[None, 1552559, 1552554]', 5658, 3303]
            ["zone_id", "place", "row", "has_panorama", "mp_disabled", "mp_color", "mp_price", "mp_price_id", "x", "y"]'''
                if place_info[6] == '0' or place in bad_seats:
                    continue
                sector_name, row, seat = place
                price = re.search(r'\d+',place_info[6])[0]

            a_seats.setdefault(sector_name, {}).update({
                                                    (row, seat): int(price)
                                                    })
        return a_seats
    
    @staticmethod
    def sector_reformat(sector):
        if re.search(r'^[ABCD]', sector):
            return f"Сектор {sector}"
        elif sector.startswith('L'):
            return f"Ложа {sector[1:]}"
        elif sector.startswith('VIP'):
            num = re.search(r'\d+', sector)[0]
            return f"VIP {num}"
        return sector
            

    async def body(self) -> None:
        widget_session_keys = ['eLdgrITSBV3mAwGoJSD8MlBUIzM5rf0n4hyoJTHz', '0bZrs4wOy54onLqK8syqUEFzJ84Ape8TrT8e0fna',
                               'XtlsP70VIO5KsEzAFP34DyL7NEsWuithSGa95WUf']
        url = f'https://hk-spartak.qtickets.ru/event/{self.id}'

        soup, text = await self.load_event(url, random.choice(widget_session_keys))
        url_seats = self.get_all_seats_url(soup)
        all_seats = await self.get_all_seats(url_seats)
        all_seats = { (i[0],str(i[2]),str(i[1])):i  for i in all_seats }
        #all_seats1 = { f"{i[0]},{str(i[2])},{str(i[1])}":i  for i in all_seats }
        # with open('TEST1.json', 'w', encoding='utf-8') as file:
        #     json.dump(all_seats1, file, indent=4, ensure_ascii=False)
        url_bad_seats = self.get_busy_seats_url(text)
        bad_seats = await self.get_busy_seats(url_bad_seats)

        avalibale_seats = self.main_work(all_seats, bad_seats)

        for sector, tickets in avalibale_seats.items():
            sector = self.sector_reformat(sector)
            self.register_sector(sector, tickets)
        #self.check_sectors()
        