import time

from requests.exceptions import ProxyError
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from parse_module.utils.captcha import image
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.drivers.proxelenium import ProxyWebDriver


class YandexAfishaParser(SeatsParser):
    proxy_check_url = 'https://afisha.yandex.ru/'
    event = 'afisha.yandex.ru'
    url_filter = lambda url: 'afisha.yandex.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, sectors):
        if 'ВТБ Арена' in self.venue:
            for sector in sectors:
                if 'Сектор C204' == sector['name']:
                    ...
                    # sector['name'] = 'Сектор C204 GOLD'
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

    def check_captcha(self, r, old_url, old_headers):
        if '<div class="CheckboxCaptcha" ' not in r.text:
            return r
        return self.handle_smart_captcha(r.url, old_url, old_headers)

    def handle_smart_captcha(self, url, old_url, old_headers):
        r = self.selenium_smart_captha(url)
        # r = self.session.get(old_url, headers=old_headers)
        return r

    def selenium_smart_captha(self, url: str):
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument('--headless=new')
        driver = ProxyWebDriver(proxy=self.proxy, chrome_options=chrome_options)

        try:
            driver.get(url=url)
            time.sleep(1)
            r = self.solve_smart_captcha_checkbox(driver)
            driver.get(url=r.url)
            r = self.solve_smart_captcha_image(driver)
        except TimeoutException as e:
            self.bprint('Яндекс капча не пройдена: что-то не работает')
            raise ProxyError(e)
        finally:
            driver.quit()
        return r

    def solve_smart_captcha_checkbox(self, driver):
        body = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        ).get_attribute('innerHTML')

        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        aes_key = driver.find_element(By.CSS_SELECTOR, 'input[name=aesKey]').get_attribute('value')
        sign_key = driver.find_element(By.CSS_SELECTOR, 'input[name=signKey]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')

        data = {
            'rdata': r_data,
            'aesKey': aes_key,
            'signKey': sign_key,
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
        r = self.session.post(url, timeout=10, headers=headers, data=data)
        return r

    def solve_smart_captcha_image(self, driver):
        img_captha = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.AdvancedCaptcha-View img"))
        )
        img_captha_href = img_captha.get_attribute('src')

        r = self.session.get(img_captha_href, stream=True)
        if r.status_code == 200:
            with open('afisha_catcha.png', 'wb') as f:
                for chunk in r:
                    f.write(chunk)

        with open('afisha_catcha.png', 'rb') as img:
            word_from_img = image(file=img)

        body = driver.find_element(By.CSS_SELECTOR, 'body').get_attribute('innerHTML')
        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        aes_key = driver.find_element(By.CSS_SELECTOR, 'input[name=aesKey]').get_attribute('value')
        sign_key = driver.find_element(By.CSS_SELECTOR, 'input[name=signKey]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')

        data = {
            'rep': word_from_img,
            'rdata': r_data,
            'aesKey': aes_key,
            'signKey': sign_key,
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
        url = f'https://afisha.yandex.ru{href}&rep={word_from_img}'
        r = self.session.post(url, timeout=10, headers=headers, data=data)
        return r

    def hallplan_request(self, event_params, count_req):
        url = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{event_params["session_id"]}/hallplan/async?clientKey={event_params["client_key"]}&req_number={count_req}'
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
        r = self.session.get(url, headers=headers)
        r = self.check_captcha(r, url, headers)

        if 'result' not in r.text:
            self.bprint(f'[req_err] request doesnt contain result: {r.text[:400]}')
            return None
        if r.json()['status'] != 'success':
            self.bprint(f'[req_err] request status != success: {r.text[:400]}')
            return None
        if 'hallplan' not in r.json()['result']:
            return None

        return r.json()['result']['hallplan']['levels']

    def get_regular_seats(self, a_sectors, r_sector, r_sector_name):
        for ticket in r_sector['seats']:
            if 'row' not in ticket['seat'] and 'place' not in ticket['seat']:  # Танцпол
                continue

            row = str(ticket['seat']['row'])
            seat = str(ticket['seat']['place'])
            price = int(float(ticket['priceInfo']['price']['value']) / 100)

            if 'Крокус Сити Холл' == self.venue:
                r_sector_name, row = self.reformat_sectors_crocus(row, seat, r_sector, r_sector_name)

            if 'Михайловский театр' == self.venue:
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

    def body(self):
        skip_events = [
            'https://widget.afisha.yandex.ru/w/sessions/MTE2NXwzODkxMzJ8Mjc4ODgzfDE2ODI2MTMwMDAwMDA%3D?widgetName=w2&lang=ru',  # ЦСКА — Ак Барс 27.04
        ]

        if self.url in skip_events:
            return None

        count_requests = 0
        r_sectors = None
        event_params = eval(self.event_params)
        while count_requests < 50 and r_sectors is None:
            r_sectors = self.hallplan_request(event_params, count_requests)
            count_requests += 1
            time.sleep(2)

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
            self.register_sector(sector['name'], sector['tickets'])
