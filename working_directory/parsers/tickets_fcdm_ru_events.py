from typing import NamedTuple, Optional, Union
import datetime
import json

from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class TicketsFcdmRu(EventParser):

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.fcdm.ru/api/event-show/posted?viewPage=TICKETS'

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self) -> OutputEvent:
        json_data = self._requests_to_events()

        return self._parse_events_from_soup(json_data)

    def _parse_events_from_soup(self, json_data: json) -> OutputEvent:
        for event in json_data:
            output_data = self._parse_data_from_event(event)
            if output_data is not None:
                yield output_data

    def _parse_data_from_event(self, event: dict) -> Optional[Union[OutputEvent, None]]:
        title = event['name']

        date = event['startDate']
        date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
        normal_date = f'{date.day} {month_list[int(date.month)]} {date.year} {date.hour}:{date.minute}'

        href = event['uuid']
        href = 'https://tickets.fcdm.ru/tickets/' + href

        return OutputEvent(title=title, href=href, date=normal_date)

    def _requests_to_events(self) -> json:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://tickets.fcdm.ru/tickets',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers, verify=False)
        return r.json()

    def body(self) -> None:
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
