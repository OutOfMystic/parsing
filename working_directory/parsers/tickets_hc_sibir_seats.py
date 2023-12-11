import re
import json
from time import sleep

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils

class Hc_Sibir_Seats(SeatsParser): 
    event = 'tickets.hcsibir.ru'
    url_filter = lambda url: 'tickets.hcsibir.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 3200
        self.driver_source = None
        self.event_id = self.url.split('/')[-1]
       
    def before_body(self):
        self.session = ProxySession(self)

    @staticmethod
    def get_row_and_place(info: str):
        if 'Ресторан' in info:
            #Ресторан Стол 1 Место 1
            sector = 'Ресторан'
            row = re.search(r'(?:Стол ?)(\d+)', info).group(1)
            seat = re.search(r'(?:Место ?)(\d+)', info).group(1)
            return sector, str(seat), str(row)
        else:
            #"Сектор E10 Ряд 1 Место 7"
            sector = re.search(r'^.+(?=Ряд)', info)[0].strip()
            row = re.search(r'(?:Ряд ?)(\d+)', info).group(1)
            seat = re.search(r'(?:Место ?)(\d+)', info).group(1)
            return sector, str(row), str(seat)

    def set_cookies(self):
        headers1 = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "User-Agent": self.user_agent
        }
        self.session.get(url=self.url, headers=headers1, verify=False)

    def get_availible_ids(self):
        url_zones = f"https://tickets.hcsibir.ru/zones-list/{self.event_id}"
        headers2 = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
            "Referer": self.url,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "User-Agent": self.user_agent
        }
        availible_zones_json = self.session.get(url=url_zones, headers=headers2, verify=False)
        availible_zones = [ i.get('id') for i in availible_zones_json.json()["zones"]]
        return availible_zones # ['153522', '153851', '154280', '154609', '154886', ...]

    @staticmethod
    def double_split(source, lstr, rstr, x=1, n=0):
        # Возвращает n-ый эелемент
        SplPage = source.split(lstr, x)[n + 1]
        SplSplPage = SplPage.split(rstr)[0]
        return SplSplPage

    def load_seats_from_zones(self, sectors_ids):
        a_tickets = {}
        all_price_zones = {}
        for id_sector in sectors_ids:
            try:
                #sleep(0.2)
                seats_sector = f'https://tickets.hcsibir.ru/seats-list/{self.event_id}/{id_sector}'
                choose_seats = f"https://tickets.hcsibir.ru/choose-seats/{self.event_id}/{id_sector}"
                headers3 = {
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.9,ru;q=0.8",
                    "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "x-requested-with": "XMLHttpRequest",
                    "Referer": choose_seats,
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                    "User-Agent": self.user_agent
                }
                price_zones = self.session.get(url=choose_seats, headers=headers3, verify=False)
                price_zones.encoding = 'utf-8'

                zones_txt = self.double_split(price_zones.text,'CORE.data.prices = ', ';')
                price_zones = json.loads(zones_txt)
                for zones in price_zones:
                    all_price_zones.setdefault(zones.get('pricezoneId') , int(float(zones.get('value'))))

                ticktes_all = self.session.get(url=seats_sector, headers=headers3, verify=False)

                for i in ticktes_all.json()['seats']:
                    sector, row, seat = self.get_row_and_place(i.get("name"))
                    price = all_price_zones.get(i.get("pricezoneId"), 500)
                    a_tickets.setdefault(sector, {}).update({
                        (row, seat): price
                    })
            except Exception as ex:
                self.error(f'{ex} error with parsin sector -> SIBIR ARENA')
        return a_tickets
    
    @staticmethod
    def reformat_sector(sector):
        return sector
        
    def body(self) -> None:
        self.set_cookies()    

        availible_zones = self.get_availible_ids()
        a_sectors = self.load_seats_from_zones(availible_zones)
    
        for sector, tickets in a_sectors.items():
            #sector = self.reformat_sector(sector)
            self.register_sector(sector, tickets)
        #self.check_sectors()
    