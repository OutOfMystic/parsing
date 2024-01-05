from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils import utils


class AfishaRuSeats(AsyncSeatsParser):
    url_filter = lambda event: 'mapi.afisha.ru' in event
    proxy_check = SpecialConditions(url='https://www.afisha.ru/')
    
    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.reformat_dict = {
            #'Геликон-опера' Белоколонный зал княгини Шаховской 
            86090: {
                'Амфитеатр. Левая сторона': 'Амфитеатр, левая сторона',
                'Амфитеатр. Правая сторона': 'Амфитеатр, правая сторона'
                },
            }

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def load_scheme(self):
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "sec-ch-ua": "\"Not/A)Brand\";v=\"99\", \"Google Chrome\";v=\"115\", \"Chromium\";v=\"115\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "Referer": "https://www.afisha.ru/",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "x-application-key": self.XApplication,
            'User-Agent': self.user_agent
        }
        url_seats = f'https://mapi.afisha.ru/api/v21/hall/{self.sessionID}?withSubstrate=true'
        response = self.session.get(url_seats, headers=headers)

        try:
            resp = response.json()
        except:
            resp = False
        if not resp:
            self.change_proxy()
            raise RuntimeError(f' cannot load {self.url}')

        return response

    def get_price(self, scheme):
        dict_price = {}
        for i in scheme.json().get('levels'):
            if i.get('seatTypes'):
                for j in i.get('seatTypes'):
                    dict_price[j.get('id')] = int(j.get('price'))
        return dict_price

    def _reformat_gelicon(self, sector_name: str) -> str:
        if 'Стол' in sector_name:
            sector_name = sector_name.replace('№', '')
        elif 'Партер' in sector_name:
            sector_name = 'Партер'
        elif 'Амфитеатр' in sector_name and 'равая' in sector_name:
            sector_name = 'Амфитеатр, правая сторона'
        elif 'Амфитеатр' in sector_name and 'евая' in sector_name:
            sector_name = 'Амфитеатр, левая сторона'

        return sector_name

    def get_sectors(self, scheme, dict_price):
        dict_seats = {}
        for lvl in scheme.json().get('levels'):
            sector = lvl.get('name')
            id_scene = scheme.json().get("creationId")
            venue_name = scheme.json().get("name")
            if id_scene in self.reformat_dict:
                sector = self.reformat_dict.get(id_scene).get(lvl.get('name'))
                if not sector:
                    sector = lvl.get('name')
            elif venue_name in self.reformat_dict:
                sector = self.reformat_dict.get(venue_name).get(lvl.get('name'))
                if not sector:
                    sector = lvl.get('name')
            elif venue_name == 'Геликон-опера':
                sector = self._reformat_gelicon(sector)

            for row in lvl.get('rows'):
                row_num = row.get("number")
                for seat in row.get('seats'):
                    if seat.get("isAvailable"):
                        place = seat.get("number")
                        seatTypeId = seat.get("seatTypeId")
                        dict_seats.setdefault(sector, {}).update({
                            (row_num, place): dict_price.get(seatTypeId)
                            })
        return dict_seats

    async def body(self):
        scheme_json = self.load_scheme()
        if not scheme_json:
            self.warning(f'this event has empty json_file!{self.url} ')
            return False
        dict_price = self.get_price(scheme_json)
        a_sectors = self.get_sectors(scheme_json, dict_price)

        for sector, tickets in a_sectors.items():
            self.register_sector(sector, tickets)
