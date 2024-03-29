from requests.exceptions import TooManyRedirects

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.manager.proxy.sessions import AsyncProxySession


class SochiCirkParser(AsyncSeatsParser):
    proxy_check = NormalConditions()
    url_filter = lambda url: 'ticket-place.ru' in url and 'sochi' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.url = self.url[:self.url.index('|')]

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def get_all_seats(self):
            headers = {
                    'accept': 'application/json, text/plain, */*',
                    'accept-encoding': 'gzip, deflate, br',
                    'accept-language': 'ru,en;q=0.9',
                    'cache-control': 'no-cache',
                    'connection': 'keep-alive',
                    'host': 'ticket-place.ru',
                    'pragma': 'no-cache',
                    'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': self.user_agent
                }
            try:
                r1 = await self.session.get(self.url,  headers=headers)
            except TooManyRedirects:
                self.error('TooManyREdirects')
            return r1.json()
    
    @staticmethod
    def reformat_sector(sector):
        return sector

    def make_a_seats(self, all_place):
        a_sectors = {}
        for place in all_place:
            if place.get("status") == "free":
                try:
                    sector = self.reformat_sector(place["sector_name"])
                    row = str(place['row_sector'])
                    seat = str(place['seat_number'])
                    price = place['price']
                    a_sectors.setdefault(sector, {}).update({
                        (row, seat): price
                    })
                except KeyError:
                    continue
        return a_sectors

    async def body(self):
        
        all_place = await self.get_all_seats()
        all_place = all_place['data']['seats']['data']

        a_sectors = self.make_a_seats(all_place)

        for sector, tickets in a_sectors.items():
            #self.info(sector, len(tickets))
            self.register_sector(sector, tickets)
        #self.check_sectors()


class SaratovCirkParser(SochiCirkParser):
    url_filter = lambda url: 'ticket-place.ru' in url and 'saratov' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.a_sectors = []

    @staticmethod
    def reformat_sector(sector):
        if 'левая сторона' in sector.lower():
            sector = 'Левая сторона'
        elif 'правая сторона' in sector.lower():
            sector = 'Правая сторона'
        return sector

    async def body(self):
        await super().body()


class VladivostokCirkParser(SochiCirkParser):
    url_filter = lambda url: 'ticket-place.ru' in url and 'vladiv' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.a_sectors = []

    @staticmethod
    def reformat_sector(sector):
        if 'Центральная ложа' in sector:
             sector = 'Ложа 1'
        elif 'Правая ложа' in sector:
             sector = 'Ложа 2'
        elif 'Левая ложа' in sector:
             sector = 'Ложа 3'
        return sector

    async def body(self):
        await super().body()


class SamaraCirkParser(SochiCirkParser):
    url_filter = lambda url: 'ticket-place.ru' in url and 'samara' in url
    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.a_sectors = []
    @staticmethod
    def reformat_sector(sector):
        if 'сторона' in sector:
            place_orientation, sector_name_and_number = sector.split(',')
            sector_name, sector_number = sector_name_and_number.split()
            sector = f'{sector_number} {sector_name}'
        return sector
    async def body(self):
        await super().body()

