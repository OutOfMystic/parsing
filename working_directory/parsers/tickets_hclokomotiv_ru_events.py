from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class Locomotiv(EventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.hclokomotiv.ru'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        month_list = [
            "", "Янв", "Фев", "Мар", "Апр",
            "Май", "Июн", "Июл", "Авг",
            "Сен", "Окт", "Ноя", "Дек"
        ]

        a_events = []
        all_events = soup.find_all('div', class_='events__item')

        for event in all_events:
            # comands = event.find_all('strong', class_='teams__name')
            # title = comands[0].text + ' - ' + comands[1].text
            # title = 'Локомотив - ' + comands[1].text
            title = 'Локомотив - '

            datetime_event = event.find('span', class_='time_center').text
            date, time = datetime_event.split()
            day, str_month, year = date.split('.')
            month = month_list[int(str_month)]
            normal_date = day + ' ' + month + ' ' + year + ' ' + time

            href = event.find('a').get('href')
            href = self.url + href

            a_events.append([title, href, normal_date])

        return a_events

    def get_events(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(url=self.url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.parse_events(soup)

        return a_events

    def body(self):
        a_events = self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])