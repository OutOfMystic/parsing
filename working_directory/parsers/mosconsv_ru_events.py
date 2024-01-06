from typing import NamedTuple, Optional, Union

from requests.exceptions import ProxyError
from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    scene: str


class WwwMosconsvRu(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'http://www.mosconsv.ru/ru/concerts'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self) -> OutputEvent:
        soup = await self._requests_to_events(self.url)

        count_page = self._get_count_pages_with_events(soup)

        events = self._get_events_from_soup(soup)

        return await self._parse_events_from_soup(events, count_page)

    async def _parse_events_from_soup(self, events: ResultSet[Tag], count_page: int) -> OutputEvent:
        for page_number in range(2, count_page+1):
            for event in events:
                output_data = await self._parse_data_from_event(event)
                if output_data is not None:
                    yield output_data

            url = f'http://www.mosconsv.ru/ru/concerts?start={page_number}'
            soup = await self._requests_to_events(url)
            events = self._get_events_from_soup(soup)

    async def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('h6').text.strip()

        day = event.find('div', class_='dom').text.strip()
        month = event.find('div', class_='m').text.strip().title()
        year = event.find('div', class_='y').text.strip()
        time = event.find('div', class_='t').text.strip()
        time = time[:2] + ':' + time[2:]
        normal_date = f'{day} {month} {year} {time}'

        href = event.find('a', class_='btn-primary')
        if href is None:
            return None
        href = href.get('href')
        href = f'http://www.mosconsv.ru{href}'

        soup_to_new_href = await self._requests_href_to_buy_tickets(href)
        new_href = self._get_href_to_buy_tickets(soup_to_new_href)
        if new_href is None:
            return None

        scene = event.select('h4 a')[0].text

        return OutputEvent(title=title, href=new_href, date=normal_date, scene=scene)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.row.concert-post')
        return events

    def _get_count_pages_with_events(self, soup: BeautifulSoup) -> int:
        count_pages = soup.find('div', class_='paginator_pages')
        count_pages = count_pages.text.split()[-1]
        count_pages = int(count_pages)
        return count_pages

    def _get_href_to_buy_tickets(self, soup: BeautifulSoup) -> Optional[Union[str, None]]:
        href_to_buy_tickets = soup.select('a.btn.btn-primary.ml-auto')
        if len(href_to_buy_tickets) == 0:
            return None
        href_to_buy_tickets = href_to_buy_tickets[0].get('href')
        return href_to_buy_tickets

    async def _requests_href_to_buy_tickets(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'www.mosconsv.ru',
            'pragma': 'no-cache',
            'referer': 'http://www.mosconsv.ru/ru/concerts?start=31',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'www.mosconsv.ru',
            'pragma': 'no-cache',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        if r.status_code == 407:
            raise ProxyError()
        return BeautifulSoup(r.text, 'lxml')

    async def body(self):
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date, scene=event.scene)
