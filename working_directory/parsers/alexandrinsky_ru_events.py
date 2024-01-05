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
    event_id: str


class AlexandrinskyRu(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://alexandrinsky.ru/afisha-i-bilety/'

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self) -> OutputEvent:
        soup = self._requests_to_events()

        all_axaj_pages = self._get_all_ajax_pages(soup)

        events = self._get_events_from_soup(soup)

        return self._parse_events_from_soup(events, all_axaj_pages)

    def _parse_events_from_soup(self, events: ResultSet[Tag], all_axaj_pages: int) -> OutputEvent:
        for count_page in range(2, all_axaj_pages+2):
            for event in events:
                output_data = self._parse_data_from_event(event)
                if output_data is not None:
                    for data in output_data:
                        yield data

            soup = self._requests_to_axaj_events(str(count_page))
            events = self._get_events_from_soup(soup)
            count_page += 1

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('a').text.strip()

        all_href_and_date = event.select('a[onclick^="listim"]')
        for href_and_date in all_href_and_date:
            day = href_and_date.find('span', class_='repertoire-date-list__day').text
            month = href_and_date.find('span', class_='repertoire-date-list__month').text.title()
            time = href_and_date.find('span', class_='repertoire-date-list__time').text
            normal_date = f'{day} {month} {time}'

            href = 'https://www.afisha.ru/wl/402/api/events/info?lang=ru&sid='
            event_id = href_and_date.get('onclick')
            event_id = double_split(event_id, 'event_id: ', '})')

            yield OutputEvent(title=title, href=href, date=normal_date, event_id=event_id)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.box-poster-tickets div.box-poster-tickets-description')
        return events

    def _get_all_ajax_pages(self, soup: BeautifulSoup) -> int:
        all_pages = soup.find('input', attrs={'id': 'all-page'})
        all_pages = all_pages.get('value')
        return int(all_pages)

    def _requests_to_axaj_events(self, next_page: str) -> BeautifulSoup:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-length': '23',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': 'alexandrinsky.ru',
            'origin': 'https://alexandrinsky.ru',
            'pragma': 'no-cache',
            'referer': 'https://alexandrinsky.ru/afisha-i-bilety/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            "ajax_events": "y",
            "PAGEN_2": next_page
        }
        url = 'https://alexandrinsky.ru/afisha-i-bilety/'
        r = self.session.post(url, headers=headers, data=data)
        return BeautifulSoup(r.text, 'lxml')

    def _requests_to_events(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'alexandrinsky.ru',
            'pragma': 'no-cache',
            'referer': 'https://alexandrinsky.ru/',
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
        r = self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date, event_id=event.event_id)
