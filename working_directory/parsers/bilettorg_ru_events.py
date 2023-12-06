from bs4 import BeautifulSoup
from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.manager.proxy.instances import ProxySession


class Bilettorg(EventParser):
    proxy_check_url = 'https://www.bilettorg.ru/'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.bilettorg.ru/anonces/106/'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self):
        a_events = []

        soup = self.get_all_events()

        all_events = soup.select('li.wow.fadeIn')
        for event in all_events:
            title = event.find('a', class_='title').text.strip()

            date = event.find('p', class_='date1').text.strip().split()
            date[1] = date[1].title()[:3]
            time = event.find('p', class_='date2').text.strip().split()[1]
            normal_date = ' '.join(date) + ' ' + time

            scene = event.find_all('p')[2].text

            href = event.find('span', class_='a-like2')
            if href is None:
                continue
            href = href.get('onclick')
            href = double_split(href, "='", "';")
            href = f'https://www.bilettorg.ru{href}'

            a_events.append([title, href, normal_date, scene])

        return a_events

    def get_all_events(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'www.bilettorg.ru',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self):
        a_events = self.parse_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], scene=event[3])
