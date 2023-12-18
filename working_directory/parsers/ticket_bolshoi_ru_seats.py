import json
import os
import random
import threading

import requests
from loguru import logger

from parse_module.manager import authorize
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import parse_utils, captcha

MAX_TRIES = 20
DEL_FROM_CART = False


class BolshoiQueue(authorize.AccountsQueue):
    proxy_check = 'https://ticket.bolshoi.ru/api/csrfToken'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def first_check(self, account):
        try:
            account.csrf_token
        except:
            account.csrf_token = self.get_csrf(account)

        # self.check_orders()

        url = 'https://ticket.bolshoi.ru/api/v1/client/checkout'
        headers = {
            'authority': 'ticket.bolshoi.ru',
            'method': 'GET',
            'path': '/api/v1/client/checkout',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://ticket.bolshoi.ru/checkout',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-csrf-token': account.csrf_token
        }
        r = account.get(url, headers=headers, verify=False)

        try:
            tickets_in_cart = r.json()
        except:
            tickets_in_cart = None
            if 'Unauthorized' in r.text:
                self.debug('Unauthorized, retrying')
                self.login(account)
                return self.first_check(account)
            else:
                raise RuntimeError(f'FIRST CHECK ERROR, passing {account}: {r.text}')
        if not tickets_in_cart:
            return True
        elif not DEL_FROM_CART:
            raise RuntimeError(f'Cart contains tickets, passing {account}')
        url = 'https://ticket.bolshoi.ru/api/v1/client/lock_seats'
        headers = {
            'authority': 'ticket.bolshoi.ru',
            'method': 'DELETE',
            'path': '/api/v1/client/lock_seats',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'origin': 'https://ticket.bolshoi.ru',
            'pragma': 'no-cache',
            'referer': 'https://ticket.bolshoi.ru/checkout',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-csrf-token': account.csrf_token
        }
        r = account.delete(url, headers=headers, verify=False)
        self.debug('deleting on', account.login)

    def is_logined(self, account):
        try:
            account.csrf_token
        except:
            account.csrf_token = self.get_csrf(account)
        seats_url = ('https://ticket.bolshoi.ru/api/v1/client/shows'
                     f'/162/tariffs/1/seats')
        headers = {
            'authority': 'ticket.bolshoi.ru',
            'method': 'GET',
            'path': '/api/v1/client/shows/130/tariffs/1/seats',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-csrf-token': account.csrf_token
        }
        r = account.get(seats_url,
                        headers=headers,
                        verify=False)
        return 'Unauthorized' not in r.text

    def login(self, account, err_counter=0):
        self.prepare_session(account)
        try:
            account.csrf_token
        except:
            account.csrf_token = self.get_csrf(account)
        solved_captcha = captcha.non_selenium_recaptcha(
            self.sitekey,
            'https://ticket.bolshoi.ru/login',
            print_logs=False)
        headers = {
            'authority': 'ticket.bolshoi.ru',
            'method': 'PUT',
            'path': '/api/v1/client/login',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-length': '67',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://ticket.bolshoi.ru',
            'pragma': 'no-cache',
            'referer': 'https://ticket.bolshoi.ru/login',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-csrf-token': account.csrf_token
        }
        params = [
            ('login', account.login),
            ('password', account.password),
            ('reCaptcha', solved_captcha),
            ('remember', 'true')
        ]
        r = account.put('https://ticket.bolshoi.ru/api/v1/client/login',
                        data=params,
                        headers=headers,
                        verify=False)
        if 'одключение к системе' in r.text:
            error = f'{account.login}:{account.password} - Заблокирован!'
            self.add_to_blacklist(account)
            raise RuntimeError(error)
        elif 'Неверное имя пользователя или пароль' in r.text:
            error = f'{account.login}:{account.password} - Неверный логпасс'
            self.add_to_blacklist(account)
            raise RuntimeError(error)
        elif '"error":"recaptcha"' in r.text:
            err_counter += 1
            if err_counter == MAX_TRIES:
                raise RuntimeError(r.text)
            else:
                logger.error('Login error: ' + r.text, name='ticket_bolshoi_ru_seats')
                account.session = requests.Session()
                self.login(account, err_counter=err_counter)

    def prepare_session(self, session):
        url = 'https://ticket.bolshoi.ru/shows'

        headers = {
            'Host': 'ticket.bolshoi.ru',
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Connection': 'keep-alive'
        }
        r = session.get(url, headers=headers, verify=False)

    def get_app_name(self, session):
        url = 'https://ticket.bolshoi.ru/login'

        headers = {
            'Host': 'ticket.bolshoi.ru',
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Connection': 'keep-alive'
        }
        r = session.get(url, headers=headers, verify=False)

        return parse_utils.double_split(r.text, '"/js/app', '"')

    def get_sitekey(self):
        session = ProxySession(self)
        self.prepare_session(session)
        app_name = self.get_app_name(session)
        headers = {
            'authority': 'ticket.bolshoi.ru',
            'method': 'GET',
            'path': f'/js/app{app_name}',
            'scheme': 'https',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://ticket.bolshoi.ru/login',
            'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'script',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = session.get(f'https://ticket.bolshoi.ru/js/app{app_name}',
                        headers=headers,
                        verify=False)

        return parse_utils.double_split(r.text, 'reCaptchaKey:"', '"')

    def get_csrf(self, account):
        headers = {
            'authority': 'ticket.bolshoi.ru',
            'method': 'GET',
            'path': '/api/csrfToken',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        try:
            r = account.get('https://ticket.bolshoi.ru/api/csrfToken',
                            headers=headers,
                            verify=False)
        except Exception as error:
            raise RuntimeError(f'No CSRF on ip ' + str(account.proxy) + ' ' + str(error))

        return r.json()['_csrf']

    def run(self):
        self.proxy = self.proxy_hub.get(self.proxy_check)
        self.sitekey = self.get_sitekey()
        super().run()


class BtParser(SeatsParser):
    event = 'ticket.bolshoi.ru'
    url_filter = lambda url: 'bolshoi.ru' in url
    proxy_check = SpecialConditions(url='https://ticket.bolshoi.ru/api/csrfToken')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.account = None
        self.delay = 900
        self.driver_source = None
        self.event_id = None
        self._lock = threading.Lock()

    def before_body(self):
        self.account = self.get_account()
        self.session = ProxySession(self)
        self.event_id = self.url.split('/')[-1]

    def get_account(self):
        global bt_accounts
        self._lock.acquire()
        if bt_accounts is None:
            bt_accounts = BolshoiQueue('authorize_accounts.txt', self.controller.proxy_hub)
        self._lock.release()
        return bt_accounts.get()

    def block_account(self):
        global bt_accounts
        self._lock.acquire()
        if bt_accounts is None:
            bt_accounts = BolshoiQueue('authorize_accounts.txt', self.controller.proxy_hub)
        self._lock.release()
        bt_accounts.add_to_blacklist(self.account)
        self.account = bt_accounts.get()
        return True

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
                if '1 ярус Левая сторона Ложа № 1' == sector_name or '1 ярус Правая сторона Ложа № 1' == sector_name:
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
        return loz_row

    def get_tickets(self):
        global bt_accounts
        # x_csrf = self.get_csrf()
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en-US;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            # 'x-csrf-token': self.account.csrf_token
        }
        url = f'https://ticket.bolshoi.ru/api/v1/client/shows/{self.event_id}/tariffs/17/seats'
        r = self.account.get(url, headers=headers)
        if 'error' in r.json() and r.json()['error'] == 'Для оформления заказа необходимо подтвердить емейл адрес!':
            self.block_account()
            return []
        return r.json()

    def body(self):
        a_sectors = []
        tickets_data = self.get_tickets()
        for ticket in tickets_data:
            if not ticket['ticketPrice']:
                continue

            if self.scene == 'Новая сцена':
                hall_section_name = ' ' + ticket['hallSectionName'] if ticket['hallSectionName'] else ''
                hall_side_name = ', ' + ticket['hallSideName'].lower() if ticket['hallSideName'] else ''
                if ticket['hallRegionName'] == 'Балкон 3 яруса':
                    hall_side_name = ''
                sector_name = ticket['hallRegionName'] + hall_side_name + hall_section_name
                if sector_name == 'Бенуар, левая сторона Ложа 1':
                    sector_name = sector_name.replace(', ', ',  ')
                elif '1 ярус' in sector_name:
                    sector_name = sector_name.replace('1 ярус', 'Первый ярус')
                row = str(ticket['seatRow'])
                seat = str(ticket['seatNumber'])
                if row == 'None':
                    row = '1'
                if sector_name == 'Первый ярус, левая сторона':
                    row = row.replace('4A', '4')
            else:
                hall_section_name = ' ' + ticket['hallSectionName'] if ticket['hallSectionName'] else ''
                hall_side_name = ' ' + ticket['hallSideName'] if ticket['hallSideName'] else ''
                if ticket['hallRegionName'] == 'Балкон 3 яруса':
                    hall_side_name = ''
                sector_name = ticket['hallRegionName'] + hall_side_name + hall_section_name
                row = str(ticket['seatRow'])
                seat = str(ticket['seatNumber'])
                row = self.reformat_row(row, seat, sector_name)

            price = int(float(ticket['ticketPrice']))

            for sector in a_sectors:
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': sector_name,
                    'tickets': {(row, seat): price}
                })
        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])


bt_accounts = None
