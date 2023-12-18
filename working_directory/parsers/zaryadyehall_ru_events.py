from typing import NamedTuple, Optional, Union

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.utils.date import month_list
from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.manager.proxy.instances import ProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class ZaryadyeHall(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://zaryadyehall.ru/event/'

    def before_body(self):
        self.session = ProxySession(self)

    def _parse_events(self) -> OutputEvent:
        soup = self._requests_to_events()

        new_page = self._next_page_with_events(soup)

        events = self._get_events_from_soup(soup)

        return self._parse_events_from_json(events, new_page)

    def _parse_events_from_json(
            self, events: ResultSet[Tag], new_page: Optional[Union[BeautifulSoup, None]]
    ) -> OutputEvent:
        count_page = 1
        while True:
            for event in events:
                output_data = self._parse_data_from_event(event)
                if output_data is not None:
                    yield output_data

            if new_page is None:
                break
            url = f'https://zaryadyehall.ru/event/?PAGEN_1={count_page}'
            count_page += 1
            soup = self._requests_to_axaj_data(url)
            new_page = self._next_page_with_events(soup)
            events = self._get_events_from_soup(soup)

    def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('a', class_='zh-c-item__name').text.strip().replace("'", '"')
        title = title.replace('\r', '').replace('\n', '')

        day, month = event.find('div', class_='zh-c-item__date').text.split('/')
        month = month_list[int(month)]

        time = event.find('li', class_='zh-meta-item_time')
        if time is None:
            return None
        time = time.text.replace('.', ':')
        normal_date = f'{day} {month} {time}'

        href = event.select('a.zh-c-item__buy')
        if len(href) == 0:
            return None
        href = href[0].get('onclick')
        try:
            href = double_split(href, "openNewWin('", "')")
        except (IndexError, AttributeError):
            return None

        return OutputEvent(title=title, href=href, date=normal_date)

    def _next_page_with_events(self, soup: BeautifulSoup) -> Optional[Union[BeautifulSoup, None]]:
        check_new_page = soup.find('a', class_='zh-events-bottom__more')
        return check_new_page

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('ul.zh-c-list > li.zh-c-list__item.zh-c-item div.zh-c-item__content')
        return events

    def _requests_to_axaj_data(self, url: str) -> BeautifulSoup:
        headers = {
            'accept': 'text/html, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://zaryadyehall.ru/event/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def _requests_to_events(self) -> BeautifulSoup:
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
        r = self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for event in self._parse_events():
            self.register_event(event.title, event.href, date=event.date)
