import time

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class CskaHockeyParser(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.our_urls = {
        }
        self.url = 'https://tickets.cska-hockey.ru/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_events(self, soup):
        a_events = []

        for event_card in soup.find_all('div', class_='matches-content-wrap'):
            date = event_card.find('div', class_='matches-content-wrap-date').text.strip()
            time = event_card.find('div', class_='matches-content-wrap-time').text.strip()
            date = self.format_date(date, time)

            title = event_card.find('div', class_='matches-content-wrap-game').text.strip()
            href = event_card.find('div', class_='matches-content-wrap-button').find('a').get('href')[1:]
            href = self.url + href

            venue = event_card.find('div', class_='matches-content-wrap-place').text.strip()
            if 'МСК "ЦСКА АРЕНА"' in venue:
                venue = 'цска аренна'

            a_events.append([title, href, date, venue])

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def format_date(self, date, time):
        d, m, y = date.split('.')
        m = month_list[int(m)]

        return f'{d} {m} {y} {time}'

    def skip_queue(self, id_queue):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://cska-hockey.queue.infomatika.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        params = [
            ('x-accel-expires', '0')
        ]
        url = 'https://cska-hockey.queue.infomatika.ru/api/users/' + id_queue
        while True:
            r = self.session.get(url, data=params, headers=headers)
            get_data = r.json()
            expired_at = get_data.get('expired_at')
            if expired_at is None:
                time.sleep(10)
            else:
                break
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://cska-hockey.queue.infomatika.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        url = 'https://tickets.cska-hockey.ru/?queue=' + id_queue
        r = self.session.get(url, headers=headers, verify=False)
        return BeautifulSoup(r.text, 'lxml')

    def get_events(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru-RU,ru;q=0.9',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
        }
        r = self.session.get(self.url, headers=headers, verify=False)

        soup = BeautifulSoup(r.text, 'lxml')
        if 'https://cska-hockey.queue.infomatika.ru/' in r.url:
            get_id = soup.select('body script')[0].text
            get_id = double_split(get_id, '}}("', '",')
            soup = self.skip_queue(get_id)

        a_events = self.parse_events(soup)

        return a_events

    async def body(self):
        a_events = self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue=event[3])
