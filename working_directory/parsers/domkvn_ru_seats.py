import re

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils

class KVNParser(SeatsParser):
    event = 'domkvn.ru'
    url_filter = lambda url: 'domkvn' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 3600
        self.driver_source = None
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "Referer": "https://domkvn.ru/",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': self.user_agent
        }
    
    def before_body(self):
        self.session = ProxySession(self)

    @staticmethod
    def reformat_sector(sector_name, row):
        sector_name2 = None
        reformat_dict = {
            'VIP Партер Левая часть': 'VIP партер 3',
            'VIP Партер Правая часть': 'VIP партер 1',
            'VIP Партер Середина': 'VIP партер 2',
            'Балкон Левая часть': 'Балкон 5',
            'Балкон Левая часть зала': 'Балкон 5',
            'Балкон Левая часть центра зала': 'Балкон 4',
            'Балкон Правая часть центра зала': 'Балкон 2',
            'Балкон Правая часть': 'Балкон 1',
            'Балкон Правая часть зала': 'Балкон 1',
            'Балкон Середина': 'Балкон 3',
            'Бельэтаж Левая часть': 'Бельэтаж 5',
            'Бельэтаж Левая часть зала': 'Бельэтаж 5',
            'Бельэтаж Левая часть центра зала': 'Бельэтаж 4',
            'Бельэтаж Середина': 'Бельэтаж 3',
            'Бельэтаж Правая часть центра зала': 'Бельэтаж 2',
            'Бельэтаж Правая часть': 'Бельэтаж 1',
            'Бельэтаж Правая часть зала': 'Бельэтаж 1',
            'Левая ложа бельэтажа': 'Левая ложа бельэтажа',
            'Правая ложа бельэтажа': 'Правая ложа бельэтажа'
        }

        if sector_name in reformat_dict:
            sector_name = reformat_dict.get(sector_name)
        
        elif sector_name == 'Партер Левая часть':
            if int(row) >= 9:
                sector_name = 'Партер 8'
                sector_name2 = 'Партер 7'
            else:
                sector_name = 'Партер 3'
        elif sector_name == 'Партер Середина':
            if int(row) >= 9:
                sector_name = 'Партер 6'
            else:
                sector_name = 'Партер 2'
        elif sector_name == 'Партер Правая часть':
            if int(row) >= 9:
                sector_name = 'Партер 4'
                sector_name2 = 'Партер 5'
            else:
                sector_name = 'Партер 1'

        return sector_name, sector_name2
    
    
    def body(self):
        r2 = self.session.get(url=self.url, headers=self.headers)

        sectors = r2.json().get('sectors')
        sectors_ids = [i.get('id') for i in sectors]
        scheme_id = re.search(r'(?<=id\=)\d+', self.url)[0]
        
        a_sectors = {}
        for sector_id in sectors_ids:
            try :
                url_to_sector = f"https://core.domkvn.ubsystem.ru/uiapi/event/scheme?id={scheme_id}&sector_id={sector_id}"
                r3 = self.session.get(url=url_to_sector, headers=self.headers)
                seats = r3.json().get('seats')
                
                for seat in seats:
                    if seat.get('unavailable') == 0:
                        row = str(seat.get('row'))
                        place = str(seat.get('seat'))
                        price = int(seat.get('price'))
                        sector, sector_2 = self.reformat_sector(seat.get("areaTitle"), row)

                        a_sectors.setdefault(sector, {}).update({
                            (row, place) : price
                        })
                        if sector_2:
                            a_sectors.setdefault(sector_2, {}).update({
                            (row, place) : price
                        })
            except Exception as ex:
                self.warning(f'{self.url} {ex}')

        for sector_name, tickets in a_sectors.items():
            self.register_sector(sector_name, tickets)