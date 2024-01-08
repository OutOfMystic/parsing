import re
from time import sleep

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class Hc_Avtomobilist_Seats(AsyncSeatsParser):
    event = 'tickets.hc-avto.ru'
    url_filter = lambda url: 'tickets.hc-avto.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 3200
        self.driver_source = None
        self.id = self.url.split('/')[-1]
       
    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def get_row_and_place(info: str):
        #"Сектор Г Ряд 4 Место 2"
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
        self.session.get(url=self.url, headers=headers1)

    def get_availible_ids(self):
        url_zones = f"https://tickets.hc-avto.ru/zones-list/{self.id}"
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
        availible_zones_json = self.session.get(url=url_zones, headers=headers2)
        availible_zones = [ i.get('id') for i in availible_zones_json.json()["zones"]]
        return availible_zones # ['52288', '52543', '52863', ...]

    def load_seats_from_zones(self, sectors_ids):
        a_sectors = {}
        for id_sector in sectors_ids:
            sleep(0.3)
            url_sector = f"https://tickets.hc-avto.ru/seats-list/{self.id}/{id_sector}"
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
                "Referer": url_sector,
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "User-Agent": self.user_agent
            }
            test = self.session.get(url = url_sector, headers=headers3)
            if test.headers['Content-Type'] == 'application/json':
                price_dict = {i.get("pricezoneId"): int(float(i.get("value"))) for i in test.json()["prices"]}
                for place in test.json()["seats"]:
                    price = price_dict.get(place["pricezoneId"])
                    sector, row, place = self.get_row_and_place(place.get("name"))
                    a_sectors.setdefault(sector, {}).update({
                        (row, place): price
                    })
            else:
                continue
        return a_sectors
    
    @staticmethod
    def reformat_sector(sector):
        if 'Б-н' in sector:
            sector = sector.replace('Б-н', 'Балкон')
        return sector
        
    async def body(self):
        self.set_cookies()    

        availible_zones = self.get_availible_ids()
        a_sectors = self.load_seats_from_zones(availible_zones)

        for sector, tickets in a_sectors.items():
            sector = self.reformat_sector(sector)
            self.register_sector(sector, tickets)
        #self.check_sectors()
    
