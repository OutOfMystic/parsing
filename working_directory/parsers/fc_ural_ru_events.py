from typing import NamedTuple, Optional, Union

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class FcUralRu(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://fc-ural.ru/bilety/bilety'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _parse_events(self) -> OutputEvent:
        soup = self._requests_to_events(self.url)

        events = self._get_events_from_soup(soup)

        return self._parse_events_from_soup(events)

    def _parse_events_from_soup(self, events: ResultSet[Tag]) -> OutputEvent:
        for event in events:
            output_data = self._parse_data_from_event(event)
            if output_data is not None:
                yield output_data

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.select('div.game span')
        if len(title) > 0:
            title = title[0].text.strip() + ' - ' + title[1].text.strip()

            date = event.select('div.date span')
            date = date[0].text.strip().split()
            day = date[0]
            month = date[1]
            month = month[:3].title()
            year = date[2]
            time = date[-1]
            normal_date = f'{day} {month} {year} {time}'

            href = event.find('a', class_='btn btn--primary')
            if href is None:
                return None
            href = href.get('href')
        else:
            title = event.find('div', class_='opponent').text.strip()
            title = f'Урал - {title}'

            date = event.find('div', class_='date')
            day, month, year = date.text.strip().split('/')
            month = month_list[int(month)]
            time = event.find('div', class_='time').text.strip()
            normal_date = f'{day} {month} {year} {time}'

            href = event.select('div.games__links a')[2]
            href = href.get('href')
            if href == 'javascript:void(0)':
                return None

        return OutputEvent(title=title, href=href, date=normal_date)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.game-screen div.container, div.season-games div.games__item_row.future')
        return events

    def _requests_to_events(self, url: str) -> BeautifulSoup:
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
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self):
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
