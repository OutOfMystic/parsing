from datetime import datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Fomenko(EventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://fomenki.ru/timetable'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self):
        a_events = []

        datetime_now = datetime.now()
        first_request = False

        while True:
            href_to_data = ''
            if first_request:
                datetime_now = datetime_now + relativedelta(months=1)
                month_to_url = str(datetime_now.month)
                if len(month_to_url) == 1:
                    month_to_url = '0' + month_to_url
                year_to_url = datetime_now.year
                href_to_data = f'/{month_to_url}-{year_to_url}'
            url = self.url + href_to_data
            soup = self.get_events(url)

            all_events = soup.find_all('div', class_='event')
            if len(all_events) == 0:
                break

            month = month_list[datetime_now.month][:3].title()
            year = str(datetime_now.year)
            for event in all_events:
                if 'past-event' not in event.get('class'):
                    title = event.find('div', class_='title').text
                    title = title.replace('\xa0', ' ').replace('\xad', '')

                    day = event.find('div', class_='date').text.split()[0]
                    time = event.find('p', class_='time').text
                    if 'Премьера' in time:
                        time = time[:time.index('П')]

                    date = day + ' ' + month + ' ' + year + ' ' + time

                    href = event.find('p', class_='tickets')
                    href = href.find('a')
                    if href is None:
                        continue
                    href = href.get('href').split('#')[1]
                    href = 'https://fomenki.ru/boxoffice/get/?event=' + href

                    a_events.append([title, href, date])

            first_request = True

        return a_events

    def get_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'fomenki.ru',
            # 'referer': 'https://fomenki.ru/timetable/03-2023/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
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

        soup = BeautifulSoup(r.text, 'lxml')

        return soup

    def body(self):
        a_events = self.parse_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])