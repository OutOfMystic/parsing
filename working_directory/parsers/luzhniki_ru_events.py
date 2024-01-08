from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class Luzhniki(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.luzhniki.ru/afisha/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def parse_events(self):
        a_events = []

        soup = await self.requests_to_events(self.url)
        all_event = soup.select('div.feed__item')
        for event in all_event:
            href_to_data = event.find('a', class_='card__link')
            if href_to_data is None:
                continue
            href_to_data = href_to_data.get('href')

            new_soup = self.requests_to_events(href_to_data)

            title = new_soup.find('h1', class_='article__title')
            if title is None:
                continue
            title = title.text.strip()

            date = new_soup.find('time', class_='params__param').text.strip()
            date = date.split()
            date[1] = date[1].title()[:3]
            time = new_soup.find('div', class_='event__time').text.strip()

            normal_date = ' '.join(date) + ' ' + time

            href = new_soup.find('a', class_='event__button')
            if href is None:
                continue
            href = href.get('href')

            a_events.append([title, href, normal_date])

        return a_events

    async def requests_to_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self):
        a_events = await self.parse_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])

