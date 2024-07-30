from typing import NamedTuple, Optional
import time
from datetime import datetime

from bs4.element import Tag
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.utils.date import make_date_if_year_is_unknown
from parse_module.utils import utils

class OutputEvent(NamedTuple):
    title: str
    href: str
    date: datetime

class NotUrlFound(Exception):
    pass
class NotImplementedUrl(Exception):
    pass

class Mikhailovsky(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.domain: str = 'https://mikhailovsky.ru'
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            "priority": "u=0, i",
            "sec-ch-ua": "\"Not/A)Brand\";v=\"8\", \"Chromium\";v=\"126\", \"Google Chrome\";v=\"126\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent,
        }
        self.print_errors = False

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def load_page_with_events(self, month_param, last_struct_month_param,
                         PAGEN_NAME, PAGEN_VALUE):
        current_timestamp = int(time.time() * 1000)
        url = f"https://mikhailovsky.ru/afisha/performances/?q=&month={month_param}"\
              f"&last_struct_month={last_struct_month_param}"\
              f"&{PAGEN_NAME}={PAGEN_VALUE}&_={current_timestamp}"
        response = await self.session.get(url, headers=self.headers)
        return response.text

    def find_all_events_in_one_page(self, soup: BeautifulSoup):
        perfomance_list = soup.find('div', id='performance-list')
        all_events_on_page = perfomance_list.select('div.card')
        a_events = []
        for event in all_events_on_page:
            try:
                output_event = self.parse_one_event(event)
                a_events.append(output_event)
            except Exception as ex:
                if self.print_errors:
                    self.bprint(f"{ex.__class__.__name__}: {ex}", color=utils.Fore.RED)
        return a_events

    def find_PAGEN_VALUES(self, soup):
        PAGEN_NAME = soup.find(id='PAGEN_NAME').get('value')
        PAGEN_VALUE = soup.find(id='PAGEN_VALUE').get('value')
        return PAGEN_NAME, PAGEN_VALUE

    def parse_one_event(self, event: Optional[Tag]):
        title = event.find('h2').text.strip()

        day = event.find(class_='card__day').text.strip()
        month, time, day_of_week = event.find(class_='card__time').text.strip().split()
        date = make_date_if_year_is_unknown(day, month, time, need_datetime=True)

        url = event.find('a', class_='button')
        if not url or 'Билетов нет' in url.text:
            raise NotUrlFound(f"{title}, {date}")
        if ('.yandex.' in url
                or 'maxitiket' in url
                or 'subscriptions' in url
                or 'wowtickets.ru' in url):
            raise NotImplementedUrl(f"{title}, {date}")
        href = f"{self.domain}{url.get('href')}"
        return OutputEvent(title=title, href=href, date=date)

    async def get_events_page(self, PAGEN_NAME, PAGEN_VALUE,
                        month_param, last_struct_month_param):
        text = await self.load_page_with_events(month_param=month_param,
                                last_struct_month_param=last_struct_month_param,
                                PAGEN_NAME=PAGEN_NAME,
                                PAGEN_VALUE=PAGEN_VALUE)
        soup = BeautifulSoup(text, 'lxml')
        PAGEN_NAME, PAGEN_VALUE = self.find_PAGEN_VALUES(soup)
        events = self.find_all_events_in_one_page(soup)
        return events, PAGEN_NAME, PAGEN_VALUE

    async def body(self) -> None:
        PAGEN_VALUE = 1
        PAGEN_NAME = 'PAGEN_1'
        month_param = f"{self.current_year}.{self.current_month}"
        last_struct_month_param = str(self.current_month)
        while PAGEN_VALUE:
            events, PAGEN_NAME, PAGEN_VALUE = await self.get_events_page(PAGEN_NAME,
                                                                   PAGEN_VALUE,
                                                                   month_param,
                                                                   last_struct_month_param)
            for event in events:
                #print(event)
                self.register_event(event.title, event.href, date=event.date, venue='Михайловский театр')
