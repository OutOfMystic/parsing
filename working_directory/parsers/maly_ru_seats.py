import re

from requests.exceptions import ProxyError

from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class MalyParser(SeatsParser):
    event = 'maly.ru'
    url_filter = lambda url: 'maly.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = None
        if 'buy-tickets' in self.url:
            self.event_id = self.url.split('/')[-1]
        elif 'select-seat' in self.url:
            self.event_id = self.url.split('=')[-1]

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, sectors):
        if self.name_of_scene == 'Историческая сцена':
            for sector in sectors:
                sector_name = sector['name']

                if 'Ложа' in sector_name and 'бельэтажа' in sector_name:
                    number = re.search(r'(\d)', sector_name).group()
                    position = 'правая' if 'правая' in sector_name else 'левая'
                    sector_name = f'Ложа бельэтажа №{number}, {position} сторона'
                
                elif 'Ложа' in sector_name and 'бенуара' in sector_name:
                    number = re.search(r'(\d)', sector_name).group()
                    position = 'правая' if 'правая' in sector_name else 'левая'
                    sector_name = f'Ложа бенуара №{number}, {position} сторона'
                
                elif 'Ложа' in sector_name and 'яруса' in sector_name:
                    number = re.search(r'№ *(\d)', sector_name).groups()[0]
                    position = 'правая' if 'правая' in sector_name else 'левая'
                    sector_name = f'Ложа первого яруса №{number}, {position} сторона'
                
                elif 'Балкон' in sector_name:
                    number = int(re.search(r'\d', sector_name).group())
                    if number == 1:
                        sector_name = 'Балкон первого яруса'
                    elif number == 2:
                        sector_name = 'Балкон второго яруса'
                
                sector['name'] = sector_name
        elif self.name_of_scene == 'Сцена на Большой Ордынке':
            for sector in sectors:
                sector_name = sector['name']

                if 'Ложа' in sector_name and 'бельэтажа' in sector_name:
                    number = re.search(r'(\d)', sector_name).group()
                    position = 'правая' if 'правая' in sector_name else 'левая'
                    sector_name = f'Ложа бельэтажа {number} {position} сторона'
                
                elif 'Ложа' in sector_name and 'бенуара' in sector_name:
                    number = re.search(r'(\d)', sector_name).group()
                    position = 'правая' if 'правая' in sector_name else 'левая'
                    sector_name = f'Ложа бенуара {number} {position} сторона'
                
                elif 'Ложа' in sector_name and 'яруса' in sector_name:
                    number = re.search(r'№ *(\d)', sector_name).groups()[0]
                    position = 'правая' if 'правая' in sector_name else 'левая'
                    sector_name = f'Ложа балкона {number} {position} сторона'
                
                elif 'Балкон' in sector_name:
                    number = int(re.search(r'\d', sector_name).group())
                    if number == 1:
                        sector_name = 'Балкон 1 яруса'
                
                sector['name'] = sector_name

    def get_csrf(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'www.maly.ru',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        if r.status_code == 407:
            raise ProxyError(f'{r.status_code = }, {self.proxy.args = }')
        try:
            csrf = double_split(r.text, 'name="csrf-token" content="', '"')
        except IndexError:
            return None
        return csrf

    def get_occupied_ticket_ids(self, csrf):
        url = f'http://www.maly.ru/halls/occupied-seats?event_id={self.event_id}'
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
            'host': 'www.maly.ru',
            'referer': 'http://www.maly.ru/checkout/select-seat?event_id=10157',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest',
            'x-csrf-token': csrf
        }
        r = self.session.get(url, headers=headers)
        return r.json()

    def _get_sectors_data(self, seat_data, occupied_ticket_ids=None):
        a_sectors = []
        for ticket in seat_data:
            if occupied_ticket_ids:
                if ticket['id'] in occupied_ticket_ids:
                    continue
            else:
                if int(ticket['unavailable']) == 1:
                    continue

            sector_name = ticket['areaTitle']
            row = str(ticket['row'])
            seat = str(ticket['seat'])
            price = int(float(ticket['price']))

            for sector in a_sectors:
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': ticket['areaTitle'],
                    'tickets': {(row, seat): price}
                })
        return a_sectors

    def body(self):
        for _ in range(10):
            csrf = self.get_csrf()
            if csrf is not None:
                break
        else:
            self.error(f'error maly.ru seats: csrf_token is None {self.url = }')
            return

        if 'select-seat' in self.url:
            occupied_ticket_ids = self.get_occupied_ticket_ids(csrf)
            headers = {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'connection': 'keep-alive',
                'content-length': '117',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'host': 'www.maly.ru',
                'origin': 'http://www.maly.ru',
                'referer': self.url,
                'user-agent': self.user_agent,
                'x-requested-with': 'XMLHttpRequest',
                'x-csrf-token': csrf
            }
            data = {
                'event_id': self.event_id,
                'lang': 'ru',
                '_csrf': csrf
            }
            url = 'http://www.maly.ru/halls/event-hall-scheme'
            r = self.session.post(url, data=data, headers=headers, verify=False)
            seat_data = r.json()['seats']
            self.name_of_scene = 'Историческая сцена'
            a_sectors = self._get_sectors_data(seat_data, occupied_ticket_ids)

        elif 'buy-tickets' in self.url:
            headers = {'user-agent': self.user_agent}
            params = {'id': self.event_id}
            url = 'http://maly.core.ubsystem.ru/uiapi/event/scheme'
            r = self.session.get(url, params=params, headers=headers, verify=False)
            seat_data = r.json()['seats']
            a_sectors = self._get_sectors_data(seat_data)
            
            try:
                response = self.session.get(f'https://maly.core.ubsystem.ru/uiapi/event/{self.event_id}', headers=headers)
                self.name_of_scene = response.json()['hallScheme']['hall']['title']
            except Exception:
                raise Exception('Cannot find hallScheme, name_of_scene')

        else:
            a_sectors = []
            self.error("Url dont have 'select-seat' or 'buy-tickets' INCORRECT REQUESTS ")

        self.reformat(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
