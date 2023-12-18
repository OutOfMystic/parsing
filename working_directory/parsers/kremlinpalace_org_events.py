import datetime
from typing import Optional, Union

from bs4 import BeautifulSoup

from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split


class KremlInPalace(EventParser):
    proxy_check = SpecialConditions(url='https://kremlinpalace.org/')

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://kremlinpalace.org/'
        self.user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                           ' AppleWebKit/537.36 (KHTML, like Gecko)'
                           ' Chrome/111.0.0.0 Safari/537.36')

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []

        def parse_items():
            items_list = soup.find_all('article', class_='event')
            for item in items_list:
                title = item.find('h4').find('a').text

                date, time = item.find_all('time')
                _, day, month, year = date.text.split()
                month = month[:3].title()
                normal_date = day + ' ' + month + ' ' + year + ' ' + time.text

                href = item.find('a', class_='button').get('href')
                if (href is None or href == '' or href == '#ticketOnlyOffice' 
                        or'icetickets' in href):
                    continue

                a_events.append([title, href, normal_date])

        parse_items()
        list_page = soup.select('ul.pagination li')
        if len(list_page) == 0:
            return None
        page_number = 2
        for page in range(len(list_page) - 2):
            url = f'https://kremlinpalace.org/?page={page_number}#events'
            soup = self.request_for_href(url)
            parse_items()
            page_number += 1

        return a_events

    def request_for_href(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
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
        r = self.session.get(url, headers=headers)

        return BeautifulSoup(r.text, "lxml")

    def request_to_soup(self):
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
        r = self.session.get(self.url, headers=headers)

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

    def get_events(self):
        soup = self._set_cookie_for_bypassing_protection()
        if soup is None:
            soup = self.request_to_soup()

        a_events = self.parse_events(soup)

        return a_events

    def body(self):
        count_error = 0
        for i in range(10):
            a_events = self.get_events()
            if a_events is None:
                if count_error >= 5:
                    self.proxy = self.controller.proxy_hub.get(self.proxy_check)
                    self.session = ProxySession(self)
                count_error += 1
            else:
                break
        else:
            raise Exception('--- kremlinpalace event parser not get list events ---')

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])
