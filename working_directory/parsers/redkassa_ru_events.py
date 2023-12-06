from bs4 import BeautifulSoup
from parse_module.models.parser import EventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession


class Redkassa(EventParser):

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.urls = [
            'https://redkassa.ru/concerts?sorting=bydate',
            'https://redkassa.ru/show?sorting=bydate'
            # 'https://redkassa.ru/theatre?sorting=bydate'
        ]

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, start_url):
        a_events = []

        count_page = 1
        while True:
            url = start_url + f'&page={count_page}'
            soup = self.requests_to_events(url)
            count_page += 1

            all_events = soup.select('li.theatre-list__item')
            if len(all_events) == 0:
                break

            for event in all_events:
                check_price = event.find('p', class_='event-snippet__price')
                if check_price is None:
                    continue

                title_and_href = event.find('a', class_='event-snippet__title')
                title = title_and_href.text.strip()
                title = title.replace("'", '"')

                date = event.find('span', class_='event-snippet__info-item').text.strip()
                if 'с' in date and 'по' in date:
                    normal_date = None
                else:
                    date = date.split('.')
                    date[1] = month_list[int(date[1])]
                    normal_date = ' '.join(date)

                href = title_and_href.get('href')
                href = f'https://redkassa.ru{href}'
                soup = self.requests_to_events(href)

                if normal_date is None:
                    dates_and_venues = soup.select('tr.event-tickets__row')
                    for date_and_venue in dates_and_venues:
                        href = date_and_venue.find('a', class_='event-tickets__btn')
                        if href is None:
                            continue
                        href = href.get('href')

                        date = date_and_venue.find('td', class_='event-tickets__col--title').text.strip()
                        date = date.split(',')[0].split()
                        date[1] = date[1].title()[:3]

                        time = date_and_venue.find('td', class_='event-tickets__col--time').text.strip()
                        normal_date = ' '.join(date) + ' ' + time

                        venue = date_and_venue.find('span', class_='bf-sector-title').text.strip()
                        venue = venue.replace("'", '"')

                        a_events.append([title, href, normal_date, venue])
                else:
                    venue = soup.find('a', class_='event-header__location-link').text.strip()
                    venue = venue.replace("'", '"')

                    a_events.append([title, href, normal_date, venue])

        return a_events

    def requests_to_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
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
        events_is_register = []
        for url in self.urls:
            a_events = self.parse_events(url)

            for event in a_events:
                if event not in events_is_register:
                    self.register_event(event[0], event[1], date=event[2], venue=event[3])
                    events_is_register.append(event)
