import json
import time
from typing import NamedTuple

from requests.exceptions import ProxyError
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from parse_module.coroutines import AsyncSeatsParser
from parse_module.drivers.proxelenium import ProxyWebDriver
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils.parse_utils import double_split


class OutputData(NamedTuple):
    sector_name: str
    tickets: dict[tuple[str, str], int]


class TktGe(AsyncSeatsParser):
    event = 'tkt.ge'
    url_filter = lambda url: 'tkt.ge' in url
    proxy_check = NormalConditions()

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = '355735'
        self.url = f'https://tkt.ge/api/v2/shows/get?itemId={self.event_id}&category=Event&previewKey=&queueItTkn=e_brunomars~q_7f49ffa3-14cc-4b2a-9799-12578a5ecac5~ts_1689595300~ce_true~rt_safetynet~h_02039ce52a856df442b56c3583793dafcf6a856d67bd8c428ae7eea4be419abe&urlWithoutQueueITTkn=https%3A%2F%2Ftkt.ge%2Fevent%2F355735&api_key=7d8d34d1-e9af-4897-9f0f-5c36c179be77'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _reformat(self, sector_name: str) -> str:
        return sector_name

    def _get_driver_with_cookies(self) -> json:
        driver = ProxyWebDriver(proxy=self.proxy)

        try:
            driver.get('https://tkt.ge/event/355735/bruno-mars')
            time.sleep(5)
            yield driver
            driver.quit()
        except TimeoutException as e:
            raise ProxyError(e)

    def _get_json_data_from_selenium(self, driver: ProxyWebDriver, url: str) -> json:
        driver.get(url=url)
        driver_json = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "pre"))
        ).text
        return json.loads(driver_json)

    def _parse_seats(self) -> OutputData:
        generator_driver = self._get_driver_with_cookies()
        driver = next(generator_driver)

        json_data = self._get_json_data_from_selenium(driver, self.url)
        # json_data = self._requests_to_json_data_to_price()
        price_data = self._get_price_data_from_json_data(json_data)

        url = f'https://tkt.ge/api/Events/Map?mapId=342778&orderKey=&api_key=7d8d34d1-e9af-4897-9f0f-5c36c179be77'
        json_data = self._get_json_data_from_selenium(driver, url)
        # json_data = self._request_to_get_all_sectors()
        all_sectors = self._get_all_sectors_from_json_data(json_data)

        output_data = self._get_output_data(all_sectors, price_data, driver)

        try:
            next(generator_driver)
        except StopIteration:
            pass
        return output_data

    def _get_output_data(self, all_sectors: dict[str, int], price_data: dict[int, int], driver) -> OutputData:
        output_data = []
        for sector_name, sector_id in all_sectors.items():
            tickets = {}

            url = f'https://tkt.ge/api/Events/Map?mapId=342778&sectionId={sector_id}&orderKey=&api_key=7d8d34d1-e9af-4897-9f0f-5c36c179be77'
            json_data = self._get_json_data_from_selenium(driver, url)
            places = json_data['data']['seats'][4:]
            # places = self._requests_to_places_in_sector(sector_id)
            for place in places:
                if (place_price_id := place['ticketTypeIds']) is not None:
                    place_row = place['rowNumber']
                    place_seat = place['seatNumber']

                    for price_id in place_price_id.split(','):
                        try:
                            place_price = price_data[int(price_id)]
                            break
                        except KeyError:
                            continue
                    else:
                        continue

                    tickets[(place_row, place_seat,)] = place_price
            output_data.append(OutputData(sector_name=sector_name, tickets=tickets))
        return output_data

    def _requests_to_places_in_sector(self, sector_id: int) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ka-GE;ka',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': f'https://tkt.ge/event/{self.event_id}/bruno-mars',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        url = f'https://tkt.ge/api/Events/Map?mapId={self.event_id}&sectionId={sector_id}&orderKey=&api_key=7d8d34d1-e9af-4897-9f0f-5c36c179be77'
        r = self.session.get(url, headers=headers)
        return r.json()['data']['seats'][4:]

    def _get_all_sectors_from_json_data(self, json_data: json) -> dict[str, int]:
        json_all_sectors = json_data['data']['sections']
        all_sectors = {
            data['name'] : data['sectionId']
            for data in json_all_sectors
            if data['ticketTypes'] is not None
        }
        return all_sectors

    def _request_to_get_all_sectors(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ka-GE;ka',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': f'https://tkt.ge/event/{self.event_id}/bruno-mars',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        url = f'https://tkt.ge/api/Events/Map?mapId={self.event_id}&orderKey=&api_key=7d8d34d1-e9af-4897-9f0f-5c36c179be77'
        r = self.session.get(url, headers=headers)
        return r.json()

    def _get_price_data_from_json_data(self, json_data: json) -> dict[int, int]:
        price_data = {}
        json_price_data = json_data['data']['events'][0]['ticketTypes']
        for json_data in json_price_data:
            if '-' in json_data['name'] and '%' in json_data['name']:
                continue
            price_id = json_data['ticketTypeId']
            price = json_data['price']['amount']
            price_data[price_id] = int(price)
        return price_data

    def _requests_to_json_data_to_price(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ka-GE;ka',
            'authorization': 'Bearer undefined',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': f'https://tkt.ge/event/{self.event_id}/bruno-mars',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        return r.json()

    async def body(self):
        for sector in self._parse_seats():
            self.register_sector(sector.sector_name, sector.tickets)
