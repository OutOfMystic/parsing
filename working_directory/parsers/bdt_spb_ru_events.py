from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class BdtSpb(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://bdt.spb.ru/afisha/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def parse_events(self):
        a_events = []

        soup = await self.requests_to_events(self.url)

        all_month = soup.select('ul.dirmenu li a[href^="/afisha/?month="]')
        for next_month_href in range(len(all_month) + 1):

            all_event_date = soup.select('div.afisha-row.d-flex.flex-column.flex-wrap.flex-md-row.flex-md-nowrap.pb-3.mb-3.border-bottom')
            for event_date in all_event_date:
                date = event_date.find('span', class_='day').text.strip()
                date = date.split('/')
                date[1] = month_list[int(date[1])]

                all_event = event_date.select('div.d-flex.flex-wrap.flex-md-row.flex-md-nowrap.pt-3.pt-md-0')
                for event in all_event:
                    href = event.find('a', class_='tl_afisha')
                    if href is None:
                        continue
                    href = href.get('href') + 'to_parser'

                    title = event.find('a', class_='text-secondary')
                    if title is None:
                        title = event.select('span.text-secondary a span')
                        if len(title) == 0:
                            title = event.select('span.text-secondary span b')
                            if len(title) == 0:
                                title = event.select('span.text-secondary p span')
                        title = title[0]
                    title = title.text.strip()

                    time = event.find('em', class_='color-bdt').text.strip().split('в ')[-1]
                    normal_date = ' '.join(date) + ' ' + time

                    a_events.append([title, href, normal_date])

            if next_month_href < len(all_month):
                url = f'https://bdt.spb.ru{all_month[next_month_href].get("href")}'
                soup = await self.requests_to_events(url)

        return a_events

    async def requests_to_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q'
                      '=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
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
        async with self.session.get_with(url, headers=headers) as r:
            return BeautifulSoup(await r.text(), 'lxml')

    async def body(self):
        a_events = await self.parse_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])

