import json
import asyncio
from aiohttp import ClientPayloadError, ClientProxyConnectionError
import re
import base64

from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image, ImageOps

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.utils import async_captcha
from parse_module.drivers.proxelenium import ProxyWebDriver
from parse_module.utils.captcha import yandex_afisha_coordinates_captha


class YandexAfishaParser(AsyncSeatsParser):
    proxy_check = SpecialConditions(url='https://afisha.yandex.ru/')
    event = 'afisha.yandex.ru'
    url_filter = lambda url: 'afisha.yandex.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.spreading = 4

        self.count_error = 0
        self.req_number = 0
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'connection': 'keep-alive',
            'host': 'widget.afisha.yandex.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        self.session_key = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, sectors):
        if 'ВТБ Арена' == self.venue and 'Динамо' in self.event_name : #Если матчи ХК Динамо
            tribune_1 = 'Трибуна Давыдова. '
            tribune_2 = 'Трибуна Васильева. '
            tribune_3 = 'Трибуна Юрзинова. '
            tribune_4 = 'Трибуна Мальцева. '

            for sector in sectors:
                sector_name = sector.get('name').strip()
                if 'A305' in sector_name:
                    sector['name'] = "Трибуна Васильева. Сектор A305"
                if 'Ресторан' in sector_name:
                    sector['name'] = tribune_3 + sector_name
                if 'Press' in sector_name or 'VVIP' in sector_name:
                    sector['name'] = tribune_1 + sector_name
                if 'Сектор' in sector_name:
                    try:
                        number_sector = int(sector_name.split('.')[0][-3:])
                    except ValueError:
                        continue
                    # if sector_name[-4] == 'A' and 100 < number_sector <= 110:
                    #     sector['name'] = tribune_1 + sector_name
                    #     continue
                    if 300 < number_sector <= 303 or 200 < number_sector <= 203 or 100 < number_sector <= 103:
                        tribune = tribune_1 if 'A' in sector_name else tribune_3
                        sector['name'] = tribune + sector_name
                    elif 304 <= number_sector <= 309 or 204 <= number_sector <= 211 or 104 <= number_sector <= 108:
                        tribune = tribune_2 if 'A' in sector_name else tribune_4
                        sector['name'] = tribune + sector_name
                    elif 310 <= number_sector < 315 or 212 <= number_sector < 215 or 109 <= number_sector < 115:
                        tribune = tribune_3 if 'A' in sector_name else tribune_1
                        sector['name'] = tribune + sector_name
                if 'Ложа' in sector_name:
                    number_sector = int(sector_name[-2:])
                    if sector_name[-4] == 'A':
                        if 1 < number_sector <= 4:
                            sector['name'] = tribune_1 + sector_name
                        elif 5 <= number_sector <= 17:
                            sector['name'] = tribune_2 + sector_name
                        elif 18 <= number_sector < 2:
                            sector['name'] = tribune_3 + sector_name
                    else:
                        if 1 < number_sector <= 5:
                            sector['name'] = tribune_3 + sector_name
                        elif 6 <= number_sector <= 18:
                            sector['name'] = tribune_4 + sector_name
                        elif 19 <= number_sector < 2:
                            sector['name'] = tribune_1 + sector_name

        elif self.venue == 'БКЗ «Октябрьский»':
            for sector in sectors:
                if '(ограниченная видимость)' in sector['name']:
                    sector['name'] = 'Балкон (места с ограниченной видимостью)'
                elif 'Партер' in sector['name']:
                    sector['name'] = 'Партер'
                elif 'Балкон' in sector['name']:
                    sector['name'] = 'Балкон'
        elif self.venue == 'Крокус Сити Холл':
            for sector in sectors:
                if 'VIP-партер' == sector['name']:
                    sector['name'] = 'VIP партер'
                if 'Grand-партер' == sector['name']:
                    sector['name'] = 'Grand партер'
                if 'Grand-партер' in sector['name'] and 'ряд' in sector['name']:
                    sector['name'] = sector['name'].replace('-', ' ')
                if 'VIP-ложа' in sector['name']:
                    # if 'на' in sector['name'] and 'персон' in sector['name']:
                    #     continue
                    if 'VIP-ложа Silver 1' in sector['name']:
                        sector['name'] = 'SILVER 1'
                    elif 'VIP-ложа Silver 2' in sector['name']:
                        sector['name'] = 'SILVER 2'
                    elif 'VIP-ложа Silver 3' in sector['name']:
                        sector['name'] = 'SILVER 3'
                    elif 'VIP-ложа Platinum 4' in sector['name']:
                        sector['name'] = 'PLATINUM 4 '
                    elif 'VIP-ложа Platinum 5A' in sector['name']:
                        sector['name'] = 'PLATINUM'
                    elif 'VIP-ложа Platinum 5B' in sector['name']:
                        sector['name'] = 'PLATINUM 5'
                    elif 'VIP-ложа Gold 6' in sector['name']:
                        sector['name'] = 'GOLD 6'
                    elif 'VIP-ложа Gold 7' in sector['name']:
                        sector['name'] = 'GOLD 7'
                    elif 'VIP-ложа Gold 8' in sector['name']:
                        sector['name'] = 'GOLD 8'
        elif self.venue == 'Большая спортивная арена «Лужники»':
            for sector in sectors:
                if '(ограниченная видимость)' in sector['name']:
                    sector['name'] = sector['name'].replace(' (ограниченная видимость)', '')
                elif sector['name'] in ['Сектор C142', 'Ложа VVIP', 'Сектор A103']:
                    sector['name'] = sector['name'] + ' Нету на схеме'
        elif self.venue == 'Театр сатиры':
            for sector in sectors:
                if 'Партер' in sector['name']:
                    sector['name'] = 'Партер'
                elif 'ложа' in sector['name']:
                    sector['name'] = 'Ложа'
                elif 'Амфитеатр' in sector['name']:
                    sector['name'] = 'Амфитеатр'
        elif self.venue == 'Зимний театр':
            to_del = []
            to_add = {}
            for index_sector, sector in enumerate(sectors):
                if 'Бенуар' in sector['name'] or 'Бельэтаж' in sector['name']:
                    to_del.append(index_sector)
                    number_lozha = sector['name'].split()[-1]
                    new_sector_name = sector['name'].split(',')[0]
                    new_sector_tickets = {
                        (number_lozha, place[1],): price
                        for place, price in sector['tickets'].items()
                    }
                    try:
                        old_new_sector_tickets = to_add[new_sector_name]
                        to_add[new_sector_name] = old_new_sector_tickets | new_sector_tickets
                    except KeyError:
                        to_add[new_sector_name] = new_sector_tickets

            to_del = sorted(to_del)[::-1]
            for sector_index in to_del:
                sectors.pop(sector_index)
            for sector_name, sector_tickets in to_add.items():
                new_sector = {
                    'name': sector_name,
                    'tickets': sector_tickets
                }
                sectors.append(new_sector)
        elif self.venue == 'Мегаспорт':
            for sector in sectors:
                if re.compile(r'Фан[- ]сектор').search(sector['name']) and ('(гости)' in sector['name'] or '(хозяева)' in sector['name']):
                    sector['name'] = 'Сектор ' + sector['name'].split()[1]

    def reformat_sectors_mikhailovsky(self, row, seat, sector_name, price):
        if 'ярус' in sector_name:
            sector_name = sector_name.replace('-й', '')
        if 'Ложа' in sector_name:
            if 'А' in row or 'Б' in row or 'В' in row or 'Д' in row:
                if '(2 билета рядом)' not in sector_name:
                    sector_name = 'Ложа ' + row + ' - (2 билета рядом) продаётся по два места'
                row = '1'
                if 'В' in sector_name or 'Д' in sector_name:
                    if seat == '1' or seat == '4':
                        seat = '1, 4'
                    elif seat == '2' or seat == '5':
                        seat = '2, 5'
                    elif seat == '3' or seat == '6':
                        seat = '3, 6'
                else:
                    if seat == '1' or seat == '5':
                        seat = '1, 5'
                    elif seat == '2' or seat == '6':
                        seat = '2, 6'
                    elif seat == '3' or seat == '7':
                        seat = '3, 7'
                    else:
                        seat = '4, 8'
                price *= 2
            else:
                sector_name = f'Ложи {sector_name}а'.capitalize()
                row = row.replace('Ложа ', '')
        if 'Ложи бельэтажа' in sector_name:
            if '(4 билета рядом)' not in sector_name:
                sector_name = 'Ложи бельэтажа - (4 билета рядом) продаётся целиком'
            row = 'Ложа номер ' + row
            seat = 'Места с 1 по 4'
            price *= 4
        if 'Ложи бенуара' in sector_name:
            if '(2 билета рядом)' not in sector_name:
                sector_name = sector_name + ' - (2 билета рядом) продаётся по два места'
            row = 'Ложа номер ' + row
            if seat == '1' or seat == '3':
                seat = 'Места 1 и 3'
            elif seat == '2' or seat == '4':
                seat = 'Места 2 и 4'
            price *= 2

        return row, seat, sector_name, price

    def reformat_sectors_crocus(self, row, seat, r_sector, r_sector_name):
        if 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name\
                or 'Крокус Сити Холл-Vip-партер' in self.scheme.name:
            if 'VIP-партер' == r_sector['name']:
                if row == '12':
                    if int(seat) <= 17:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 53:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                if row == '11':
                    if int(seat) <= 17:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 53:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '10':
                    if int(seat) <= 16:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 58:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '9':
                    if int(seat) <= 15:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 57:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                if row == '8':
                    if int(seat) <= 15:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 57:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '7':
                    if int(seat) <= 13:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 41:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '6':
                    if int(seat) <= 13:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 41:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '5':
                    if int(seat) <= 11:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 35:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '4':
                    if int(seat) <= 11:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 35:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '3':
                    if int(seat) <= 11:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 35:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '2':
                    if int(seat) <= 9:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 29:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
                elif row == '1':
                    if int(seat) <= 8:
                        r_sector_name = 'VIP партер 1'
                    elif int(seat) <= 26:
                        r_sector_name = 'VIP партер 2'
                    else:
                        r_sector_name = 'VIP партер 3'
        if ('Крокус Сити Холл-Столы' in self.scheme.name and 'в 4 ряда' not in self.scheme.name)\
                or 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name\
                or 'Крокус Сити Холл-Vip-партер' in self.scheme.name:
            if 'Партер' == r_sector['name']:
                if row == '8':
                    if int(seat) <= 25:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 61:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '7':
                    if int(seat) <= 23:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 60:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '6':
                    if int(seat) <= 23:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 57:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '5':
                    if int(seat) <= 22:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 56:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '4':
                    if int(seat) <= 22:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 66:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '3':
                    if int(seat) <= 21:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 65:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '2':
                    if int(seat) <= 19:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 63:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
                elif row == '1':
                    if int(seat) <= 18:
                        r_sector_name = 'Партер 1'
                    elif int(seat) <= 60:
                        r_sector_name = 'Партер 2'
                    else:
                        r_sector_name = 'Партер 3'
            if 'Амфитеатр' == r_sector['name'] or 'Партер' == r_sector['name']:
                if (row == '6' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '14':
                    if row == '6':
                        row = '14'
                    if int(seat) <= 17:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 33:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 50:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '5' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '13':
                    if row == '5':
                        row = '13'
                    if int(seat) <= 17:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 33:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 65:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 81:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '4' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '12':
                    if row == '4':
                        row = '12'
                    if int(seat) <= 16:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 32:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 64:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 80:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '3' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '11':
                    if row == '3':
                        row = '11'
                    if int(seat) <= 16:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 31:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 62:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 77:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '2' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '10':
                    if row == '2':
                        row = '10'
                    if int(seat) <= 15:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 30:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 60:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 75:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
                elif (row == '1' and not 'Крокус Сити Холл-Без Амфитиатра' in self.scheme.name) or row == '9':
                    if row == '1':
                        row = '9'
                    if int(seat) <= 10:
                        r_sector_name = 'Партер 4'
                    elif int(seat) <= 24:
                        r_sector_name = 'Партер 5'
                    elif int(seat) <= 44:
                        r_sector_name = 'Партер 6'
                    elif int(seat) <= 58:
                        r_sector_name = 'Партер 7'
                    else:
                        r_sector_name = 'Партер 8'
        if 'Бельэтаж' == r_sector['name']:
            if row == '8':
                if int(seat) <= 27:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 50:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 93:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 117:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '7':
                if int(seat) <= 27:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 49:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 90:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 113:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '6':
                if int(seat) <= 27:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 48:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 89:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 112:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '5':
                if int(seat) <= 25:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 48:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 86:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 108:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '4':
                if int(seat) <= 25:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 46:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 85:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 107:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '3':
                if int(seat) <= 24:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 44:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 83:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 104:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '2':
                if int(seat) <= 24:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 44:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 81:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 102:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
            elif row == '1':
                if int(seat) <= 23:
                    r_sector_name = 'Бельэтаж 1'
                elif int(seat) <= 42:
                    r_sector_name = 'Бельэтаж 2'
                elif int(seat) <= 70:
                    r_sector_name = 'Бельэтаж 3'
                elif int(seat) <= 98:
                    r_sector_name = 'Бельэтаж 4'
                else:
                    r_sector_name = 'Бельэтаж 5'
        elif 'Балкон' == r_sector['name']:
            if row == '17':
                if int(seat) <= 38:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 69:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 129:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 162:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '16':
                if int(seat) <= 38:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 71:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 130:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 164:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '15':
                if int(seat) <= 3:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 70:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 129:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 163:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '14':
                if int(seat) <= 37:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 69:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 127:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 161:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '13':
                if int(seat) <= 37:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 69:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 126:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 159:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '12':
                if int(seat) <= 36:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 68:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 122:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 154:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '11':
                if int(seat) <= 36:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 67:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 122:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 154:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '10':
                if int(seat) <= 35:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 65:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 120:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 151:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '9':
                if int(seat) <= 34:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 63:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 147:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            if row == '8':
                if int(seat) <= 34:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 63:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 147:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '7':
                if int(seat) <= 33:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 61:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 112:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 141:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '6':
                if int(seat) <= 29:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 54:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 97:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 123:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '5':
                if int(seat) <= 29:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 53:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 96:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 121:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '4':
                if int(seat) <= 25:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 51:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 92:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '3':
                if int(seat) <= 28:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 51:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 92:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 116:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '2':
                if int(seat) <= 28:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 49:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 88:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 111:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
            elif row == '1':
                if int(seat) <= 24:
                    r_sector_name = 'Балкон 1'
                elif int(seat) <= 43:
                    r_sector_name = 'Балкон 2'
                elif int(seat) <= 76:
                    r_sector_name = 'Балкон 3'
                elif int(seat) <= 97:
                    r_sector_name = 'Балкон 4'
                else:
                    r_sector_name = 'Балкон 5'
        return r_sector_name, row

    async def check_captcha(self, r, old_url, old_headers):
        if '<div class="CheckboxCaptcha" ' not in r.text:
            return r
        return await self.handle_smart_captcha(r.url, old_url, old_headers)

    async def handle_smart_captcha(self, url, old_url, old_headers):
        while True:
            r = await self.selenium_smart_captha(url)
            if not ('captcha' in r.url and len(r.url) > 200):
                break
        return r
        r = await self.selenium_smart_captha(url)
        # r = await self.session.get(old_url, headers=old_headers)
        return r

    async def selenium_smart_captha(self, url: str):
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument('--headless=new')
        driver = ProxyWebDriver(proxy=self.proxy, chrome_options=chrome_options)

        try:
            driver.get(url=url)
            await asyncio.sleep(1)
            r = await self.solve_smart_captcha_checkbox(driver)
            driver.get(url=r.url)
            r = await self.solve_smart_captcha_image(driver)
        except TimeoutException as e:
            raise ClientProxyConnectionError(e)
        except Exception as e:
            raise Exception(str(e))
        finally:
            driver.quit()
        return r

    async def solve_smart_captcha_checkbox(self, driver):
        body = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        ).get_attribute('innerHTML')

        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')

        data = {
            'rdata': r_data,
            'pdata': pdata
        }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'content-length': '5650',
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'afisha.yandex.ru',
            'origin': 'https://afisha.yandex.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        url = f'https://afisha.yandex.ru{href}'
        r = await self.session.post(url, timeout=10, headers=headers, data=data)
        return r

    async def solve_smart_captcha_image(self, driver):
        img_captha = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.AdvancedCaptcha-View img"))
        )
        img_captha_href = img_captha.get_attribute('src')

        img_captha_order = driver.find_element(By.CSS_SELECTOR, value='div.AdvancedCaptcha-SilhouetteTask canvas')
        img_captha_order.screenshot('afisha_catcha_order.png')

        textinstructions = driver.find_element(By.CSS_SELECTOR, value='span.Text').text

        r = await self.session.get(img_captha_href, stream=True)
        if r.status_code == 200:
            with open('afisha_catcha.png', 'wb') as f:
                f.write(r.content)


        with Image.open('afisha_catcha.png') as img:
            image_with_elements = img.convert('RGB')
            image_with_elements.save('afisha_catcha.jpg')
        with open('afisha_catcha.jpg', 'rb') as img:
            image_with_elements = base64.b64encode(img.read())
        with Image.open('afisha_catcha_order.png') as img:
            w, h = img.size
            area = (0, 0, w-399, 0)
            image_with_order = ImageOps.crop(img, area)
            image_with_order = image_with_order.convert('RGB')
            image_with_order.save('afisha_catcha_order.jpg')
        with open('afisha_catcha_order.jpg', 'rb') as img:
            image_with_order = base64.b64encode(img.read())

        coordinates = await async_captcha.yandex_afisha_coordinates_captha(image_with_elements,
                                                                           image_with_order,
                                                                           textinstructions)
        self.debug(coordinates)
       
        for coordinate in coordinates:
            actions = ActionChains(driver)
            img_captha = driver.find_element(By.CSS_SELECTOR, "div.AdvancedCaptcha-View img")
            x_offset = float(coordinate['x'])
            y_offset = float(coordinate['y'])
            # Получаем координаты верхнего левого угла элемента
            element_location = img_captha.location
            # Вычисляем смещение, чтобы переместиться в верхний левый угол
            xoffset = element_location['x']
            yoffset = element_location['y']
            actions.move_by_offset(xoffset, yoffset)
            actions.pause(1)
            actions.move_by_offset(x_offset, y_offset)
            actions.click().perform()
            actions.pause(1)
            actions.reset_actions()

        body = driver.find_element(By.CSS_SELECTOR, 'body').get_attribute('innerHTML')
        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')
        rep = driver.find_element(By.CSS_SELECTOR, 'input[name=rep]').get_attribute('value')

        data = {
            'rep': rep,
            'rdata': r_data,
            'pdata': pdata
            }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'content-length': '5650',
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'afisha.yandex.ru',
            'origin': 'https://afisha.yandex.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        url = f'https://afisha.yandex.ru{href}&rep={rep}'
        r = await self.session.post(url, timeout=10, headers=headers, data=data)

        if not '<div class="CheckboxCaptcha' in r.text:
            self.info(f'Yandex captcha success solved bro!')
        else:
            self.warning(f'Yandex captcha DIDNT solved!!!')
        return r

    async def hallplan_request(self, event_params, default_headers):
        if not self.session_key:
            self.session_key = event_params.get("session_id", '')
        url = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{self.session_key}/hallplan/async?clientKey={event_params["client_key"]}&req_number={self.req_number}'
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'connection': 'keep-alive',
            'host': 'widget.afisha.yandex.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        if not default_headers:
            default_headers = {}
        headers.update(default_headers)
        try:
            r = await self.session.get(url, headers=headers)
        except ClientPayloadError as ex:
            self.error(f"{url} {ex} failed to decode it! wrong sessinon_id or client_key")
            raise
        r = await self.check_captcha(r, url, headers)

        if 'result' not in r.text:
            self.info(f'[req_err] request doesnt contain result: {r.text[:400]}')
            return None, r
        if r.json()['status'] != 'success':
            self.info(f'[req_err] request status != success: {r.text[:400]}')
            return None, r
        if r.json()['result']['saleStatus'] in ['not-available', 'closed', 'no-seats']:
            return r.json()['result']['saleStatus'], r
        if 'hallplan' not in r.json()['result']:
            return None, r

        return r.json()['result']['hallplan']['levels'], r


    def get_regular_seats(self, a_sectors, r_sector, r_sector_name):
        for ticket in r_sector['seats']:
            if 'row' not in ticket['seat'] and 'place' not in ticket['seat']:  # Танцпол
                continue

            row = str(ticket['seat']['row'])
            seat = str(ticket['seat']['place'])
            price = int(float(ticket['priceInfo']['price']['value']) / 100)

            if 'Крокус Сити Холл' == self.venue:
                r_sector_name, row = self.reformat_sectors_crocus(row, seat, r_sector, r_sector_name)

            if 'Михайловский театр' == self.venue and 'Ложи бенуара' not in self.scheme.sector_names():
                row, seat, r_sector_name, price = self.reformat_sectors_mikhailovsky(row, seat, r_sector_name, price)

            for sector in a_sectors:
                if r_sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': r_sector_name,
                    'tickets': {(row, seat): price}
                })


    def get_admission_seats(self, a_sectors, r_sector, r_sector_name):
        if self.is_special_case():
            self.get_special_admission_seats(a_sectors, r_sector, r_sector_name)
            return None

        # """ Фанзона, Танцевальный партер """
        # available_seat_count = r_sector['availableSeatCount']
        # price = r_sector['prices'][0]
        # self.register_dancefloor(r_sector_name, price, available_seat_count)

    def get_special_admission_seats(self, a_sectors, r_sector, r_sector_name):
        available_seat_count = r_sector['availableSeatCount']
        sectors_max_seat_count = self.get_sector_max_seat_count()
        sector_num = [char for char in r_sector_name if char.isdigit()]
        sector_num = int(''.join(sector_num))

        if sector_num % 2 == 0:
            seat_range = range(1, available_seat_count + 1)
        else:
            seat_range = range(sectors_max_seat_count, 0, -1)

        for i, ticket in enumerate(r_sector['seats']):
            if not ticket['admission']:
                continue

            row = str(1)
            seat = str(seat_range[i])
            price = int(float(ticket['priceInfo']['price']['value']) / 100)

            for sector in a_sectors:
                if r_sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': r_sector_name,
                    'tickets': {(row, seat): price}
                })

    def is_special_case(self):
        if 'Барвиха' in self.venue:
            return True

        return False

    def get_sector_max_seat_count(self):
        if 'Барвиха' in self.venue:
            return 4
        return 4
    
    async def load_default_headers(self):
        r = await self.session.get(url=self.url, headers=self.headers)
        box = double_split(r.text, 'defaultHeaders":', '}')
        box = json.loads( box + '}')
        return box


    async def check_availible_seats_and_session_key(self, default_headers, event_params):
        headers2 = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "content-type": "application/json; charset=UTF-8",
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "timeout": "5000",
            "Referer": self.url.strip(),
            "Referrer-Policy": "no-referrer-when-downgrade",
            'user-agent': self.user_agent
        }
        headers2.update(default_headers)

        url2 = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{event_params["session_id"]}?clientKey={event_params["client_key"]}&req_number={self.req_number}'
        r2 = await self.session.get(url=url2, headers=headers2)
        self.req_number += 1
        
        try:
            self.session_key = r2.json()["result"]["session"]["key"]
        except:
            self.session_key = event_params["session_id"]

        if r2.json().get('status') != 'success':
            return False
        if r2.json()["result"]["session"]["saleStatus"] in ['not-available', 'closed', 'no-seats']:
            return False
        return True

    async def body(self):
        skip_events = [
            'https://widget.afisha.yandex.ru/w/sessions/MTE2NXwzODkxMzJ8Mjc4ODgzfDE2ODI2MTMwMDAwMDA%3D?widgetName=w2&lang=ru',  # ЦСКА — Ак Барс 27.04
        ]
        if self.url in skip_events:
            return None
        
        try:
            default_headers = await self.load_default_headers()
        except Exception as ex:
            default_headers = {}
            self.warning(f'if cannot load default_headers: eval(default_headers=dict()) {self.url} {ex}')
        else:
            self.debug(default_headers)

        event_params = eval(self.event_params)
        
        try:
            if_seats = await self.check_availible_seats_and_session_key(default_headers, event_params)
        except Exception as ex:
            self.error(f'Seats not found {self.url}')
            return
        else:
            if not if_seats:
                self.debug(f'Skip, no tickets, empty_seats{self.url}')
                return
            else:
                self.debug(f'find_tickets {self.url}')

        r_sectors = None
        r = None

        while self.req_number < 50 and r_sectors is None:
            try:
                await asyncio.sleep(0.2)
                r_sectors, r = await self.hallplan_request(event_params, default_headers)
            except ClientProxyConnectionError as ex:
                self.error(f'Catch(change_proxy): {ex} \n url:{self.url}')
                await self.change_proxy()
                await asyncio.sleep(1)
            except ClientPayloadError as ex:
                self.error(f"{self.url} {ex} failed to decode it! wrong sessinon_id or client_key")
                return
            except Exception as ex:
                self.error(f'Catch: {ex}; url:{self.url}')
                await asyncio.sleep(1)
            finally:
                self.req_number += 1
        if r_sectors == 'no-seats' or r_sectors == 'not-available' or r_sectors == 'closed':
            self.warning(f'No tickets {self.url} yandex_afisha this'
                         f'event dont have any tickets')
            return
        
        self.debug(f'Make requests count:{self.req_number}')

        if r is None:
            self.warning(f'try {self.req_number} requests without sucess')
            self.warning(f'Changing proxy... load 40..sec')
            self.req_number = 0
            self.default_headers = {}
            await self.change_proxy()
            await asyncio.sleep(40)
            
            while self.req_number < 50 and r_sectors is None:
                await asyncio.sleep(0.2)
                try:
                    r_sectors, r = await self.hallplan_request(event_params, default_headers)
                except ClientPayloadError as ex:
                    self.error(f"{self.url} {ex} failed to decode it! wrong sessinon_id or client_key")
                    return
                except Exception as ex:
                    self.error(f'Catch(2-nd while): {ex} url:{self.url}')
                finally:
                    self.req_number += 1
                if r_sectors == 'no-seats' or r_sectors == 'not-available' or r_sectors == 'closed':
                    self.warning(f'NO tickets {self.url} Yandex afisha this \
                                event dont have any tickets')
                    return
            self.debug(f'Make NEW requests count:{self.req_number}')

        if r_sectors is None:
            self.warning(f'NO tickets {self.url} Yandex afisha this event dont have any tickets')
            return 

        a_sectors = []
        for r_sector in r_sectors:
            r_sector_name = r_sector['name']
            admission = r_sector['admission']

            if not admission:
                self.get_regular_seats(a_sectors, r_sector, r_sector_name)
            else:
                self.get_admission_seats(a_sectors, r_sector, r_sector_name)

        self.reformat(a_sectors)

        for sector in a_sectors:
            #self.debug(sector['name'], len(sector['tickets']))
            self.register_sector(sector['name'], sector['tickets'])
        #self.check_sectors()
