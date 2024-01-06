from typing import NamedTuple, Optional, Union

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class CircusSochiRu(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://www.circus-sochi.ru/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self) -> OutputEvent:
        soup = await self._requests_to_events(self.url)

        events = self._get_events_from_soup(soup)

        return self._parse_events_from_soup(events)

    def _parse_events_from_soup(self, events: ResultSet[Tag]) -> OutputEvent:
        for event in events:
            output_data = self._parse_data_from_event(event)
            for data in output_data:
                if data is not None:
                    yield data

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[list[OutputEvent], None]]:
        output_list = []
        title = 'Девочка и слон'

        day = event.find('p', class_='day').text
        month = event.find('p', class_='month').text[:3]

        all_time_in_day = event.find_all('a')
        for time_in_day in all_time_in_day:
            time = time_in_day.find('p').text
            time = time.replace('Купить на ', '')

            normal_date = f'{day} {month} {time}'

            id_event = time_in_day.get('data-tp-event')
            href = f'https://ticket-place.ru/widget/{id_event}/data' + '|sochi'
            output_list.append(OutputEvent(title=title, href=href, date=normal_date))
        return output_list

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.ticket_item')
        return events

    async def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'www.circus-sochi.ru',
            'pragma': 'no-cache',
            'referer': 'https://yandex.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r_text = await self.session.get_text(url, headers=headers)
        return BeautifulSoup(r_text, 'lxml')

    async def body(self) -> None:
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
