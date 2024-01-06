from typing import NamedTuple, Optional, Union

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.utils.date import month_list


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    venue: str
    event_params: str


class PelmenyNet(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://pelmeny.net/afisha'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self) -> OutputEvent:
        soup = await self._requests_to_events(self.url)

        events = self._get_events_from_soup(soup)

        return await self._parse_events_from_soup(events)

    async def _parse_events_from_soup(self, events: ResultSet[Tag]) -> OutputEvent:
        for event in events:
            output_data = await self._parse_data_from_event(event)
            for data in output_data:
                if data is not None:
                    yield data

    async def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.select('div.spoiler-poster__show-name a')[0].text
        venue = event.find('div', class_='spoiler-poster__place').text

        href = event.find('a', class_='btn').get('href')
        if 'widget.afisha.yandex.ru' in href:
            normal_date = await self._get_normal_date_from_yandex_afisha(href)
            client_key = double_split(href, '?', '&')
            session_id = double_split(href, 'sessions/', '?')
            event_params = str({'client_key': client_key, 'session_id': session_id}).replace("'", '"')
            href = href[:href.index('?')]
            yield OutputEvent(title=title, href=href, date=normal_date, venue=venue, event_params=event_params)
        elif 'kassir' in href:
            events_from_kassir = await self._get_events_from_kassir(href)
            for event_from_kassir in events_from_kassir:
                yield OutputEvent(
                    title=title, href=event_from_kassir[1], date=event_from_kassir[0], venue=venue, event_params=''
                )
        else:
            yield None

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.spoiler-poster-item')
        return events

    async def _get_events_from_kassir(self, url: str) -> tuple[str, str]:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://pelmeny.net/',
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
        r = await self.session.get(url, headers=headers)

        soup = BeautifulSoup(r.text, 'lxml')
        events = soup.find_all('a', class_='item')
        for event in events:
            day = event.find('span', class_='day-m').text
            mouth = event.find('span', class_='mouth').text
            time = event.find('span', class_='time').text
            normal_date = day + ' ' + mouth + ' ' + time

            href = event.get('href')
            href = url[:url.index('/f')] + href
            yield normal_date, href

    async def _get_normal_date_from_yandex_afisha(self, href: str) -> str:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/json; charset=UTF-8',
            'host': 'widget.afisha.yandex.ru',
            'pragma': 'no-cache',
            'referer': href,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'timeout': '5000',
            'x-requested-with': 'XMLHttpRequest',
            # 'X-Parent-Request-Id': request_id,
            'X-Retpath-Y': href,
            'user-agent': self.user_agent
        }
        event_id = double_split(href, 'sessions/', '?')
        url = 'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/' + event_id
        r = await self.session.get(url, headers=headers)

        date_datetime = r.json()['result']['session']['sessionDate']
        date, time = date_datetime.split('T')
        date = date.split('-')[::-1]
        date[1] = month_list[int(date[1])]
        time = time.split('+')[0]
        normal_date = ' '.join(date) + ' ' + time
        return normal_date

    async def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://pelmeny.net/',
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
        all_events = set(await self._parse_events())
        for event in all_events:
            self.register_event(
                event.title, event.href, date=event.date, venue=event.venue, event_params=event.event_params
            )
