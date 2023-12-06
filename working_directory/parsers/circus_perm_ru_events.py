from typing import NamedTuple, Optional, Union

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class CircusPermRu(EventParser):

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://www.circus-perm.ru/'

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self) -> OutputEvent:
        soup = self._requests_to_events(self.url)

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
        title = 'Эпохи'

        day = event.find('p', class_='day').text
        month = event.find('p', class_='month').text[:3]

        all_time_in_day = event.find_all('a')
        for time_in_day in all_time_in_day:
            time = time_in_day.find('p').text
            time = time.replace('Купить на ', '')

            normal_date = f'{day} {month} {time}'

            id_event = time_in_day.get('data-tp-event')
            href = f'https://ticket-place.ru/widget/{id_event}/data'
            output_list.append(OutputEvent(title=title, href=href, date=normal_date))
        return output_list

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.ticket_item')
        return events

    def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'www.circus-perm.ru',
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
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
