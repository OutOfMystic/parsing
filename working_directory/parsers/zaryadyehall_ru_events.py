from typing import NamedTuple, Optional, Union
import re

from bs4 import BeautifulSoup, ResultSet, Tag

from parse_module.coroutines import AsyncEventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.sessions import AsyncProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class ZaryadyeHall(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url: str = 'https://zaryadyehall.ru/event/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_events(self) -> OutputEvent:
        soup = await self._requests_to_events(self.url)

        new_page = self._next_page_with_events(soup)

        events = self._get_events_from_soup(soup)
        
        return await self._parse_events_from_json(events, new_page)

    async def _parse_events_from_json(
            self, events: ResultSet[Tag], new_page: Optional[Union[BeautifulSoup, None]]
    ):
        datas = []
        count_page = 1
        for i in range(40):
            for event in events:
                output_data = await self._parse_data_from_event(event)
                if output_data is not None:
                    datas.append(output_data)
            if new_page is None:
                return datas
            url = f'https://zaryadyehall.ru/event/?PAGEN_1={count_page}'
            count_page += 1
            soup = await self._requests_to_axaj_data(url)
            new_page = self._next_page_with_events(soup)
            events = self._get_events_from_soup(soup)
        

    async def _parse_data_from_event(self, event: Tag) -> Optional[Union[OutputEvent, None]]:
        title = event.find('a', class_='zh-c-item__name').text.strip().replace("'", '"')
        title = title.replace('\r', '').replace('\n', '')
        title = title.replace('Купить билет', '')

        day, month = event.find('div', class_='zh-c-item__date').text.split('/')
        month = month_list[int(month)]

        time = event.find('li', class_='zh-meta-item_time')
        if time is None:
            return None
        time = time.text.replace('.', ':')
        normal_date = f'{day} {month} {time}'

        href = event.select_one('a.zh-c-item__buy')
        if len(href) == 0:
            return None
        id = href.get('onclick')
        if not id and 'одробнее' in href.text:
            href_part = href.get('href')
            url_to_load = f"https://zaryadyehall.ru{href_part}"
            soup = await self._requests_to_events(url_to_load)
            event_id = soup.find('a', onclick=lambda value: value and "openNewWin" in value)
            if event_id:
                onclick = event_id.get('onclick')
                url = re.search(r"https?://[^\s')]+", onclick)[0]
                #https://tickets.afisha.ru/iframe/101/api?gclid=1404449415#/place/726031
                id = url.split('/')[-1]
                href = f"https://tickets.afisha.ru/wl/101/api#/place/{id}"
            else:
                self.warning(f"Something went wrong {title}, {href}")
                return None
        else:
            try:
                event_id = re.search(r'(?<=event_id:) +\d+', id)[0].strip()
                href = f"https://tickets.afisha.ru/wl/101/api?site=zaryadyehall.ru&cat_id=undefined&building_id=undefined#/place/{event_id}"
            except (IndexError, AttributeError):
                self.warning(f"Something went wrong{title}, {href}")
                return None

        return OutputEvent(title=title, href=href, date=normal_date)

    def _next_page_with_events(self, soup: BeautifulSoup) -> Optional[Union[BeautifulSoup, None]]:
        check_new_page = soup.find('a', class_='zh-events-bottom__more')
        return check_new_page

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('ul.zh-c-list > li.zh-c-list__item.zh-c-item div.zh-c-item__content')
        return events

    async def _requests_to_axaj_data(self, url: str) -> BeautifulSoup:
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
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def _requests_to_events(self, url) -> BeautifulSoup:
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

    async def _requests_to(self, url) -> BeautifulSoup:
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
        box = await self._parse_events()
        for event in box:
            #self.info(event)
            if len(event.title) >= 200:
                event = event._replace(title=event.title[:200])
            self.register_event(event.title, event.href, date=event.date, venue='Зарядье')
