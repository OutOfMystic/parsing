from typing import NamedTuple, Optional, Union
import datetime

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class CskaBasket(EventParser):

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://tickets.cskabasket.ru/ru/'

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self) -> OutputEvent:
        soup = self._requests_to_events(self.url)

        events = self._get_events_from_soup(soup)

        return self._parse_events_from_soup(events)

    def _parse_events_from_soup(self, events: ResultSet[Tag]) -> OutputEvent:
        datetime_now = datetime.datetime.now()
        month = datetime_now.month
        month = month_list[month]
        year = datetime_now.year
        for event in events:
            if 'events-main__month' in event.get('class'):
                month, year = event.text.split()
                month = month.title()[:3]
            else:
                output_data = self._parse_data_from_event(event, month, year)
                if output_data is not None:
                    yield output_data

    def _parse_data_from_event(self, event: Tag, month: str, year: str) -> Optional[Union[OutputEvent, None]]:
        title = event.select('div.teams__item div.teams__name')
        title = title[0].text + ' - ' + title[1].text

        date = event.find('div', class_='event-item__date').text.strip().split()
        day = date[0]
        time = date[-2]
        normal_date = f'{day} {month} {year} {time}'

        href = event.find('a', class_='event-item__btn')
        if href is None:
            return None
        href = href.get('href')
        href = 'https://tickets.cskabasket.ru/ru' + href

        return OutputEvent(title=title, href=href, date=normal_date)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.events-main__list')
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
