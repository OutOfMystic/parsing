from typing import NamedTuple, Optional, Union

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class Lokobasket(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://lokobasket.qtickets.ru/organizer/12326'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _parse_events(self):
        soup = self._requests_to_events()

        events = self._get_events_from_soup(soup)

        output_data = self._parse_events_from_soup(events)

        return output_data

    def _parse_events_from_soup(self, events: ResultSet[Tag]) -> OutputEvent:
        for event in events:
            output_data = self._parse_data_from_event(event)
            if output_data is not None:
                yield output_data

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('span', class_='name')
        title = title.text.strip()

        date = event.find('span', class_='date').text.strip().split()
        date[1] = date[1].title()[:3]
        del date[3]
        normal_date = ' '.join(date)

        href = event.find('a').get('onclick')
        event_id = double_split(href, "'loadEvent', ", ', {')
        href = 'https://lokobasket.qtickets.ru/event/' + event_id

        return OutputEvent(title=title, href=href, date=normal_date)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.item')
        return events

    def _requests_to_events(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'content-length': '735',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://lokobasket.com',
            'pragma': 'no-cache',
            'referer': 'https://lokobasket.com/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        data = {
            'organizer_id': '12326'
        }
        r = self.session.post(self.url, headers=headers, data=data)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self):
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
