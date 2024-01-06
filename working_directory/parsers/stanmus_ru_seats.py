import json
from time import sleep

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.utils import utils


class StanmusParser(AsyncSeatsParser):
    event = 'stanmus.ru'
    url_filter = lambda url: 'stanmus.ru' in url
    proxy_check = NormalConditions()

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, sectors):
        for sector in sectors:
            if ' (ограниченная видимость)' in sector['name']:
                sector['name'] = sector['name'].replace(' (ограниченная видимость)', '')
            sector_name_l = sector['name'].lower()

            if 'ложа бенуар' in sector_name_l:

                reformatted_tickets = {}
                for row, seat in sector['tickets']:
                    reformatted_tickets[('1', seat)] = sector['tickets'][(row, seat)]

                sector['tickets'] = reformatted_tickets

                if '№' in sector_name_l:
                    lozha_num = sector_name_l.split('№')[-1]
                    sector['name'] = f'Ложа {lozha_num}'
                else:
                    # TODO протестировать "Ложа А" "Ложа Б" когда такие билеты с этих секторов появятся на сайте
                    lozha_sym = sector_name_l.split()[-1]

                    sector['name'] = f'Ложа {lozha_sym}'

    async def body(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'stanmus.ru',
            'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(self.url, headers=headers)

        count = 10
        if r.status_code != 200 and count > 0:
            self.error(f'Status code: {r.status_code} Cannot load {self.url} Sleep..')
            self.proxy = self.controller.proxy_hub.get(self.proxy_check)
            self.session = AsyncProxySession(self)
            sleep(60)
            count -= 1
            r = await self.session.get(self.url, headers=headers)
        try:
            seat_data = json.loads(double_split(r.text, 'window.seatData = ', '};') + '}')
        except Exception as ex:
            self.error(f'Status code:{r.status_code} Cannot load {r.text} {ex}')

        a_sectors = []
        for ticket in seat_data['rows']:
            sector_name = ticket['sector_name']
            row = str(ticket['row'])
            seat = str(ticket['seat'])
            price = int(float(ticket['price']))

            for sector in a_sectors:
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': ticket['sector_name'],
                    'tickets': {(row, seat): price}
                })

        self.reformat(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
