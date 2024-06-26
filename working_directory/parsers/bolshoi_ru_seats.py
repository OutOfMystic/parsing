import os
import re
import json
import time
import threading
import urllib.parse
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twocaptcha import TwoCaptcha

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import ProxySession
from parse_module.utils.captcha import API_KEY
from parse_module.drivers.chrome_selenium_driver import ChromeProxyWebDriver as ProxyWebDriver
from parse_module.utils import utils
from parse_module.utils.date import format_expiry_time


class AuthorizationError(Exception):
    pass

class BolshoiParser(SeatsParser):
    proxy_check_url = 'https://ticket.bolshoi.ru/'
    event = 'ticket.bolshoi.ru'
    url_filter = lambda url: 'ticket.bolshoi.ru' in url
    _instance_lock = threading.Lock()

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 5200
        self.count = 3
        self.driver_source = None
        self.project_root = self.find_project_root()
        self.file_path = os.path.join(self.project_root, 'working_directory/files/parsers_data/bolshoi_ru/')

    def find_project_root(self):
        current_dir = os.path.abspath(__file__)
        while current_dir != os.path.dirname(current_dir):
            if any(os.path.exists(os.path.join(current_dir, indicator)) for indicator in
                   ['requirements.txt']):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        return current_dir  # Вернем корневую папку, если не нашли индикаторы

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, a_sectors):
        bolshoi_tickets_reformat_dict = {
            # Историческая сцена
            'Партер, левая сторона': 'Партер Левая сторона',
            'Партер, правая сторона': 'Партер Правая сторона',
            'Балкон 4 яруса, левая сторона': 'Балкон 4 яруса Левая сторона',
            'Балкон 4 яруса, правая сторона': 'Балкон 4 яруса Правая сторона',
            'Балкон 3 яруса, левая сторона': 'Балкон 3 яруса',
            'Балкон 3 яруса, правая сторона': 'Балкон 3 яруса',
            'Балкон 2 яруса, левая сторона': 'Балкон 2 яруса Левая сторона',
            'Балкон 2 яруса, правая сторона': 'Балкон 2 яруса Правая сторона',
            '3 ярус, левая сторона Ложа № 1': '3 ярус Левая сторона Ложа № 1',
            '3 ярус, левая сторона Ложа № 2': '3 ярус Левая сторона Ложа № 2',
            '3 ярус, левая сторона Ложа № 3': '3 ярус Левая сторона Ложа № 3',
            '3 ярус, левая сторона Ложа № 4': '3 ярус Левая сторона Ложа № 4',
            '3 ярус, левая сторона Ложа № 5': '3 ярус Левая сторона Ложа № 5',
            '3 ярус, левая сторона Ложа № 6': '3 ярус Левая сторона Ложа № 6',
            '3 ярус, левая сторона Ложа № 7': '3 ярус Левая сторона Ложа № 7',
            '3 ярус, левая сторона Ложа № 8': '3 ярус Левая сторона Ложа № 8',
            '3 ярус, левая сторона Ложа № 9': '3 ярус Левая сторона Ложа № 9',
            '3 ярус, правая сторона Ложа № 1': '3 ярус Правая сторона Ложа № 1',
            '3 ярус, правая сторона Ложа № 2': '3 ярус Правая сторона Ложа № 2',
            '3 ярус, правая сторона Ложа № 3': '3 ярус Правая сторона Ложа № 3',
            '3 ярус, правая сторона Ложа № 4': '3 ярус Правая сторона Ложа № 4',
            '3 ярус, правая сторона Ложа № 5': '3 ярус Правая сторона Ложа № 5',
            '3 ярус, правая сторона Ложа № 6': '3 ярус Правая сторона Ложа № 6',
            '3 ярус, правая сторона Ложа № 7': '3 ярус Правая сторона Ложа № 7',
            '3 ярус, правая сторона Ложа № 8': '3 ярус Правая сторона Ложа № 8',
            '3 ярус, правая сторона Ложа № 9': '3 ярус Правая сторона Ложа № 9',
            '2 ярус, левая сторона Ложа № 1': '2 ярус Левая сторона Ложа № 1',
            '2 ярус, левая сторона Ложа № 2': '2 ярус Левая сторона Ложа № 2',
            '2 ярус, левая сторона Ложа № 3': '2 ярус Левая сторона Ложа № 3',
            '2 ярус, левая сторона Ложа № 4': '2 ярус Левая сторона Ложа № 4',
            '2 ярус, левая сторона Ложа № 5': '2 ярус Левая сторона Ложа № 5',
            '2 ярус, левая сторона Ложа № 6': '2 ярус Левая сторона Ложа № 6',
            '2 ярус, левая сторона Ложа № 7': '2 ярус Левая сторона Ложа № 7',
            '2 ярус, левая сторона Ложа № 8': '2 ярус Левая сторона Ложа № 8',
            '2 ярус, левая сторона Ложа № 9': '2 ярус Левая сторона Ложа № 9',
            '2 ярус, правая сторона Ложа № 1': '2 ярус Правая сторона Ложа № 1',
            '2 ярус, правая сторона Ложа № 2': '2 ярус Правая сторона Ложа № 2',
            '2 ярус, правая сторона Ложа № 3': '2 ярус Правая сторона Ложа № 3',
            '2 ярус, правая сторона Ложа № 4': '2 ярус Правая сторона Ложа № 4',
            '2 ярус, правая сторона Ложа № 5': '2 ярус Правая сторона Ложа № 5',
            '2 ярус, правая сторона Ложа № 6': '2 ярус Правая сторона Ложа № 6',
            '2 ярус, правая сторона Ложа № 7': '2 ярус Правая сторона Ложа № 7',
            '2 ярус, правая сторона Ложа № 8': '2 ярус Правая сторона Ложа № 8',
            '2 ярус, правая сторона Ложа № 9': '2 ярус Правая сторона Ложа № 9',
            '1 ярус, левая сторона Ложа № 1': '1 ярус Левая сторона Ложа № 1',
            '1 ярус, левая сторона Ложа № 2': '1 ярус Левая сторона Ложа № 2',
            '1 ярус, левая сторона Ложа № 3': '1 ярус Левая сторона Ложа № 3',
            '1 ярус, левая сторона Ложа № 4': '1 ярус Левая сторона Ложа № 4',
            '1 ярус, левая сторона Ложа № 5': '1 ярус Левая сторона Ложа № 5',
            '1 ярус, левая сторона Ложа № 6': '1 ярус Левая сторона Ложа № 6',
            '1 ярус, левая сторона Ложа № 7': '1 ярус Левая сторона Ложа № 7',
            '1 ярус, левая сторона Ложа № 8': '1 ярус Левая сторона Ложа № 8',
            '1 ярус, левая сторона Ложа № 9': '1 ярус Левая сторона Ложа № 9',
            '1 ярус, левая сторона Ложа № 10': '1 ярус Левая сторона Ложа № 10',
            '1 ярус, левая сторона Ложа № 11': '1 ярус Левая сторона Ложа № 11',
            '1 ярус, левая сторона': '1 ярус Левая сторона Ложа № 12',
            '1 ярус, правая сторона Ложа № 1': '1 ярус Правая сторона Ложа № 1',
            '1 ярус, правая сторона Ложа № 2': '1 ярус Правая сторона Ложа № 2',
            '1 ярус, правая сторона Ложа № 3': '1 ярус Правая сторона Ложа № 3',
            '1 ярус, правая сторона Ложа № 4': '1 ярус Правая сторона Ложа № 4',
            '1 ярус, правая сторона Ложа № 5': '1 ярус Правая сторона Ложа № 5',
            '1 ярус, правая сторона Ложа № 6': '1 ярус Правая сторона Ложа № 6',
            '1 ярус, правая сторона Ложа № 7': '1 ярус Правая сторона Ложа № 7',
            '1 ярус, правая сторона Ложа № 8': '1 ярус Правая сторона Ложа № 8',
            '1 ярус, правая сторона Ложа № 9': '1 ярус Правая сторона Ложа № 9',
            '1 ярус, правая сторона Ложа № 10': '1 ярус Правая сторона Ложа № 10',
            '1 ярус, правая сторона Ложа № 11': '1 ярус Правая сторона Ложа № 11',
            '1 ярус, правая сторона': '1 ярус Правая сторона Ложа № 12',
            'Бельэтаж, левая сторона Ложа № 1': 'Бельэтаж Левая сторона Ложа № 1',
            'Бельэтаж, левая сторона Ложа № 2': 'Бельэтаж Левая сторона Ложа № 2',
            'Бельэтаж, левая сторона Ложа № 3': 'Бельэтаж Левая сторона Ложа № 3',
            'Бельэтаж, левая сторона Ложа № 4': 'Бельэтаж Левая сторона Ложа № 4',
            'Бельэтаж, левая сторона Ложа № 5': 'Бельэтаж Левая сторона Ложа № 5',
            'Бельэтаж, левая сторона Ложа № 6': 'Бельэтаж Левая сторона Ложа № 6',
            'Бельэтаж, левая сторона Ложа № 7': 'Бельэтаж Левая сторона Ложа № 7',
            'Бельэтаж, левая сторона Ложа № 8': 'Бельэтаж Левая сторона Ложа № 8',
            'Бельэтаж, левая сторона Ложа № 9': 'Бельэтаж Левая сторона Ложа № 9',
            'Бельэтаж, левая сторона Ложа № 10': 'Бельэтаж Левая сторона Ложа № 10',
            'Бельэтаж, левая сторона Ложа № 11': 'Бельэтаж Левая сторона Ложа № 11',
            'Бельэтаж, левая сторона Ложа № 12': 'Бельэтаж Левая сторона Ложа № 12',
            'Бельэтаж, левая сторона Ложа № 13': 'Бельэтаж Левая сторона Ложа № 13',
            'Бельэтаж, левая сторона Ложа № 14': 'Бельэтаж Левая сторона Ложа № 14',
            'Бельэтаж, левая сторона Ложа № 15': 'Бельэтаж Левая сторона Ложа № 15',
            'Бельэтаж, правая сторона Ложа № 1': 'Бельэтаж Правая сторона Ложа № 1',
            'Бельэтаж, правая сторона Ложа № 2': 'Бельэтаж Правая сторона Ложа № 2',
            'Бельэтаж, правая сторона Ложа № 3': 'Бельэтаж Правая сторона Ложа № 3',
            'Бельэтаж, правая сторона Ложа № 4': 'Бельэтаж Правая сторона Ложа № 4',
            'Бельэтаж, правая сторона Ложа № 5': 'Бельэтаж Правая сторона Ложа № 5',
            'Бельэтаж, правая сторона Ложа № 6': 'Бельэтаж Правая сторона Ложа № 6',
            'Бельэтаж, правая сторона Ложа № 7': 'Бельэтаж Правая сторона Ложа № 7',
            'Бельэтаж, правая сторона Ложа № 8': 'Бельэтаж Правая сторона Ложа № 8',
            'Бельэтаж, правая сторона Ложа № 9': 'Бельэтаж Правая сторона Ложа № 9',
            'Бельэтаж, правая сторона Ложа № 10': 'Бельэтаж Правая сторона Ложа № 10',
            'Бельэтаж, правая сторона Ложа № 11': 'Бельэтаж Правая сторона Ложа № 11',
            'Бельэтаж, правая сторона Ложа № 12': 'Бельэтаж Правая сторона Ложа № 12',
            'Бельэтаж, правая сторона Ложа № 13': 'Бельэтаж Правая сторона Ложа № 13',
            'Бельэтаж, правая сторона Ложа № 14': 'Бельэтаж Правая сторона Ложа № 14',
            'Бельэтаж, правая сторона Ложа № 15': 'Бельэтаж Правая сторона Ложа № 15',
            'Амфитеатр, левая сторона': 'Амфитеатр Левая сторона',
            'Амфитеатр, правая сторона': 'Амфитеатр Правая сторона',
            'Бенуар, левая сторона Ложа № 1': 'Бенуар Левая сторона Ложа № 1',
            'Бенуар, левая сторона Ложа № 2': 'Бенуар Левая сторона Ложа № 2',
            'Бенуар, левая сторона Ложа № 3': 'Бенуар Левая сторона Ложа № 3',
            'Бенуар, левая сторона Ложа № 4': 'Бенуар Левая сторона Ложа № 4',
            'Бенуар, левая сторона Ложа № 5': 'Бенуар Левая сторона Ложа № 5',
            'Бенуар, левая сторона Ложа № 6': 'Бенуар Левая сторона Ложа № 6',
            'Бенуар, левая сторона Ложа № 7': 'Бенуар Левая сторона Ложа № 7',
            'Бенуар, левая сторона Ложа № 8': 'Бенуар Левая сторона Ложа № 8',
            'Бенуар, правая сторона Ложа № 1': 'Бенуар Правая сторона Ложа № 1',
            'Бенуар, правая сторона Ложа № 2': 'Бенуар Правая сторона Ложа № 2',
            'Бенуар, правая сторона Ложа № 3': 'Бенуар Правая сторона Ложа № 3',
            'Бенуар, правая сторона Ложа № 4': 'Бенуар Правая сторона Ложа № 4',
            'Бенуар, правая сторона Ложа № 5': 'Бенуар Правая сторона Ложа № 5',
            'Бенуар, правая сторона Ложа № 6': 'Бенуар Правая сторона Ложа № 6',
            'Бенуар, правая сторона Ложа № 7': 'Бенуар Правая сторона Ложа № 7',
            'Бенуар, правая сторона Ложа № 8': 'Бенуар Правая сторона Ложа № 8'
        }
        bolshoi_tickets_reformat_dict_new_scene = {
            # Новая сцена
            'Партер, левая сторона': 'Партер, левая сторона',
            'Партер, правая сторона': 'Партер, правая сторона',
            'Амфитеатр, левая сторона': 'Амфитеатр, левая сторона',
            'Амфитеатр, правая сторона': 'Амфитеатр, правая сторона',
            'Бенуар, левая сторона Ложа 1': 'Бенуар,  левая сторона Ложа 1',
            'Бенуар, правая сторона Ложа 1': 'Бенуар, правая сторона Ложа 1',
            'Бенуар, левая сторона': 'Бенуар, левая сторона',
            'Бенуар, правая сторона': 'Бенуар, правая сторона',
            'Бельэтаж, правая сторона Ложа 1': 'Бельэтаж, правая сторона Ложа 1',
            'Бельэтаж, левая сторона': 'Бельэтаж, левая сторона',
            'Бельэтаж, правая сторона': 'Бельэтаж, правая сторона',
            '1 ярус, левая сторона Ложа 1': 'Первый ярус, левая сторона Ложа 1',
            '1 ярус, правая сторона Ложа 1': 'Первый ярус, правая сторона Ложа 1',
            '1 ярус, левая сторона': 'Первый ярус, левая сторона',
            '1 ярус, правая сторона': 'Первый ярус, правая сторона'
        }

        ref_dict = {}
        if 'большой театр' in self.venue.lower():
            if "Новая сцена" in self.scene:
                ref_dict = bolshoi_tickets_reformat_dict_new_scene
            else:
                ref_dict = bolshoi_tickets_reformat_dict

        for sector in a_sectors:
            sector['name'] = ref_dict.get(sector['name'], sector['name'])

    def reformat_row(self, row, seat, sector_name):
        loz_row = row
        if not row or row == 'None':
            loz_row = '1'
        if 'Ложа' in sector_name:
            if 'Бенуар' in sector_name:
                if seat in ['1', '3', '5']:
                    loz_row = '1'
                else:
                    loz_row = '2'
            elif 'Бельэтаж' in sector_name:
                if seat in ['1', '3', '5']:
                    loz_row = '1'
                elif seat in ['2', '4', '6']:
                    loz_row = '2'
                else:
                    loz_row = '3'
            elif '1 ярус' in sector_name:
                if '1 ярус Левая сторона Ложа № 1' == sector_name:
                    if seat in ['1', '2', '3', '5', '7']:
                        loz_row = '1'
                    elif seat in ['4', '6', '8']:
                        loz_row = '2'
                elif '№ 10' in sector_name or '№ 11' in sector_name:
                    if seat in ['1', '3', '5']:
                        loz_row = '1'
                    elif seat in ['2', '4', '6']:
                        loz_row = '2'
                    else:
                        loz_row = '3'
                elif '№ 12' in sector_name:
                    pass
                else:
                    if seat in ['1', '3', '5']:
                        loz_row = '1'
                    else:
                        loz_row = '2'
            elif '2 ярус' in sector_name:
                if '№ 7' in sector_name or '№ 8' in sector_name or '№ 9' in sector_name:
                    if seat in ['1', '3', '5']:
                        loz_row = '1'
                    else:
                        loz_row = '2'
                else:
                    loz_row = '1'
            elif '3 ярус' in sector_name:
                loz_row = '1'
        if self.scene == 'Новая сцена':
            if 'Бенуар' in sector_name:
                loz_row = '1'
        return loz_row


    def parse_seats(self, ready_json):
        total_sector = []
        all_sector = {}
        for seats in ready_json:
            price = seats.get('ticketPrice')
            if price:
                sector_first_part = seats.get('hallRegionName')
                sector_second_part = seats.get('hallSideName')
                if sector_first_part is None:
                    sector_first_part = ''
                if sector_second_part is None:
                    sector_second_part = ''
                sector = sector_first_part + ', ' + sector_second_part.lower()

                seats_row = seats.get('seatRow')
                seats_number = seats.get('seatNumber')
                if seats_row is None:
                    seats_row = seats.get('hallSectionName')

                if self.scene == 'Новая сцена' and sector_first_part == 'Бельэтаж'\
                        and seats_row is not None and seats.get('hallSectionName') is not None:
                    sector += ' ' + seats.get('hallSectionName')

                if "Ложа" in seats_row:
                    sector += ' ' + seats_row

                seats_row = self.reformat_row(seats_row, seats_number, sector)

                if all_sector.get(sector):
                    dict_sector = all_sector[sector]
                    dict_sector[(seats_row, seats_number,)] = price
                else:
                    all_sector[sector] = {(seats_row, seats_number,): price}

        for sector, total_seats_row_prices in all_sector.items():
            total_sector.append(
                {
                    "name": sector,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def authorization(self):
        with ProxyWebDriver(proxy_controller=self.proxy, capability=True) as driver:
            driver.get('https://ticket.bolshoi.ru/login')

            self.wait = WebDriverWait(driver, 10)

            login_field = self.wait.until(EC.presence_of_element_located((By.ID, "login")))
            login_field.send_keys("mikheyev9@gmail.com")
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
            password_field.send_keys("Sb2,*9)HcHhiBFL")

            reCaptcha_code = self._solve_google_captcha(driver)
            data = {
                'login': 'mikheyev9@gmail.com',
                'password': 'Sb2,*9)HcHhiBFL',
                'reCaptcha': reCaptcha_code,
                'remember': 'true'
            }

            # Преобразование данных в формат application/x-www-form-urlencoded
            data_encoded = urllib.parse.urlencode(data)

            chrome_logs = driver.get_capabilites_logs()
            _csrf = self._work_with_logs(driver, chrome_logs)

            # JavaScript для отправки POST-запроса
            js_code = f"""
                        var callback = arguments[arguments.length - 1];
                        var xhr = new XMLHttpRequest();
                        xhr.open('PUT', 'https://ticket.bolshoi.ru/api/v1/client/login', true);
                        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                        xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');
                        xhr.setRequestHeader('X-Csrf-Token', '{_csrf}');
                        xhr.onreadystatechange = function() {{
                            if (xhr.readyState == 4) {{
                                var result;
                                if (xhr.status == 200) {{
                                    result = {{status: 'success', response: xhr.responseText}};
                                }} else {{
                                    result = {{status: 'error', response: xhr.statusText, code: xhr.status}};
                                }}
                                console.log(result);
                                callback(result);
                            }}
                        }};
                        xhr.onerror = function() {{
                            var result = {{status: 'error', response: 'Network error'}};
                            console.log(result);
                            callback(result);
                        }};
                        xhr.send('{data_encoded}');
                        """
            result = driver.execute_async_script(js_code, 10000)
            if result and result['status'] == 'success':
                print(utils.colorize(f"{type(self).__name__}| "
                                            f"Ответ: {result['response']}", color=utils.Fore.GREEN))
                driver.refresh()
                cookies = driver.get_cookies()

                self._write_on_file_for_test('cookies.json', cookies)
                return True
            else:
                print(utils.colorize(f"{type(self).__name__}| "
                                     f"Ошибка: {result['response']}", color=utils.Fore.RED))
                self._try_authorize()

    def _try_authorize(self):
        if self.count:
            self.count -= 1
            self.authorization()
        else:
            raise AuthorizationError

    def _solve_google_captcha(self, driver, use_proxy=False):
        solver = TwoCaptcha(API_KEY)

        iframe = self.wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@title="reCAPTCHA"]')))
        iframe_src = iframe.get_attribute('src')

        current_url = driver.current_url
        pattern_find_data_sitekey_for_google_captcha = r'(?<=&k\=).+?(?=\&)'
        google_data_sitekey = re.search(pattern_find_data_sitekey_for_google_captcha, iframe_src)[0]

        data_for_send_to_recaptcha = dict(sitekey=google_data_sitekey,
                                  url=current_url)

        if use_proxy:
            user_agent = driver.execute_script("return navigator.userAgent;")
            proxy_dict = {
                'type': 'HTTPS',
                'uri': f'{self.proxy.login}:{self.proxy.password}@{self.proxy.ip}:{self.proxy.port}'
            }
            data_for_send_to_recaptcha.update(dict(proxy=proxy_dict,
                                    userAgent=user_agent))

        result = solver.recaptcha(**data_for_send_to_recaptcha)
        print(utils.colorize(f'2Captcha| {result}', color=utils.Fore.GREEN))
        return result['code']

    def _work_with_logs(self, driver, chrome_logs,
                        debug=False):
        if debug:
            self._write_on_file_for_test('goog_loggingPrefs.json', chrome_logs)

        _csrf_data = driver.find_data_in_responseReceived(chrome_logs,
                                                     find_patterns=('https://ticket.bolshoi.ru/api/csrfToken'))
        _csrf = _csrf_data.get('_csrf')
        return _csrf

    def _write_on_file_for_test(self, file_name, data):
        with open(f'{self.file_path}{file_name}', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def _load_cookies(self, driver, filepath):
        with open(filepath, 'r') as file:
            cookies = json.load(file)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                driver.add_cookie(cookie)

    def check_cookies(self):
        if os.path.exists(f'{self.file_path}cookies.json'):
            is_cookie_valid, expiry_time = self._check_cookies_expiry()
            if is_cookie_valid:
                mess = f"{type(self).__name__}| Файл cookies.json действителен {expiry_time}"
                print(utils.colorize(mess, color=utils.Fore.GREEN))
                return True
            else:
                mess = f"{type(self).__name__}| Файл cookies.json недействителен {expiry_time}"
                print(utils.colorize(mess, color=utils.Fore.YELLOW))
        else:
            mess = f"{type(self).__name__}| Файл cookies.json не найден."
            print(utils.colorize(mess, color=utils.Fore.YELLOW))
            return False

    def _check_cookies_expiry(self):
         with open(f'{self.file_path}cookies.json', 'r') as file:
             cookies = json.load(file)
             cookies_with_expiry = [cookie for cookie in cookies if 'expiry' in cookie]
             min_expiry_cookie = min(cookies_with_expiry, key=lambda c: c['expiry'])

             current_time = datetime.utcnow().timestamp()
             expiry_time = format_expiry_time(min_expiry_cookie['expiry'])
             is_cookie_valid = min_expiry_cookie['expiry'] > current_time

         return is_cookie_valid, expiry_time


    def authorize_with_cookies_and_request_to_url(self, w=False):
        with ProxyWebDriver(proxy_controller=self.proxy, capability=True) as driver:
            driver.get('https://ticket.bolshoi.ru')
            driver.delete_all_cookies()
            self._load_cookies(driver, f'{self.file_path}cookies.json')
            driver.refresh()
            driver.get(self.url)
            time.sleep(2)
            json_seats = self._find_json_with_seats(driver, w=w)
            #time.sleep(200)
            return json_seats

    def _find_json_with_seats(self, driver, w=False):
        json_seats = driver.find_data_in_responseReceived(print_all_urls=False,
            find_patterns=('https://ticket.bolshoi.ru/api/v1/client/shows',
                           'tariffs'))
        if w:
            self._write_on_file_for_test('json_seats.json', json_seats)
        #print(json_seats)
        return json_seats

    def body(self):
        with self._instance_lock:
            is_cookies = self.check_cookies()
            if not is_cookies:
                self.authorization()
            json_seats = self.authorize_with_cookies_and_request_to_url(w=False)
            if not json_seats:
                raise AuthorizationError
            total_sectors = self.parse_seats(json_seats)
            self.reformat(total_sectors)

        for sector in total_sectors:
            #print(sector['name'], len(sector['tickets']))
            self.register_sector(sector['name'], sector['tickets'])