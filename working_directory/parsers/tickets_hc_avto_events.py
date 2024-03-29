import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.sessions import AsyncProxySession


class HcAvtomobilistHockey(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 1600
        self.driver_source = None
        self.url = 'https://tickets.hc-avto.ru'
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "User-Agent": self.user_agent
            }

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def date_reformat(date: str):
        #вт, 03 октября 2023 19:00
        date = date.split(',')[-1].strip()
        day, month, year, time = date.split()
        month = month[:3].capitalize()
        return f"{day} {month} {year} {time}"

    async def body(self):
        r = await self.session.get(url=self.url, headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')

        tickets = soup.select_one('#tickets')
        tr = tickets.find_all('tr', attrs={'data-type': re.compile(r'\d+')})
        a_events = []
        for i in tr:
            try:
                title, date, venue, url1 = i.find_all('td')
                title = title.text
                date = self.date_reformat(date.text)
                venue = venue.text
                url1 = url1.find('a').get('href')
                url1 = f"{self.url}{url1}"
                a_events.append((title, url1, date, venue))
            except Exception as ex:
                continue

        for event in a_events:
            self.register_event(event_name=event[0], url=event[1],
                                date=event[2], venue=event[3])