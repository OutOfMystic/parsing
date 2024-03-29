from typing import NamedTuple, Optional, Union, Generator
import datetime

from dateutil import relativedelta
from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class GoUnicsRu(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://go.unics.ru/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self):
        soup = await self._requests_to_events()

        events = self._get_events_from_soup(soup)

        output_data = self._parse_events_from_soup(events)

        return output_data

    def _parse_events_from_soup(self, events: ResultSet[Tag]):
        datas = []
        for event in events:
            output_data = self._parse_data_from_event(event)
            if output_data is not None:
                datas.append(output_data)
        return datas

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.findAll('div', class_='teams__name')
        try:
            title = f'{title[0].text.strip()} - {title[1].text.strip()}'
        except IndexError:
            return None

        date, time = event.find('span', class_='time').text.strip().split()
        day, month, year = date.split('.')
        month = month_list[int(month)]
        normal_date = f'{day} {month} {year} {time}'

        href = event.find('a', class_='events__buy')
        if href is None:
            return None
        href = 'https://go.unics.ru' + href.get('href')

        return OutputEvent(title=title, href=href, date=normal_date)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.events__item')
        return events

    async def _requests_to_events(self) -> BeautifulSoup:
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
            'sec-fetch-site': 'same-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self):
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
