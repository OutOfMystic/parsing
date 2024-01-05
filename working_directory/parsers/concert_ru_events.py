from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Concert(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.concert.ru'

    def before_body(self):
        self.session = ProxySession(self)
        self.our_places_data = [
            'https://www.concert.ru/shou/',
            # 'https://www.concert.ru/teatry/',
            # 'https://www.concert.ru/kontserty/',
            # 'https://www.concert.ru/sport/',
            # 'https://www.concert.ru/detyam/',
            # 'https://www.concert.ru/raznoe/'
        ]

    def parse_page(self, soup):
        events = soup.find_all('div', class_='event')
        for event in events:
            title_and_href = event.find('a', class_='event__name')
            title = title_and_href.text.replace("'", '"')
            href = title_and_href.get('href')

            venue = event.find('div', class_='event__type').text.strip()

            url = 'https://www.concert.ru' + href
            soup_for_event = self.get_all_events_in_this_event(url)

            all_date_for_event = soup_for_event.select('.eventTabs__table tr[class^="tr_"]')
            for event_date in all_date_for_event:
                new_venue = event_date.find_all('span', class_='eventTabs__tableWeekday')

                link_to_tickets = event_date.find('a', class_='buyButton')
                if link_to_tickets.text.strip() != 'Купить':
                    continue
                link_to_tickets = link_to_tickets.get('href')
                url_to_tickets = 'https://www.concert.ru' + link_to_tickets

                date = link_to_tickets.split('/')[-2].split('-')
                if 'open' in date:
                    continue
                date[1] = month_list[int(date[1])]
                normal_date = ' '.join(date[:4]) + ':' + date[-1]

                if len(new_venue) == 0:
                    normal_venue = venue
                else:
                    normal_venue = new_venue[-1].text.strip()
                yield [title, url_to_tickets, normal_date, normal_venue]

    def parse_events(self, url):
        soup = self.get_all_events_in_this_event(url)
        new_page = soup.find('a', class_='pagination__next').get('href')
        yield self.parse_page(soup)
        while True:
            if new_page == '#':
                break
            url = 'https://www.concert.ru' + new_page
            soup = self.get_all_events_in_this_event(url)
            yield self.parse_page(soup)
            new_page = soup.find('a', class_='pagination__next').get('href')

    def get_all_events_in_this_event(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'www.concert.ru',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
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
        return BeautifulSoup(r.text, 'lxml')

    def body(self):
        a_events = []
        for url in self.our_places_data:
            for events in self.parse_events(url):
                for event in events:
                    if event not in a_events:
                        if 'Красная площадь' == event[3]:
                            event[3] = 'Кремлевский дворец'
                        self.register_event(event[0], event[1], date=event[2], venue=event[3])
                        a_events.append(event)

