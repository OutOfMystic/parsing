from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.utils.captcha import yandex_smart_captcha


class OperettaParser(AsyncSeatsParser):
    event = 'mosoperetta.ru'
    url_filter = lambda event: 'mosoperetta.ru' in event

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 4800
        self.driver_source = None

        self.csrf = ''

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, a_sectors, place_name):
        operetta_reformat_dict = {
            '': 'Партер',
            '': 'Ложа бенуара №1',
            '': 'Ложа бенуара №2',
            '': 'Ложа бенуара №3',
            '': 'Ложа бенуара №4',
            '': 'Ложа бенуара №5',
            '': 'Ложа бенуара №6',
            '': 'Ложа бенуара №7',
            '': 'Ложа бенуара №8',
            '': 'Амфитеатр',
            '': 'Балкон',
            '': 'Бельэтаж',
            '': 'Ложа бельэтажа №1',
            '': 'Ложа бельэтажа №2',
        }

        ref_dict = {}
        ref_dict = operetta_reformat_dict

        for sector in a_sectors:
            sector['name'] = ref_dict.get(sector['name'], sector['name'])

    async def get_event_data(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://mosoperetta.ru/afisha/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(self.url, headers=headers, verify=False)

        count = 8
        while not r.ok and count > 0:
            self.debug(f'{self.proxy.args = }, {self.session.cookies = } mosoperetta 505 bad gateway')
            self.proxy = self.controller.proxy_hub.get(self.proxy_check)
            self.session = AsyncProxySession(self)
            r = await self.session.get(self.url, headers=headers, verify=False)
            count -= 1

        sitekey = double_split(r.text, 'data-sitekey="', '"')

        tries = 0
        token = None
        while not token:
            token = yandex_smart_captcha(sitekey, self.url, print_logs=False)

            if tries >= 3:
                raise RuntimeError('[operetta_seats]: no token for yandex captcha')

            tries += 1

        headers = {
            'Host': 'mosoperetta.ru',
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Content-Length': '284',
            'Origin': 'https://mosoperetta.ru',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': self.url,
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'TE': 'trailers',
        }
        data = {
            'smart-token': token,
        }

        r = await self.session.post(self.url, headers=headers, data=data, verify=False)
        try:
            svg_url = double_split(r.text, "url_svg = '", "'")
        except:
            self.error('svg_url cannot be got {r.status_code}')
        seats_url = 'https://mosoperetta.ru' + double_split(r.text, "var checkTSR = '", "'")

        return seats_url

    async def get_a_sector_seats(self, seats_url):
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        url = seats_url
        r = await self.session.get(url, headers=headers, verify=False)
        if not r.json().get('FreePlacesQty'):
            return []

        a_seats = []
        for seat in r.json()['hall_tooltips'].values():
            if 'tooltip' not in seat:
                continue

            if seat.get('disabled', False):
                continue

            f_seat = {
                'row': seat['attr']['row'],
                'place': seat['attr']['seat']
            }
            sector = double_split('[s_k]' + seat['tooltip'], '[s_k]', '<br')
            price = double_split(seat['tooltip'], 'Цена: ', ' р.').replace(' ', '')
            f_seat['sector'] = sector
            f_seat['price'] = price

            a_seats.append(f_seat)

        return a_seats

    async def body(self):
        seats_url = await self.get_event_data()
        seats = await self.get_a_sector_seats(seats_url)

        a_sectors = []
        for ticket in seats:
            row = str(ticket['row'])
            seat = str(ticket['place'])
            price = int(float(ticket['price']))
            for sector in a_sectors:
                if ticket['sector'] == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': ticket['sector'],
                    'tickets': {(row, seat): price}
                })

        self.reformat(a_sectors, self.venue)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])

