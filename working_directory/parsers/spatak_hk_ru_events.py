from typing import NamedTuple, Optional, Union
import re

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class Lokobasket(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://hk-spartak.qtickets.ru/'

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self):
        soup = self._requests_to_events()
        events = self._get_events_from_soup(soup)
        output_data = self._parse_events_from_soup(events)

        return output_data

    def _parse_events_from_soup(self, events: ResultSet[Tag]) -> OutputEvent:
        a_events = []
        for event in events:
            title = event.find('h2')
            title = title.text.strip()
            date = event.find('span', attrs={'class':re.compile('date')}).text.strip().split()
            if '–' in date: # aбонемент
                continue
            date[1] = date[1].title()[:3]
            normal_date = ' '.join(date[:3])
            href = event.find('a').get('href')

            a_events.append(OutputEvent(title=title, href=href, date=normal_date))
        return a_events
        

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('h2')
        title = title.text.strip()
        date = event.find('span', attrs={'class':re.compile('date')}).text.strip().split()
        if '–' in date: # aбонемент
            return 'None'
        date[1] = date[1].title()[:3]
        normal_date = ' '.join(date[:3])
        href = event.find('a').get('href')

        return OutputEvent(title=title, href=href, date=normal_date)
    

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('.item')
        return events
    

    def _requests_to_events(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
                'user-agent': self.user_agent
            }
        r = self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for event in self._parse_events():
            self.register_event(event.title, event.href,
                                 date=event.date, venue='Дворец Спорта «Мегаспорт»')