from typing import NamedTuple, Optional, Union, Generator
import datetime

from dateutil import relativedelta
from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class MelomanRu(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://meloman.ru/calendar/?hall=koncertnyj-zal-chajkovskogo'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _parse_events(self):
        next_url = self._get_next_url()

        url, year, month = next(next_url)

        soup = self._requests_to_events(url)

        events = self._get_events_from_soup(soup)

        output_data = self._parse_events_from_soup(events, year, month, next_url)

        return output_data

    def _parse_events_from_soup(
            self, events: ResultSet[Tag], year: str, month: str, next_url: Generator[tuple[str, ...], None, None]
    ) -> OutputEvent:
        count_empty = 0
        while True:
            for event in events:
                output_data = self._parse_data_from_event(event, year, month)
                if output_data is not None:
                    yield output_data

            url, year, month = next(next_url)
            soup = self._requests_to_events(url)
            events = self._get_events_from_soup(soup)
            if len(events) == 0:
                count_empty += 1
            if count_empty == 5:
                break

    def _parse_data_from_event(self, event: Tag, year: str, month: str) -> Optional[Union[OutputEvent, None]]:
        title = event.find('a')
        if title is None:
            title = event.find('strong')
        title = title.text.strip()

        day = event.find('p', class_='day').text
        month = month_list[int(month)]
        time = event.findAll('span', class_=['text', 'sans'])[-1].text
        normal_date = f'{day} {month} {year} {time}'

        href = event.find('a', class_='buy-tickets-online')
        if href is None:
            return None
        href = href.get('href')

        return OutputEvent(title=title, href=href, date=normal_date)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.calendar-day')
        return events

    def _get_next_url(self) -> Generator[tuple[str, ...], None, None]:
        date = datetime.datetime.today()
        while True:
            next_url = self.url + f'&year={date.year}&month={date.month}'
            yield next_url, date.year, date.month
            date = date + relativedelta.relativedelta(months=1)

    def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'meloman.ru',
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
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
