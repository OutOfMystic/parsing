import json

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split, lrsplit
import codecs


class InticketsParser(AsyncSeatsParser):
    event = 'intickets.ru'
    url_filter = lambda url: 'intickets.ru' in url and 'pre8136' not in url
    proxy_check = SpecialConditions(url='https://iframeab-pre4073.intickets.ru/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, sectors):
        for sector in sectors:
            pass

    def decode_unicode_escape(self, text):
        return codecs.decode(text.encode('UTF-8'), 'unicode-escape')

    async def body(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r_text = await self.session.get_text(self.url, headers=headers, verify_ssl=False)

        if 'Билетов больше нет' in r_text:
            return False

        sectors_data = double_split(r_text, '"schemaSectorArr":', '}') + '}'
        sectors_data = self.decode_unicode_escape(sectors_data)
        sectors_data = json.loads(sectors_data)

        # data-seat="269034554|22|1|1500|11370050"
        # [0] - ticket_id, [1] - row, [2] - seat, [3] - price, [4] - sector_id
        tickets_data = [ticket_str.split('|') for ticket_str in lrsplit(r_text, 'data-seat="', '"')]

        a_sectors = []
        for ticket in tickets_data:
            sector_name = sectors_data[ticket[4]]
            row = str(ticket[1])
            seat = str(ticket[2])
            price = int(float(ticket[3]))

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
