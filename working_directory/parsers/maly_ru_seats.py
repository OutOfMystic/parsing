from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split
from requests.exceptions import ProxyError


class MalyParser(SeatsParser):
    event = 'maly.ru'
    url_filter = lambda url: 'maly.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.event_id = None

    def before_body(self):
        self.session = ProxySession(self)
        self.event_id = self.url.split('=')[-1]

    def reformat(self, sectors):
        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ')
            sector_name_l = sector['name'].lower()

            if 'основная' in self.scene.lower():
                sector['name'] = sector['name'].replace('№ ', '№')
                sector['name'] = sector['name'].replace(' правая', ', правая').replace(' левая', ', левая')

                if 'ярус' in sector_name_l:
                    if 'балкон' in sector_name_l:
                        sector['name'] = sector['name'].replace('ярус', 'яруса')

                    if ' 1 ' in sector_name_l:
                        sector['name'] = sector['name'].replace(' 1 ', ' первого ')
                    elif ' 2 ' in sector_name_l:
                        sector['name'] = sector['name'].replace(' 2 ', ' второго ')

                elif 'ложа' in sector_name_l:
                    sec_name = 'unknown'
                    if 'бенуар' in sector_name_l:
                        sec_name = 'бенуара'
                    elif 'бельэтаж' in sector_name_l:
                        sec_name = 'бельэтажа'
                    elif 'ярус' in sector_name_l:
                        sec_name = 'первого яруса'

                    side = 'unknown'
                    if 'левая' in sector_name_l:
                        side = 'левая сторона'
                    elif 'правая' in sector_name_l:
                        side = 'правая сторона'

                    num = sector["name"].split()[-3].replace(',', '')

                    sector['name'] = f'Ложа {sec_name} {num}, {side}'

            elif 'ордынк' in self.scene.lower():
                sector['name'] = sector['name'].replace('1-го', '1')

                if 'ложа' in sector_name_l:
                    number = sector_name_l.split('№')[-1]
                    side = 'левая' if 'лев' in sector_name_l else 'правая'

                    if 'ложа 1-го яруса' in sector_name_l:
                        sec_name = 'балкона'
                    elif 'бенуара' in sector_name_l:
                        sec_name = 'бенуара'
                    elif 'бельэтажа' in sector_name_l:
                        sec_name = 'бельэтажа'
                    else:
                        sec_name = 'unregistered'

                    sector['name'] = f'Ложа {sec_name} {number} {side} сторона'

    def get_csrf(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
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

    def body(self):
        for _ in range(10):
            csrf = self.get_csrf()
            if csrf is not None:
                break
        else:
            self.bprint(f'error maly.ru seats: csrf_token is None {self.url = }')
            return
        occupied_ticket_ids = self.get_occupied_ticket_ids(csrf)

        url = 'http://www.maly.ru/halls/event-hall-scheme'
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

        r = self.session.post(url, data=data, headers=headers)

        seat_data = r.json()['seats']

        a_sectors = []
        for ticket in seat_data:
            if ticket['id'] in occupied_ticket_ids:
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

        self.reformat(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
