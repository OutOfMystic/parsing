from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class TNA(EventParser):
    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.urls = [
            'https://tna-tickets.ru/sport/akbars/',
            'https://tna-tickets.ru/',
        ]

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []

        items_list = soup.find_all('div', class_='tickets_item')
        items_list += soup.find_all('div', class_='home_events_item')

        for item in items_list:
            try:
                title = item.find_all('b')
                first_team = title[0].text
                second_team = title[1].text
                title = first_team[:first_team.index(' (')] + ' - ' + second_team[:second_team.index(' (')]
            except IndexError:
                title = item.select('div.home_events_item_info a')[0].text.replace("'", '"')

            try:
                date_and_time = item.find('div', class_='tickets_item_date').text
                date_and_time = date_and_time.replace(' /', '').split()
                date_and_time[1] = date_and_time[1].title()[:3]

                normal_date = ' '.join(date_and_time)
            except AttributeError:
                date_and_time = item.find('div', class_='home_events_item_date').text
                date, time = date_and_time.split('/')
                day, month = date.split()
                month = month.title()[:3]
                time = time.replace(' ', '')

                normal_date = day + ' ' + month + ' ' + time

            parametr_for_get_href = item.find('a').get('href')
            url = f'https://tna-tickets.ru{parametr_for_get_href}'
            soup = self.request_for_href(url)

            try:
                href = soup.select('.event_view_header .border_link')[0].get('href')
            except IndexError:
                href = soup.find('a', class_='ticket-link').get('href')
            href = f'https://tna-tickets.ru{href}'

            a_events.append([title, href, normal_date])

        return a_events

    def request_for_href(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'tna-tickets.ru',
            'referer': 'https://tna-tickets.ru/sport/akbars/',
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

        return BeautifulSoup(r.text, "lxml")

    def get_events(self, url: str):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'tna-tickets.ru',
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

        a_events = self.parse_events(soup)

        return a_events

    def body(self):
        for url in self.urls:
            a_events = self.get_events(url)

            for event in a_events:
                self.register_event(event[0], event[1], date=event[2])
