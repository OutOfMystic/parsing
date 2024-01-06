from typing import NamedTuple, Callable, Optional, Union
from datetime import datetime

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils import utils


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class Mikhailovsky(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://mikhailovsky.ru/afisha/performances/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self) -> Callable[[BeautifulSoup, str], OutputEvent]:
        soup = await self._requests_to_events()

        events, next_href = self._get_events_from_soup(soup)

        return await self._parse_events_from_json(events, next_href)

    async def _parse_events_from_json(
            self, events: list, next_href: BeautifulSoup
                    ) -> Callable[[BeautifulSoup, str], OutputEvent]:
        day_old = int(datetime.now().day)
        month_now = month_list[datetime.now().month]
        while True:
            for event in events:
                if event.name == 'h3':
                    month_now = event.text[:3]
                    continue
                try:
                    day_now = int(event.find('div', class_='day').text)
                    if day_old > day_now:
                        month_now = month_list.index(month_now)
                        month_now = month_list[(month_now+1) % len(month_list)][:3] or 'Янв'
                    day_old = day_now
                except Exception as ex:
                    self.debug(ex, month_now, month_list, day_now, day_old)

                output_data = self._parse_data_from_event(event, month_now)
                if output_data is not None:
                    yield output_data

            if next_href is None:
                break
            else:
                url = next_href.get('href')
                url = f'https://mikhailovsky.ru{url}'
                soup = await self._requests_to_axaj_events(url)
                events, next_href = self._get_events_from_soup(soup)

    def _parse_data_from_event(self, event: BeautifulSoup, month_now: str) -> Optional[Union[OutputEvent, None]]:
        month_current = datetime.now().month
        month_event = month_list.index(month_now)

        year = datetime.now().year
        if month_event < month_current:
            year += 1

        title = event.select('div.detail a')[0].text

        day = event.find('div', class_='day').text
        time = event.select('div.time span')[0].text
        normal_date = f'{day} {month_now} {year} {time}'

        href = event.select('div.ticket a')
        if len(href) == 0:
            return None
        href = href[0].get('href')
        if '.yandex.' not in href and 'maxitiket' not in href and 'subscriptions' not in href:
            href = f'https://mikhailovsky.ru{href}'
        else:
            return None
        # else:
        #     href = # await self.session.get(href).url
        #     href = href[:href.index('?')].replace('=', '%3D') + '?widgetName=w2&lang=ru'

        return OutputEvent(title=title, href=href, date=normal_date)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> tuple[list, BeautifulSoup]:
        id_to_find_elements = '#afisha_performance_list_container'
        # events = soup.select(f'{id_to_find_elements} h3, {id_to_find_elements} div.item:not([style])')
        events = soup.select(f'{id_to_find_elements} div.item:not([style])')
        next_href = soup.find('a', class_='load-more')
        return events, next_href

    async def _requests_to_axaj_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'mikhailovsky.ru',
            'pragma': 'no-cache',
            'referer': 'https://mikhailovsky.ru/afisha/performances/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def _requests_to_events(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'mikhailovsky.ru',
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
        r = await self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self) -> None:
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
