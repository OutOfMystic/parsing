from typing import NamedTuple, Optional, Union
from datetime import datetime, timedelta

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils.date import month_list


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class VDNHRu(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://vdnh.ru/selections/kupit-bilet/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def _parse_events(self) -> OutputEvent:
        soup = self._requests_to_events(self.url)

        events = self._get_events_from_soup(soup)

        return self._parse_events_from_soup(events)

    def _parse_events_from_soup(self, events: ResultSet[Tag]) -> OutputEvent:
        for event in events:
            output_data = self._parse_data_from_event(event)
            if output_data is not None:
                yield output_data

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('span', class_='event-block-title').text.strip()
        if 'Экскурсия-квест «Кирилл и' in title:
            return None

        href = event.get('href')
        href = 'https://vdnh.ru/' + href

        soup_to_new_href = self._requests_href_to_buy_tickets(href)
        new_href = self._get_href_to_buy_tickets(soup_to_new_href)
        if new_href is None:
            return None

        normal_date = self._get_date_from_soup_to_new_href(soup_to_new_href)
        if normal_date is None:
            return None

        return OutputEvent(title=title, href=new_href, date=normal_date)

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('a.event-block')
        return events

    def _get_href_to_buy_tickets(self, soup: BeautifulSoup) -> Optional[Union[str, None]]:
        href_to_buy_tickets = soup.find('a', class_='ticket-button')
        if href_to_buy_tickets is None:
            return None
        href_to_buy_tickets = 'https://vdnh.ru' + href_to_buy_tickets.get('href')
        href_to_buy_tickets = href_to_buy_tickets.split('&success')[0]
        return href_to_buy_tickets

    def _get_date_from_soup_to_new_href(self, soup: BeautifulSoup) -> Optional[Union[str, None]]:
        date = soup.find('div', class_='detail-table__left')
        if date is None:
            return None
        elif date.text == 'Завтра':
            date_tomorrow = datetime.now() + timedelta(days=1)
            day = date_tomorrow.day
            month = month_list[date_tomorrow.month]
        elif date.text == 'Сегодня':
            date_today = datetime.now()
            day = date_today.day
            month = month_list[date_today.month]
        else:
            day, month = date.text.strip().split()
            month = month[:3].title()
        time = soup.find('div', class_='detail-table__right').text.strip()
        normal_date = f'{day} {month} {time}'
        return normal_date

    def _requests_href_to_buy_tickets(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://vdnh.ru/selections/kupit-bilet/',
            'sec-ch-ua': '"Not A(Brand";v="24", "Chromium";v="110"',
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

    def _requests_to_events(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not A(Brand";v="24", "Chromium";v="110"',
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

    async def body(self):
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
        events = [
            ['Теона Контридзе', 'https://vdnh.ru/widget/#/?zone=real&frontendId=2045&token=8aa5d7484641e8706fa5&id=32873&cityId=2&lng=ru&agr=https://vdnh.ru/agreement', '25 Авг 2023 20:00'],
            ['Нюша', 'https://vdnh.ru/widget/#/?zone=real&frontendId=2045&token=8aa5d7484641e8706fa5&id=32890&cityId=2&lng=ru&agr=https://vdnh.ru/agreement', '7 Сен 2023 20:00'],
            ['Нурлан Сабуров', 'https://vdnh.ru/widget/#/?zone=real&frontendId=2045&token=8aa5d7484641e8706fa5&id=33075&cityId=2&lng=ru&agr=https://vdnh.ru/agreement', '13 Авг 2023 19:00']
        ]
        for event in events:
            self.register_event(event[0], event[1], date=event[2])