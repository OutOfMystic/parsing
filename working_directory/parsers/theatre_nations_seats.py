from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.coroutines import AsyncSeatsParser

class NationsParser(AsyncSeatsParser):
    event = 'theatreofnations.ru'
    url_filter = lambda url: 'theatreofnations.ru' in url
    proxy_check = SpecialConditions(url='https://theatreofnations.ru/events/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 900
        self.driver_source = None
        self.event_id = None

    async def before_body(self):
        self.session = AsyncProxySession(self)
        self.event_id = self.url.split('/')[-2]

    def reformat(self, a_sectors):
        for sector in a_sectors:
            sector['name'] = sector['name'].replace(' (неудобное место)', '').capitalize()

    def _reformat(self, sector_name: str, place_row: str) -> tuple[str, str]:
        if 'Партер' in sector_name:
            sector_name = 'Партер'
        elif 'Места за креслами' in sector_name:
            sector_name = 'Места за креслами'
        elif 'Ложи бельэтажа' in sector_name:
            place_row = sector_name.split('№')[1].split()[0]
            place_row = 'Ложа ' + place_row
            sector_name = 'Бельэтаж'
        elif '1 яруса' in sector_name:
            place_row = sector_name.split('№')[1].split()[0]
            place_row = 'Ложа ' + place_row
            sector_name = '1 ярус'
        elif '2 яруса' in sector_name:
            place_row = sector_name.split('№')[1].split()[0]
            place_row = 'Ложа ' + place_row
            sector_name = '2 ярус'
        elif '3 яруса' in sector_name:
            place_row = sector_name.split('№')[1].split()[0]
            place_row = 'Ложа ' + place_row
            sector_name = '3 ярус'
        elif '4 яруса' in sector_name:
            place_row = sector_name.split('№')[1].split()[0]
            place_row = 'Ложа ' + place_row
            sector_name = '4 ярус'
        elif 'БАЛКОН 3 ЯРУСА' in sector_name:
            sector_name = 'Балкон 3го яруса'
        elif 'Царская ложа' == sector_name:
            place_row = '1'

        return sector_name, place_row

    def get_tickets(self):
        url = ("https://theatreofnations.ru/api/places/?nombilkn="
               f"{self.event_id}&cmd=get_hall_and_places&early_access=")
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,de;q=0.6',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'theatreofnations.ru',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = self.session.get('https://theatreofnations.ru/api/token_places/', headers=headers)
        headers['authorization'] = r.text
        r = self.session.get(url, headers=headers)
        seats = r.json()['EvailPlaceList']
        a_sectors = []
        for seat in seats:
            sector = seat['name_sec'].replace('Ложа', 'Ложи')
            row = seat['row']
            seat_num = seat['seat']
            price = seat['Price'].split('.')[0]
            sector, row = self._reformat(sector, str(row))
            formatted = {
                'name': sector,
                'seat': str(seat_num),
                'row': row,
                'price': int(price),
            }
            a_sectors.append(formatted)
        return a_sectors

    async def body(self):
        a_sectors = []
        tickets = self.get_tickets()
        for ticket in tickets:

            sector_name = ticket['name']
            row = str(ticket['row'])
            seat = str(ticket['seat'])
            price = ticket['price']

            for sector in a_sectors:
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': sector_name,
                    'tickets': {(row, seat): price}
                })

        self.reformat(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
