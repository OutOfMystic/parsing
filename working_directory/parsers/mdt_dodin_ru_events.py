from typing import NamedTuple, Optional, Union

import json
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.logger import track_coroutine
from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    id_event: str


class MdtDodin(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://mdt-dodin.ru/plays/afisha/'

    @track_coroutine
    async def before_body(self):
        self.session = AsyncProxySession(self)

    @track_coroutine
    async def _parse_events(self):
        soup = await self._requests_to_events(self.url)

        links_with_all_events_pages = self._get_href_with_all_events_pages(soup)

        events = self._get_events_from_soup(soup)

        all_events = await self._parse_events_from_json(events, links_with_all_events_pages)

        return await self._get_filtered_events(all_events)

    @track_coroutine
    async def _get_filtered_events(self, all_events: list[OutputEvent]) -> OutputEvent:
        events = []
        all_id_event = [event.id_event for event in all_events]

        data_status_event = await self._requests_to_check_tickets(all_id_event)
        for event in all_events:
            if self._get_status_event(data_status_event, event.id_event):
                events.append(event)

    @track_coroutine
    async def _parse_events_from_json(self, events: list, links_with_all_events_pages: list[str]) -> list[OutputEvent]:
        output_list = []
        for index, link_with_events in enumerate(links_with_all_events_pages):
            for event in events:
                output_data = self._parse_data_from_event(event, link_with_events)
                if output_data is not None:
                    output_list.append(output_data)

            if index == len(links_with_all_events_pages) - 1:
                break
            soup = await self._requests_to_events(links_with_all_events_pages[index + 1])
            events = self._get_events_from_soup(soup)
        return output_list

    def _parse_data_from_event(self, event: BeautifulSoup, link_with_events: str) -> Optional[Union[OutputEvent, None]]:
        title = event.select('div.performance-afisha__body:last-child a')[0].text.strip()

        day = event.find('div', class_='day').text
        month, year = link_with_events.split('=')[-1].split('.')
        month = month_list[int(month)]
        time = event.find('div', class_='time').text
        normal_date = f'{day} {month} {year} {time}'

        href = event.select('li.performance-afisha__buy a')
        if len(href) == 0:
            return None
        href = href[0].get('href')
        id_event = href.split('/')[-1]
        if not id_event.isnumeric():
            return None
        href = f'https://mdt-dodin.ru/buy-tickets/0/#/event/{id_event}'

        return OutputEvent(title=title, href=href, date=normal_date, id_event=id_event)

    def _get_status_event(self, data_status_event: json, id_event: str) -> bool:
        data_about_id_event = data_status_event.get(id_event)
        status_id_event = data_about_id_event.get('salesAvailable')
        return status_id_event

    def _get_href_with_all_events_pages(self, soup: BeautifulSoup) -> list[str]:
        all_month_with_events = soup.select('div.dropdown__list a')
        link_to_events = 'https://mdt-dodin.ru/plays/afisha/?yearList='
        all_links_with_events = [link_to_events + date.get('data-input-value') for date in all_month_with_events]
        return all_links_with_events

    def _get_events_from_soup(self, soup: BeautifulSoup) -> list:
        events = soup.select('ul.ui-list > li ul.pack-list')
        return events

    async def _requests_to_check_tickets(self, data: list) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'content-length': '142',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://mdt-dodin.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent
        }
        url = 'https://mdtdodin.core.ubsystem.ru/uiapi/event/sale-status'
        data = {
            "ids": data
        }
        r = await self.session.post(url, headers=headers, json=data, verify=False)
        return r.json()

    async def _requests_to_events(self, url: str) -> BeautifulSoup:
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
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def body(self) -> None:
        for event in await self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
