import time

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split, lrsplit, contains_class, class_names_to_xpath
from parse_module.utils import utils


class LenkomParser(SeatsParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'lenkom' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 300
        self.driver_source = None

    def get_tl_csrf_and_data(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp'
                      ',image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://bdt.spb.ru/',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)

        tl_csrf = double_split(r.text, '<meta name="csrf-token" content="', '"')
        if 'performanceId:' not in r.text:
            return None
        performance_id = double_split(r.text, 'performanceId: ', ',')
        if 'maxTicketCount' not in r.text:
            return None

        limit = double_split(r.text, 'maxTicketCount: ', ',')
        is_special_sale = double_split(r.text, "isSpecialSale: '", "'")

        return tl_csrf, performance_id, limit, is_special_sale

    def before_body(self):
        self.session = ProxySession(self)
        event_vars = self.get_tl_csrf_and_data()
        while not event_vars:
            self.bprint('Waiting event vars')
            time.sleep(self.delay)
            self.last_time_body = time.time()
            event_vars = self.get_tl_csrf_and_data()
        else:
            tl_csrf, self.performance_id, self.limit, self.is_special_sale = event_vars
        self.tl_csrf_no_f = tl_csrf.replace('=', '%3D')

    def reformat(self, sectors):
        pass

    def body(self):
        json, all_ = 1, 1

        url = (f'https://{self.domain}/hallview/map/'
               f'{self.performance_id}/?json='
               f'{json}&all={all_}&isSpecialSale={self.is_special_sale}&tl-csrf='
               f'{self.tl_csrf_no_f}')

        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = self.session.get(url, headers=headers)
        if '"Unable to verify your data submission."' in r.text:
            self.proxy = self.controller.proxy_hub.get()
            self.before_body()
        if '""' in r.text:
            self.proxy = self.controller.proxy_hub.get()
            self.before_body()
        if isinstance(r.json(), str):
            self.bprint(utils.yellow(r.text))
            return
        all_tickets = r.json()['places']

        a_sectors = []
        for ticket in all_tickets:
            try:
                row = int(ticket['row'])
            except:
                row = 0
            try:
                seat = int(ticket['place'])
            except:
                try:
                    seat = int(ticket['place'].replace('+', ''))
                except:
                    seat = 1
            cost = int(ticket['price'])

            for sector in a_sectors:
                sector_name = ticket['section']['name']
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = cost
                    break
            else:
                a_sectors.append({
                    'name': ticket['section']['name'],
                    'tickets': {(row, seat): cost}
                })
        self.reformat(a_sectors)
        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])


class MKHTParser(LenkomParser):
    event = 'ticketland.ru'
    url_filter = lambda url: 'ticketland.ru' in url and 'mkht' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 300
        self.driver_source = None

    def sect(self,x):

        a = [
            ['Бельэтаж ложа правая','Бельэтаж, ложа правая'],
            ['Бельэтаж ложа левая','Бельэтаж, ложа левая'],
            ['Бельэтаж середина','Бельэтаж, середина'],
            ['Бельэтаж правая сторона','Бельэтаж, правая сторона'],
            ['Бельэтаж левая сторона','Бельэтаж, левая сторона'],
            ['Балкон середина','Балкон, середина'],
            ['Балкон правая сторона','Балкон, правая сторона'],
            ['Балкон левая сторона','Балкон, левая сторона'],
            ['Партер откидное А','Партер, откидные А'],
            ['Партер откидное Б','Партер, откидные Б'],
            ['Бельэтаж откидное А','Бельэтаж, место 1А'],
            ['Бельэтаж откидное А','Бельэтаж, место 2А'],
            ['бАЛКОН ПРАВАЯ НЕУДОБНОЕ','Балкон, правая сторона (неудобные места)'],
            ['БАЛКОН ЛЕВАЯ НЕУДОБНОЕ','Балкон, левая сторона (неудобные места)']
        ]
        for i in a:
            if x==i[0]:
                x=i[1]
        return x

    def body(self):
        json, all_ = 1, 1

        url = (f'https://{self.domain}/hallview/map/'
               f'{self.performance_id}/?json='
               f'{json}&all={all_}&isSpecialSale={self.is_special_sale}&tl-csrf='
               f'{self.tl_csrf_no_f}')

        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = self.session.get(url, headers=headers)
        if '"Unable to verify your data submission."' in r.text:
            self.proxy = self.controller.proxy_hub.get()
            self.before_body()
        if '""' in r.text:
            self.proxy = self.controller.proxy_hub.get()
            self.before_body()
        if isinstance(r.json(), str):
            self.bprint(utils.yellow(r.text))
            return
        all_tickets = r.json()['places']

        a_sectors = []
        for ticket in all_tickets:
            try:
                row = int(ticket['row'])
            except:
                row = 0
            try:
                seat = int(ticket['place'])
            except:
                try:
                    seat = int(ticket['place'].replace('+', ''))
                except:
                    seat = 1
            cost = int(ticket['price'])

            for sector in a_sectors:
                sector_name = self.sect(ticket['section']['name'])
                sector['name'] = self.sect(sector['name'])
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = cost
                    break
            else:
                a_sectors.append({
                    'name': self.sect(ticket['section']['name']),
                    'tickets': {(row, seat): cost}
                })
        self.reformat(a_sectors)
        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
