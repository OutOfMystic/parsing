import datetime
from typing import Optional, Union

from bs4 import BeautifulSoup

from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split


class KremlInPalace(SeatsParser):
    event = 'kremlinpalace.org'
    url_filter = lambda url: 'kremlinpalace.org' in url
    proxy_check = SpecialConditions(url='https://kremlinpalace.org/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.authorization = 'Bearer pNJDWUGZMvW8HO7SiOqka07gJJIbZcB7tYKBdJluSpmabr8Ccpd7cWkNxSIA'
        self.id_event = None
        self.user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                           ' AppleWebKit/537.36 (KHTML, like Gecko)'
                           ' Chrome/111.0.0.0 Safari/537.36')

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, a_sectors):
        scheme_main = {
            'Партер правая сторона': 'Партер, правая сторона',
            'Партер левая сторона': 'Партер, левая сторона',
            'Партер середина': 'Партер, середина',
            'Ложа балкона правая': 'Ложа балкона, правая сторона',
            'Ложа балкона левая': 'Ложа балкона, левая сторона',
            'Балкон-середина': 'Балкон, середина',
            'Балкон правая сторона': 'Балкон, правая сторона',
            'Балкон прав.ст. откидное': 'Балкон, правая сторона (откидные)',
            'Балкон левая сторона': 'Балкон, левая сторона',
            'Балкон лев.ст. откидное': 'Балкон, левая сторона (откидные)',
            'Амфитеатр-середина': 'Амфитеатр, середина',
            'Амфитеатр правая сторона': 'Амфитеатр, правая сторона',
            'Амфитеатр левая сторона': 'Амфитеатр, левая сторона',
            'Сектор А': 'Сектор А',
            'Сектор В': 'Сектор B',
            'Сектор С': 'Сектор C',
            'Малый зал ГКД': 'Партер',
            '6-й этаж': 'Партер'

        }

        for sector in a_sectors:
            sector['name'] = scheme_main.get(sector['name'], sector['name'])

    def parse_seats(self, json_data):
        total_sector = []

        all_data = []
        all_place = json_data.get('data')
        if all_place is None:
            return []
        for place in all_place:
            color = place.get('color')
            sector_name = place.get('section_name')
            row = place.get('row')
            seat = place.get('place')
            price = place.get('price')
            all_data.append({color: (sector_name, (row, seat, price))})

        url = f'https://gw-ts.kremlinpalace.org/api/v1/sections?event_id={self.id_event}'
        get_all_sectors = self.requests_to_json(url)

        all_real_color = set()
        all_sector = get_all_sectors.get('data')
        for sector in all_sector:
            color_in_sector = sector.get('legendTariffs')
            for color in color_in_sector:
                all_real_color.add(color.get('color'))

        final_data = {}
        for place in all_data:
            for color, data in place.items():
                if color in all_real_color:
                    sector_name = data[0]
                    row, seat, price = data[1]
                    real_place_in_sector = {(row, seat,): int(price)}
                    if final_data.get(sector_name):
                        this_sector = final_data[sector_name]
                        this_sector[(row, seat,)] = int(price)
                    else:
                        final_data[sector_name] = real_place_in_sector

        for sector_name, total_seats_row_prices in final_data.items():
            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def requests_to_json(self, url):
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'authorization': self.authorization,
            'connection': 'keep-alive',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'host': 'gw-ts.kremlinpalace.org',
            'origin': 'https://kremlinpalace.org',
            'referer': 'https://kremlinpalace.org/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = self.session.get(url, headers=headers)
        return r.json()

    def request_to_id(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://kremlinpalace.org/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def _get_js_code_and__js_p__from_main_site(self) -> tuple[str, str, str]:
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
        r = self.session.get(self.url, headers=headers)
        js_code = double_split(r.text, '<script>', '</script>')
        return js_code, self.session.cookies.get('__js_p_'), r.text

    def _generate_jhash_from_js_code(self, js_code: str, var_code: int) -> int:
        function_get_jhash = double_split(js_code, 'function get_jhash(b) {', ';}')

        var_k = 0
        var_x = int(double_split(function_get_jhash, 'var x = ', ';'))
        var_range = int(double_split(function_get_jhash, '; i < ', '; i++'))
        for i in range(var_range):
            var_x = ((var_x + var_code) ^ (var_x + (var_x % 3) + (var_x % 17) + var_code) ^ i) % 16776960
            if var_x % 117 == 0:
                var_k = (var_k + 1) % 1111
        return var_k

    def _processing_js_code_to_generate_cookie(self, js_code: str, cookie__js_p_: str) -> None:
        cookie__js_p__split = cookie__js_p_.split(',')
        index_code = double_split(js_code, 'var code = get_param("__js_p_", "int", ', ');')
        var_code = int(cookie__js_p__split[int(index_code)])

        index_age = double_split(js_code, 'var age = get_param("__js_p_", "int", ', ');')
        var_age = cookie__js_p__split[int(index_age)]
        expires = datetime.datetime.timestamp(datetime.datetime.now()) + int(var_age)
        expires = int(expires)

        var_jhash = self._generate_jhash_from_js_code(js_code, var_code)
        self.session.cookies.set(
            '__jhash_',
            str(var_jhash),
            expires=expires,
            domain='kremlinpalace.org',
            path='/',
            secure='False'
        )
        self.session.cookies.set(
            '__jua_',
            'Mozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F111.0.0.0%20Safari%2F537.36',
            expires=expires,
            domain='kremlinpalace.org',
            path='/',
            secure='False'
        )

    def _set_cookie_for_bypassing_protection(self) -> Optional[Union[None, BeautifulSoup]]:
        js_code, cookie__js_p_, r_text = self._get_js_code_and__js_p__from_main_site()
        if cookie__js_p_ is None or 'var code = get_param("__js_p_", "int", 0);' not in js_code:
            return BeautifulSoup(r_text, 'lxml')
        self._processing_js_code_to_generate_cookie(js_code, cookie__js_p_)
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://kremlinpalace.org/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        self.session.get(self.url, headers=headers)

    def get_seats(self):
        soup = self._set_cookie_for_bypassing_protection()
        if soup is None:
            soup = self.request_to_id(self.url)
        self.id_event = soup.find('div', attrs={'id': 'app'}).get('data-performance')

        url = f'https://gw-ts.kremlinpalace.org/api/v1/places?event_id={self.id_event}'
        json_data = self.requests_to_json(url)

        all_sectors = self.parse_seats(json_data)

        return all_sectors

    def body(self):
        for count_error in range(10):
            try:
                all_sectors = self.get_seats()
                break
            except AttributeError as error:
                if count_error == 9:
                    raise AttributeError(error)
                if count_error >= 5:
                    self.proxy = self.controller.proxy_hub.get(self.proxy_check)
                    self.session = ProxySession(self)
                continue
        else:
            all_sectors = {}
            self.error('--- seats_parser kremlepalace bypassing protection is failed ---')

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
