from typing import NamedTuple, Optional, Union
import json

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.date import month_list


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    event_id: str


class HelikonRu(EventParser):

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://www.helikon.ru/ru/playbill'

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self) -> OutputEvent:
        soup = self._requests_to_events()

        events = self._get_events_from_soup(soup)

        all_events = self._parse_events_from_soup(events)

        return self._filters_events(all_events)

    def _filters_events(self, all_events: list[OutputEvent]) -> OutputEvent:
        all_events_id = [event.href.split('/')[-1] for event in all_events]
        data_about_all_event_id = self._requests_to_data_about_all_event_id(all_events_id)
        sold_out = [str(event['id']) for event in data_about_all_event_id.values() if event['salesAvailable'] is False]
        for event in all_events:
            if event.event_id not in sold_out:
                yield event

    def _parse_events_from_soup(self, events: ResultSet[Tag]) -> list[OutputEvent]:
        all_events = []
        for event in events:
            output_data = self._parse_data_from_event(event)
            if output_data is not None:
                all_events.append(output_data)
        return all_events

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('a', class_='title')
        if title is None:
            title = event.find('span', class_='title')
        title = title.text.strip()

        date_and_time = event.find_all('td')
        date = date_and_time[0].text.strip()
        date = date.split(', ')[1]
        day, month, year = date.split('.')
        month = month_list[int(month)]
        time = date_and_time[3].text.strip()
        normal_date = f'{day} {month} {year} {time}'

        href_and_event_id = event.select('a[data-hwm-event-id]')
        if len(href_and_event_id) == 0:
            return None

        event_id = href_and_event_id[0].get('data-hwm-event-id')
        href = href_and_event_id[0].get('href')

        return OutputEvent(title=title, href=href, date=normal_date, event_id=event_id)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('table.sticky-enabled tbody tr')
        return events

    def _requests_to_data_about_all_event_id(self, all_events_id: list[str]) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'content-length': '821',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://www.helikon.ru',
            'pragma': 'no-cache',
            'referer': 'https://www.helikon.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent
        }
        data = {
            'ids': all_events_id
        }
        url = 'https://helikon.core.ubsystem.ru/uiapi/event/sale-status'
        r = self.session.post(url, headers=headers, json=data)
        return r.json()

    def _requests_to_events(self) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://www.helikon.ru/buy-tickets/',
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
            self.register_event(event.title, event.href, date=event.date)
