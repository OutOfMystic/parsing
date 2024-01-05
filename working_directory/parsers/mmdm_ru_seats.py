import json
import time
from pathlib import Path
from typing import NamedTuple

from requests.exceptions import ProxyError, JSONDecodeError

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class Mmdm(SeatsParser):
    event = 'mmdm.ru'
    url_filter = lambda url: 'www.mmdm.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.csrf_token: str = 'tkiCzbt7mj2WVEvZW33VNFgonoVtSdzyyUiWQLu1FbAcaME4Myq1Kpc875pTjhZg'
        self._ddg2_: str = 'k3wy1Spd29SBOfv7'
        self.ddg2: str = 'k3wy1Spd29SBOfv7'
        self.user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                               'Chrome/110.0.0.0 YaBrowser/23.3.2.806 Yowser/2.5 Safari/537.36'

    def before_body(self):
        self.session = ProxySession(self)
        self.session.cookies.set('__ddgid_', 'yuEsc7A7O3KpYzHw', domain='www.mmdm.ru')
        self.session.cookies.set('__ddg1_', 'vm5OlV40vtdtUMkebHon', domain='.mmdm.ru')
        self.session.cookies.set('__ddg2_', 'k3wy1Spd29SBOfv7', domain='.mmdm.ru')
        self.session.cookies.set('ddg2', 'k3wy1Spd29SBOfv7', domain='.mmdm.ru')
        self.session.cookies.set('__ddg5_', 'DlNIMY8IBLJvt2Hh', domain='.mmdm.ru')
        self.session.cookies.set('__ddgmark_', 'u3MhHHdpAbRxnr4x', domain='www.mmdm.ru')
        self.session.cookies.set('sessionid', self.session_id, domain='www.mmdm.ru')
        self.session.cookies.set(
            'csrftoken', 'tkiCzbt7mj2WVEvZW33VNFgonoVtSdzyyUiWQLu1FbAcaME4Myq1Kpc875pTjhZg', domain='www.mmdm.ru'
        )
        self.session.cookies.set('_ym_d', '1682084959', domain='.mmdm.ru')
        self.session.cookies.set('_ym_uid', '1681998721619246323', domain='.mmdm.ru')
        self.session.cookies.set('_ym_isad', '1', domain='.mmdm.ru')
        self.session.cookies.set('_ym_visorc', 'w', domain='.mmdm.ru')

    def _reformat(self, sector_name: str) -> str:
        if 'Светлановский зал' in self.scene:
            if 'Балкон правая' in sector_name:
                sector_name = 'Балкон, правая сторона'
            elif 'Балкон левая' in sector_name:
                sector_name = 'Балкон, левая сторона'
            elif 'Балкон середина' in sector_name:
                sector_name = 'Балкон, середина 5'
            elif 'Амфитеатр правая сторона' in sector_name:
                sector_name = 'Амфитеатр, правая сторона'
            elif 'Амфитеатр левая сторона' in sector_name:
                sector_name = 'Амфитеатр, левая сторона'
            elif 'Амфитеатр середина' in sector_name:
                sector_name = 'Амфитеатр, середина 3'
            elif 'Бельэтаж правая ст' in sector_name:
                sector_name = 'Бельэтаж, правая сторона'
            elif 'Бельэтаж левая ст' in sector_name:
                sector_name = 'Бельэтаж, левая сторона'
        elif 'Театральный зал' in self.scene:
            if 'Амфитеатр с ограниченным обзором' in sector_name:
                sector_name = 'Амфитеатр (с ограниченным обзором)'
            elif 'с ограниченным обзором' in sector_name:
                sector_name = sector_name.replace('с ограниченным обзором', '(с ограниченным обзором)')
        elif 'камерный' in self.scene.lower():
            sector_name = sector_name.replace(' неудобные места', '')
            if sector_name == 'Партер с ограниченным обзором':
                sector_name = 'Партер (с ограниченным обзором)'

        return sector_name

    def _parse_seats(self) -> OutputData:
        json_data = self._request_to_json_data()

        places_is_not_busy = self._get_place_from_json(json_data)

        output_data = self._get_output_data(places_is_not_busy)

        return output_data

    def _get_output_data(self, places_is_not_busy: list) -> OutputData:
        sectors_data = {}
        for place in places_is_not_busy:

            place_sector, place_row, place_seat, place_price = self._get_place_data(place)

            if sectors_data.get(place_sector):
                old_data: dict[tuple[str, str], int] = sectors_data[place_sector]
                old_data[(place_row, place_seat)] = place_price
                sectors_data[place_sector] = old_data
            else:
                sectors_data[place_sector] = {(place_row, place_seat): place_price}

        for sector_name, tickets in sectors_data.items():
            yield OutputData(sector_name=sector_name, tickets=tickets)

    def _get_place_data(self, place: dict) -> tuple[str, str, str, int]:
        place_sector = place['name_sec']
        place_row = place['row']
        place_seat = place['seat']
        place_price = place['Price']
        place_price = int(place_price.split('.')[0])

        place_sector = self._reformat(place_sector)

        return place_sector, place_row, place_seat, place_price

    def _get_place_from_json(self, json_data: json) -> list:
        places_is_not_busy = json_data['EvailPlaceList']
        return places_is_not_busy

    def _request_to_json_data(self, count_error_bypassing: int = 0) -> json:
        if count_error_bypassing == 10:
            raise ProxyError(f'------ bypassing protection ddos-guard is failed {count_error_bypassing = } --------')
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://mdt-dodin.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent
        }
        id_event = self.url.split('/')[-2]
        url = f'https://www.mmdm.ru/api/places/?nombilkn={id_event}&cmd=get_hall_and_places'
        r = self.session.get(url, headers=headers)

        if r.status_code == 200:
            try:
                return r.json()
            except JSONDecodeError:
                return self._request_to_json_data(count_error_bypassing=count_error_bypassing+1)
        elif r.status_code == 403:
            self.bypassing_protection(count_error_bypassing)
            return self._request_to_json_data(count_error_bypassing=count_error_bypassing+1)
        else:
            raise ProxyError(f'{self.url = } status_code {r.status_code = }')

    def bypassing_protection(self, count_error_bypassing: int) -> None:
        delay_to_requests = 0
        if count_error_bypassing > 6:
            delay_to_requests = 1.5
        elif count_error_bypassing > 3:
            delay_to_requests = 1

        requests_to_js_1_status, requests_to_js_2_status = self.requests_to_js_ddos_guard(delay_to_requests)
        requests_to_image_1_status, requests_to_image_2_status = self.requests_to_image_ddos_guard(delay_to_requests)
        requests_to_send_data_status = self.requests_post_to_send_device_data(delay_to_requests)

        if requests_to_js_1_status != 200 or requests_to_js_2_status != 200 or requests_to_image_1_status != 200 or \
                requests_to_image_2_status != 200 or requests_to_send_data_status != 200:
            self.error('---------- seats_parser bypassing protection ddos-guard is failed ----------')

    def requests_to_js_ddos_guard(self, delay_to_requests: int) -> tuple[int, int]:
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
        time.sleep(1 + delay_to_requests)
        url = 'https://www.mmdm.ru/.well-known/ddos-guard/check?context=free_splash'
        r = self.session.get(url, headers=headers)
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
        time.sleep(1 + delay_to_requests)
        url = 'https://check.ddos-guard.net/check.js'
        r = self.session.get(url, headers=headers)
        requests_to_js_2_status = r.status_code

        return requests_to_js_1_status, requests_to_js_2_status

    def requests_to_image_ddos_guard(self, delay_to_requests: int) -> tuple[int, int]:
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
        time.sleep(1 + delay_to_requests)
        url = f'https://check.ddos-guard.net/set/id/{self.session.cookies.get("ddg2")}'
        r = self.session.get(url, headers=headers)
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
        time.sleep(1 + delay_to_requests)
        url = f'https://www.mmdm.ru/.well-known/ddos-guard/id/{self.session.cookies.get("__ddg2_")}'
        r = self.session.get(url, headers=headers)
        requests_to_image_2_status = r.status_code

        return requests_to_image_1_status, requests_to_image_2_status

    def requests_post_to_send_device_data(self, delay_to_requests: int) -> int:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-length': '44134',
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

        time.sleep(1 + delay_to_requests)
        url = 'https://www.mmdm.ru/.well-known/ddos-guard/mark/'
        r = self.session.post(url, headers=headers, data=data)
        requests_to_send_data_status = r.status_code

        return requests_to_send_data_status

    def body(self) -> None:
        skip_urls = [
            'https://www.mmdm.ru/reserve-ticket/7003/',
            # 'https://www.mmdm.ru/reserve-ticket/7322/',
        ]
        if self.url in skip_urls:
            return
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
