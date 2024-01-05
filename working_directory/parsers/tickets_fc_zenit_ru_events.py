import json
from typing import NamedTuple, Iterable

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class TicketsFcZenit(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.urls: tuple[str, ...] = (
            'https://tickets.fc-zenit.ru/football/tickets/',
            'https://tickets.fc-zenit.ru/basketball/tickets/',
            'https://tickets.fc-zenit.ru/events/concerts/',
        )

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self, url: str) -> OutputEvent:
        soup = self._requests_to_events(url)

        json_data = self._get_json_data_from_soup(soup)

        return self._parse_event_from_json(json_data)

    def _parse_event_from_json(self, json_data: json) -> OutputEvent:
        all_events_in_json_data: Iterable = json_data.get('events')
        for event in all_events_in_json_data:
            title = event.get('name')

            date_and_time: dict[str] = event.get('date')
            date = date_and_time.get('formatted').split(',')[0].split()
            date[1] = date[1].title()[:3]
            time = date_and_time.get('time')
            normal_date = ' '.join(date) + ' ' + time

            href = event.get('bitrixId')
            href = f'https://tickets.fc-zenit.ru/stadium.php?MATCH_ID={href}'

            yield OutputEvent(title=title, href=href, date=normal_date)

    def _get_json_data_from_soup(self, soup: BeautifulSoup) -> json:
        js_data_from_script_in_page = soup.select('main script')[0].text
        index_start = js_data_from_script_in_page.index('=') + 2
        json_data_from_script_in_page = js_data_from_script_in_page[index_start:]
        return json.loads(json_data_from_script_in_page)

    def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'tickets.fc-zenit.ru',
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
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for url in self.urls:
            for event in self._parse_events(url):
                self.register_event(event.title, event.href, date=event.date)
