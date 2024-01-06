from bs4 import BeautifulSoup
from requests.exceptions import SSLError

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Vakhtakassa(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://vakhtakassa.com/events'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def parse_events(self):
        a_events = []

        count_page = 1
        while True:
            url = self.url + f'?page={count_page}'
            r = await self.request_events(url)
            soup = BeautifulSoup(r.text, "lxml")

            all_cart_events = soup.select('a[data-selenium="event-preview"]')
            for event in all_cart_events:
                title = event.select('h3[class*="EventPreview-19_eventName"]')[0].text
                href = event.get('href')
                href = 'https://vakhtakassa.com' + href

                day = event.select('div[class*="RowDates_dayNumber"]')[0].text
                time = event.select('div[class*="RowDates_week"]')[0].text.split()[1]
                month = event.select('div[class*="RowDates_month"]')[0].text[:3].title()

                normal_date = f'{day} {month} 2023 {time}'

                a_events.append([title, href, normal_date])

            all_page = soup.select('div[class*="Pagination_wrapper"] a[aria-label*="Page"]')
            if count_page == len(all_page):
                break
            count_page += 1

        return a_events

    async def request_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'vakhtakassa.com',
            # 'referer': 'https://vakhtakassa.com/events?',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        try:
            r = await self.session.get(url, headers=headers)
        except SSLError:
            r = await self.session.get(url, headers=headers, verify_ssl=False)
        return r

    async def body(self):
        a_events = await self.parse_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])
