import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class HcSibirHockey(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.hcsibir.ru'
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
    def data_reformat(date, time):
        '''date: 06 октября, пт.
        time: 19:30'''
        date = date.split(',')[0]
        day, month = map(str.strip, date.split())
        month = month[:3].capitalize()
        time = time.strip()
        return f"{day} {month} {time}"
    

    async def body(self):
            r = await self.session.get(url=self.url, headers=self.headers, verify=False)
            soup = BeautifulSoup(r.text, 'lxml')

            tickets = soup.find(class_='tickets__list').find('tbody')
            data_items = tickets.find_all('tr', attrs={'data-team': '4'})
            #4 = СИБИРЬ  ; 7 = СИБИРСКИЕ СНАЙПЕРЫ
            a_events = []
            if data_items:
                for event in data_items:
                    t1 = event.find(class_='t1-text')
                    host = t1.find(class_='host').text.split()[0].strip()
                    guest = t1.find(class_='guest').text.split()[0].strip()
                    title = f"{host} - {guest}"

                    t2 = event.find(class_='t2')
                    date = t2.find('small').text
                    time = t2.find('span').text
                    full_date = self.data_reformat(date, time)
                    
                    try:
                        link = event.find(class_='tickets__buy').find('a').get('href')
                    except AttributeError:
                         continue
                    url_event = f"{self.url}{link}"

                    a_events.append((title, url_event, full_date, 'Сибирь-Арена'))
            
            for event in a_events:
                self.register_event(event_name=event[0], url=event[1],
                                                 date=event[2], venue=event[3])
                self.debug(event)