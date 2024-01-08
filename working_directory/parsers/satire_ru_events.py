import datetime
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.utils.date import month_num_by_str
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class SatireParser(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.our_urls = {
        }
        self.url = 'https://satire.ru'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_events(self, soup):
        a_events = []

        for event_card in soup.find_all('div', class_='cards-06-list__item'):
            title_block = event_card.find('div', class_='cards-06-item__title')
            title_block_text = title_block.text.strip().replace('\n', ', ').replace('\xa0', ' ')
            title_block_text_spl = title_block_text.split(', ')

            date = title_block_text_spl[0]
            time = title_block_text_spl[2]
            date = self.format_date(date, time)

            title = event_card.find('div', class_='cards-06-item__text').find_all('a')[-1].text.strip()
            title = title.replace('\u200b', '')
            href = event_card.find('a', class_='cards-06-item__button').get('href')

            scene = title_block_text_spl[-1]

            a_events.append([title, href, date, scene])

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def format_date(self, date, time):
        today = datetime.date.today()
        current_year = today.year
        current_month = today.month

        d, m = date.split(' ')
        m = m[:3].capitalize()

        m_num = month_num_by_str[m]
        y = current_year if current_month <= m_num else current_year + 1

        return f'{d} {m} {y} {time}'

    def get_events(self, month_url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'referer': 'https://satire.ru/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
        }
        r = self.session.get(month_url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.parse_events(soup)

        return a_events

    def get_month_urls(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
        }
        r = self.session.get(self.url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        months_container = soup.find('div', class_='page-header-17-nav-catalog__content')
        months_a = months_container.find_all('a', class_='page-header-17-nav-catalog-item__link')
        relative_month_urls = [month_a['href'] for month_a in months_a if 'Афиша' in month_a.text]
        absolute_month_urls = [self.url + month_url for month_url in relative_month_urls]

        return absolute_month_urls

    async def body(self):
        month_urls = self.get_month_urls()
        a_events = []
        for month_url in month_urls:
            a_events += self.get_events(month_url)

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue=event[3])
