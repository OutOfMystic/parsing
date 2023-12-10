from typing import NamedTuple, Optional, Union
import datetime

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    venue: str


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

    @staticmethod
    def work_with_event(month, year, event):
        if not event.find(class_='event-item__place'): #скорее всего это абонемент
            return None
        venue = event.find(class_='event-item__place').text or 'Мегаспорт'

        day, str_day ,time = map(str.strip ,event.find(class_='event-item__date').text.split('/'))
        time = time.split()[0]
        full_data = f'{day} {month} {year} {time}' #"03 Сен 2023 19:00"

        teams = event.find(class_='teams__wrapper')
        title = ' - '.join(map(str.strip, [i.text for i in teams.find_all(class_='teams__item')]))
        
        href = event.find(class_='event-item__btn').get('href')
        href = f"https://tickets.cskabasket.ru/ru{href}"
        return OutputEvent(title=title, href=href, date=full_data, venue=venue)

    def _parse_events_from_soup(self, events):
        a_events = []
        months = events.find_all(class_='events-main__month')
        for month_year in months:
            month, year = month_year.text.split()
            month = month[:3].capitalize()
            event = month_year.find_next()
            while event.get('class') and 'event-item' in event.get('class'):
                try:
                    output_event = self.work_with_event(month, year, event)
                except Exception as ex:
                    self.warning(f'{ex}')
                else:
                    if output_event:
                        a_events.append(output_event)
                event = event.find_next_sibling()
        return a_events

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events_box = soup.select_one('div.events-main__list')
        return events_box

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
        a_events = self._parse_events()
        for event in a_events:
            self.register_event(event.title, event.href, date=event.date, venue=event.venue)
