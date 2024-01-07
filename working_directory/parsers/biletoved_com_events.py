from datetime import datetime
from typing import NamedTuple

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.manager.proxy.instances import AsyncProxySession
from parse_module.utils import utils


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: datetime
    place: str


class BiletovedEvents(AsyncEventParser):
    def __init__(self, *args):
        super().__init__(*args)
        self.delay = 3600
        self.driver_source = None
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            'user-agent': self.user_agent
        }
    
    async def load_all_events(self, soup):
        pagelist = soup.find(class_='shop2-pagelist')
        if pagelist:
            pagelist_box = pagelist.select('li.page-num:not(.active-num)')
            urls = [f"https://biletoved.com{i.find('a').get('href')}" for i in pagelist_box]
        
        a_events = []
        a_events.extend(self.load_one_event(soup))
        for page in urls:
            try:
                r2 = await self.session.get(page, headers=self.headers)
                soup = BeautifulSoup(r2.text, 'lxml')
                a_events.extend(self.load_one_event(soup))
            except Exception as ex:
                self.bprint(f"error in {page} {ex}")
        return a_events

    def load_one_event(self, soup):
        a_events = []
        all_events_container = soup.find(class_='product-list')
        all_events_list = all_events_container.find_all('form')
        for event in all_events_list:
            details = event.find(class_='product-details')
            date = details.select_one('.even:not([class*=" "])').find('td').text 
            #03.01.2024 or 2024
            if '.' not in date:
                continue
            time = details.find(attrs={'data-asd':"vrema_nacala"}).find('td').text.strip()
            date_obj = datetime.strptime(date, '%d.%m.%Y')
            time_obj = datetime.strptime(time, '%H:%M').time()
            datetime_obj = datetime.combine(date_obj, time_obj)

            url = event.find(class_='product-name')
            title = url.text
            url = f"https://biletoved.com{url.find('a').get('href')}"

            place = event.find(class_='mesto-provedenia-sobytia').find('th').text
            
            a_events.append(OutputEvent(title=title, href=url, date=datetime_obj, place=place))
        return a_events

    async def get_soup_from_url(self, url):
        r1 = await self.session.get(url, headers=self.headers)
        soup = BeautifulSoup(r1.text, 'lxml')
        return soup

    async def before_body(self):
        self.session = AsyncProxySession(self)


    async def body(self):
        all_urls = [
            'https://biletoved.com/zakazbiletov/folder/bilety-v-bkz-oktyabrskiy',
        ]

        a_events = []

        for url in all_urls:
            try:
                soup = await self.get_soup_from_url(url)
                events = await self.load_all_events(soup)
            except Exception as ex:
                self.warning(f'cannot load {url} {ex}')
                raise
            else:
                a_events.extend(events)

        for event in a_events:
            #self.info(event)
            self.register_event(event.title, event.href, 
                                        date=event.date, venue=event.place, place=event.place)