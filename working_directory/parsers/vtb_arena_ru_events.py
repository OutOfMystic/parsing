from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class VtbArena(EventParser):
    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://vtb-arena.com/poster/'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []

        # all_events = soup.find_all('div', class_='col')
        all_events = soup.select('#poster_poster div.col.w-33')

        for event in all_events:
            title = event.find('a', class_='card-c__title').text.strip()

            date = event.find('div', class_='card-c__date').text.strip()
            # date = double_split(str(date), '>', '<').strip()
            date = date.split()
            month = date[1][:3].title()
            if month == 'Мая':
                month = 'Май'
            date = date[0] + ' ' + month + ' ' + date[2] + ' ' + date[5]

            href = event.find('a', class_='card-c__label')
            if not href:
                continue
            href = href.get('href')

            a_events.append([title, href, date])

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def get_events(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'referer': 'https://vtb-arena.com/',
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
        r = self.session.get(self.url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.parse_events(soup)

        return a_events

    def body(self):
        a_events = self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])