import re
import json
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils import utils


class HcLadaHockeyTLTarena_seats(AsyncSeatsParser):
    event = 'tickets.tlt-arena.ru'
    url_filter = lambda url: 'tickets.tlt-arena.ru' in url
 
    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 3200
        self.driver_source = None
        self.event_id_ = self.url.split('/')[-1]
       
    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def double_split(source, lstr, rstr, x=1, n=0):
        # Возвращает n-ый эелемент
        SplPage = source.split(lstr, x)[n + 1]
        SplSplPage = SplPage.split(rstr)[0]
        return SplSplPage

    @staticmethod
    def reformat_sector(sector):
        return sector
        
    async def get_seats_list(self, url):
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': self.user_agent
        }
        r1 = await self.session.get(url=url, headers=headers, ssl=False)
        zones = self.double_split(r1.text, 'CORE.data.zones = ', ';')
        json_data = json.loads(zones)
        ids = [i.get('id') for i in json_data]
        return ids
    
    async def make_zones_dict(self, id):
        url = f'https://tickets.tlt-arena.ru/seats-list/{self.event_id_}/{id}'
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "sec-ch-ua": "\"Chromium\";v=\"118\", \"Google Chrome\";v=\"118\", \"Not=A?Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
            "Referer": self.url,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': self.user_agent
            }   
        r = await self.session.get(url=url, headers=headers, ssl=False)

        self.prices.update(
            {i["pricezoneId"]: i["value"] for i in r.json()['prices']}
        )

        for place_info in r.json()["seats"]:
            sector, row, place = re.findall(r'(\w+ \d+)', place_info.get('name'))
            row = str(row.split()[-1])
            place = str(place.split()[-1])
            price = int(float(self.prices.get(place_info.get("pricezoneId"), 500)))

            self.a_sectors.setdefault(sector, {}).update({
                (row, place) : price
            })

    async def body(self):
        all_zones = await self.get_seats_list(self.url)
        self.prices = {}
        self.a_sectors = {}

        for zone in all_zones:
            await self.make_zones_dict(zone)
        
        for sector, tickets in self.a_sectors.items():
            self.register_sector(sector, tickets)
