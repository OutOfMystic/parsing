from typing import NamedTuple, Optional, Union

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    event_id: str
    token: str


class Contextfest(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://contextfest.com/programs/duo-12'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self) -> OutputEvent:
        soup = await self._requests_to_events(self.url)

        title = soup.select('section h3')[0].text
        events = self._get_events_from_soup(soup)

        return self._parse_events_from_soup(events, title)

    def _parse_events_from_soup(self, events: ResultSet[Tag], title: str) -> OutputEvent:
        for event in events:
            output_data = self._parse_data_from_event(event, title)
            if output_data is not None:
                yield output_data

    def _parse_data_from_event(self, event: Tag, title: str) -> Optional[Union[OutputEvent, None]]:
        date = event.find('div', class_='date').text.split()
        date[1] = date[1][:3].title()
        normal_date = ' '.join(date)

        href_data = event.find('button')
        event_id = href_data.get('data-tc-event')
        token = href_data.get('data-tc-token')
        # href = f'https://ticketscloud.com/v1/widgets/common?event={event_id}&token={token}'
        href = 'https://ticketscloud.com/v1/services/widget'

        return OutputEvent(title=title, href=href, date=normal_date, event_id_=event_id, token=token)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.find_all('div', class_='list-item')
        return events

    async def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://contextfest.com/programs/performances',
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
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date, event_id_=event.event_id, token=event.token)
