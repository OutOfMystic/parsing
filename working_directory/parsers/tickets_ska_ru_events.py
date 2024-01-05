from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Cska(EventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.ska.ru'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []

        for event_card in soup.find_all('li', class_='tickets__item'):
            try:
                href = event_card.find('a', class_='ticket__buy')
                if href:
                    date_and_time = event_card.find('div', class_='ticket__date').text.strip().split(' / ')

                    month = month_list[int(event_card.get('id')[4:6])]
                    date = date_and_time[0].split()[0] + ' ' + month + ' ' + event_card.get('id')[:4] + ' ' + date_and_time[2]

                    title = event_card.find_all('span', class_='ticket__team-name')
                    first_command = title[0].text.strip()
                    second_command = title[1].text.strip()
                    if first_command and second_command:
                        title = first_command + ' - ' + second_command
                    elif not second_command:
                        title = first_command
                    elif not first_command:
                        title = second_command

                    href = self.url + href.get('href')

                    venue = event_card.find('div', class_='ticket__adress').text.strip().split(',')[0] + ' (ХКСКА)'

                    a_events.append([title, href, date, venue])
            except:
                continue

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def get_events(self):
        url = self.url
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'tickets.ska.ru',
            'sec-ch-ua': '"Chromium";v="106", "Yandex";v="22", "Not;A=Brand";v="99"',
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
        a_events = self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue=event[3])