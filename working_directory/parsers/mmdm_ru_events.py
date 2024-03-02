import asyncio
from http.cookies import SimpleCookie
from typing import NamedTuple, Optional, Union
from pathlib import Path
import json
import asyncio

from requests.exceptions import ProxyError
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession, add_cookie_to_cookies


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    scene: str


class Mmdm(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://www.mmdm.ru/afisha/'
        self.user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                               'Chrome/110.0.0.0 YaBrowser/23.3.2.806 Yowser/2.5 Safari/537.36'

    async def before_body(self):
        self.session = AsyncProxySession(self)

        to_cookies = [
            ('__ddgid_', 'yuEsc7A7O3KpYzHw', 'www.mmdm.ru',),
            ('__ddg1_', 'vm5OlV40vtdtUMkebHon', '.mmdm.ru',),
            ('__ddg2_', 'k3wy1Spd29SBOfv7', '.mmdm.ru',),
            ('ddg2', 'k3wy1Spd29SBOfv7', '.mmdm.ru',),
            ('__ddg5_', 'DlNIMY8IBLJvt2Hh', '.mmdm.ru',),
            ('__ddgmark_', 'u3MhHHdpAbRxnr4x', 'www.mmdm.ru',),
            ('csrftoken', 'tkiCzbt7mj2WVEvZW33VNFgonoVtSdzyyUiWQLu1FbAcaME4Myq1Kpc875pTjhZg', 'www.mmdm.ru',),
            ('_ym_d', '1682084959', '.mmdm.ru',),
            ('_ym_uid', '1681998721619246323', '.mmdm.ru',),
            ('_ym_isad', '1', '.mmdm.ru',),
            ('_ym_visorc', 'w', '.mmdm.ru',),
            # ('sessionid', 'ydoqrzaigouasn5pmwzlq7liaztdg2n4', 'www.mmdm.ru',),
        ]

        cookies = SimpleCookie()
        for cookie in to_cookies:
            add_cookie_to_cookies(cookies, *cookie)
        self.session.cookies.update_cookies(cookies)

    async def _get_session_id(self) -> None:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://www.mmdm.ru/afisha/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        url = 'https://www.mmdm.ru/api/cart/'
        r = await self.session.get(url, headers=headers)
        self.session_id = self.session.cookies.filter_cookies(url)['sessionid']

    async def _parse_events(self):
        soup = await self._requests_to_events()

        events = self._get_events_from_soup(soup)

        return await self._parse_events_from_soup(events)

    async def _parse_events_from_soup(self, events):
        collected = []
        link_to_get_next_events = True
        count_request_to_axaj = 2

        while len(events) > 0:
            for event in events:
                output_data = self._parse_data_from_event(event)
                if output_data is not None:
                    collected.append(output_data)

            if link_to_get_next_events is False:
                break
            json_data = await self._requests_to_axaj_events(count_request_to_axaj)
            events, link_to_get_next_events = self._get_events_from_json(json_data)
            count_request_to_axaj += 1
        return collected

    def _parse_data_from_event(self, event: BeautifulSoup) -> Optional[Union[OutputEvent, None]]:
        title = event.find('a', class_='egi_title').text.strip().replace("'", '"')

        date = event.find('div', class_='egi_datetime').text.strip()
        date = date.split()
        date[1] = date[1].title()[:3]
        if len(date) > 4:
            del date[3]
        normal_date = ' '.join(date)

        href = event.find('a', class_='egi_btn')
        if href is None:
            return None
        href = href.get('href')
        if href == 'javascript:void(0);':
            return None
        href = 'https://www.mmdm.ru' + href

        scheme = event.find('div', class_='egi_hall').text.strip()

        return OutputEvent(title=title, href=href, date=normal_date, scene=scheme)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> list:
        events = soup.select('div.event_grid_item.splide__slide div.egi_bottom')
        return events

    def _get_events_from_json(self, json_data: json) -> tuple[list, bool]:
        link_to_get_next_events = json_data.get('has_next')
        html_text_in_json = json_data.get('html')
        soup = BeautifulSoup(html_text_in_json, 'lxml')
        return self._get_events_from_soup(soup), link_to_get_next_events

    async def _requests_to_axaj_events(self, count_request_to_axaj: int, count_error_bypassing: int = 0) -> json:
        if count_error_bypassing == 10:
            raise ProxyError(f'------ bypassing protection ddos-guard is failed {count_error_bypassing = } --------')
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://www.mmdm.ru/afisha/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        url = f'https://www.mmdm.ru/events_ajax/?p_number={count_request_to_axaj}'
        r = await self.session.get(url, headers=headers)

        if r.status_code == 200:
            return r.json()
        elif r.status_code == 403:
            await self.bypassing_protection(count_error_bypassing)
            return await self._requests_to_axaj_events(count_request_to_axaj, count_error_bypassing=count_error_bypassing+1)
        else:
            raise ProxyError(f'{self.url = } status_code {r.status_code = }')

    async def _requests_to_events(self, count_error_bypassing: int = 0) -> BeautifulSoup:
        if count_error_bypassing == 10:
            raise ProxyError(f'------ bypassing protection ddos-guard is failed {count_error_bypassing = } --------')
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://www.mmdm.ru/afisha/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
        }
        r = await self.session.get(self.url, headers=headers)

        if r.status_code == 200:
            return BeautifulSoup(r.text, 'lxml')
        elif r.status_code == 403:
            await self.bypassing_protection(count_error_bypassing)
            return await self._requests_to_events(count_error_bypassing=count_error_bypassing+1)
        else:
            raise ProxyError(f'{self.url = } status_code {r.status_code = }')

    async def bypassing_protection(self, count_error_bypassing: int) -> None:
        delay_to_requests = 0
        if count_error_bypassing > 6:
            delay_to_requests = 1.5
        elif count_error_bypassing > 3:
            delay_to_requests = 1

        requests_to_js_1_status, requests_to_js_2_status = await self.requests_to_js_ddos_guard(delay_to_requests)
        requests_to_image_1_status, requests_to_image_2_status = await self.requests_to_image_ddos_guard(delay_to_requests)
        requests_to_send_data_status = await self.requests_post_to_send_device_data(delay_to_requests)

        if requests_to_js_1_status != 200 or requests_to_js_2_status != 200 or requests_to_image_1_status != 200 or \
                requests_to_image_2_status != 200 or requests_to_send_data_status != 200:
            self.error('---------- event_parser bypassing protection ddos-guard is failed ----------')

    async def requests_to_js_ddos_guard(self, delay_to_requests: int) -> tuple[int, int]:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'referer': 'https://www.mmdm.ru/afisha/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'script',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
        }
        await asyncio.sleep(1 + delay_to_requests)
        url = 'https://www.mmdm.ru/.well-known/ddos-guard/check?context=free_splash'
        r = await self.session.get(url, headers=headers)
        requests_to_js_1_status = r.status_code

        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'referer': 'https://www.mmdm.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'script',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent,
        }
        await asyncio.sleep(1 + delay_to_requests)
        url = 'https://check.ddos-guard.net/check.js'
        r = await self.session.get(url, headers=headers)
        requests_to_js_2_status = r.status_code

        return requests_to_js_1_status, requests_to_js_2_status

    async def requests_to_image_ddos_guard(self, delay_to_requests: int) -> tuple[int, int]:
        headers = {
            'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'referer': 'https://www.mmdm.ru/afisha/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
        }
        await asyncio.sleep(1 + delay_to_requests)

        cookies = self.session.cookies.filter_cookies('https://check.ddos-guard.net/check.js')
        url = f'https://check.ddos-guard.net/set/id/{cookies["ddg2"]}'
        r = await self.session.get(url, headers=headers)
        requests_to_image_1_status = r.status_code

        headers = {
            'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'referer': 'https://www.mmdm.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'image',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent,
        }
        await asyncio.sleep(1 + delay_to_requests)
        url = f'https://www.mmdm.ru/.well-known/ddos-guard/id/{cookies["ddg2"]}'
        r = await self.session.get(url, headers=headers)
        requests_to_image_2_status = r.status_code

        return requests_to_image_1_status, requests_to_image_2_status

    async def requests_post_to_send_device_data(self, delay_to_requests: int) -> int:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'text/plain;charset=UTF-8',
            'origin': 'https://www.mmdm.ru',
            'pragma': 'no-cache',
            'referer': 'https://www.mmdm.ru/',
            'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
        }
        BASE_DIR = Path(__file__).resolve().parent.parent
        file = BASE_DIR.joinpath('data.txt')
        with open(file, 'r', encoding='utf-8') as f:
            data = f.read()

        await asyncio.sleep(1 + delay_to_requests)
        url = 'https://www.mmdm.ru/.well-known/ddos-guard/mark/'
        r = await self.session.post(url, headers=headers, data=data)
        requests_to_send_data_status = r.status_code

        return requests_to_send_data_status

    async def body(self) -> None:
        await self._get_session_id()
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date, scene=event.scene, session_id=self.session_id)
