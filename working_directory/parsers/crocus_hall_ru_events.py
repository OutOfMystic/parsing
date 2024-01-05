from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils import utils


class CrocusHall(EventParser):
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://crocus-hall.ru/events/'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []

        items_list = soup.find_all('div', class_='afisha-items-list__item')

        for item in items_list:
            try:
                month_and_year = item.get('id')
                item = item.find('a', class_='card')
                if 'show-cancel' in item.get('class'):
                    continue
                if_tickets = item.find('div', class_='text-right').text.strip()
                if 'Sold out' in if_tickets or '' == if_tickets or 'Оставить заявку' in if_tickets:
                    continue
                title = item.find('h3', class_='card-title').text.strip().replace("'", '"')

                date_and_time = item.find('span', class_='date')
                date_and_time = date_and_time.find_all('span')
                day, month = date_and_time[0].text.split()
                month = month[:3].title()
                year_and_month = month_and_year.replace('item-', '')
                year = year_and_month[:4]
                time = date_and_time[1].text.replace('.', ':')

                normal_date = day + ' ' + month + ' ' + year + ' ' + time

                parametr_for_get_href = item.get('href')
                url = f'https://crocus-hall.ru{parametr_for_get_href}/'
                soup = self.request_for_href(url)

                all_date = []
                detail_active = soup.find_all('div', class_='detail')
                if len(detail_active) > 0:
                    if len(str(day)) == 1:
                        day = f'0{day}'
                    date_to_find = year_and_month + day
                    for detail in detail_active:
                        data_key = detail.get('data-key')
                        if data_key == date_to_find:
                            href = detail.find('a', class_='crocus-widget').get('href')
                            more_one_event_in_day = detail.find_all('div', class_='seans')
                            if len(more_one_event_in_day) > 0:
                                for event_in_day in more_one_event_in_day:
                                    this_date = ' '.join(normal_date.split()[:3])
                                    this_time = event_in_day.find('span', class_='time').text.replace('.', ':')
                                    this_date = this_date + ' ' + this_time
                                    href = event_in_day.find('a', class_='crocus-widget').get('href')
                                    all_date.append((this_date, href))
                            break
                else:
                    href = soup.find('a', class_='crocus-widget')
                    if href is None:
                        continue
                    href = href.get('href')

                venue = item.find('span', class_='color-light').text
                if 'Crocus City Hall' == venue:
                    venue = 'Крокус Сити Холл'
                elif 'Vegas City Hall' == venue:
                    venue = 'Vegas City Hall'
                else:
                    venue = 'Ресторан Backstage'

                if len(all_date) == 0:
                    a_events.append([title, href, normal_date, venue])
                else:
                    for date, href in all_date:
                        a_events.append([title, href, date, venue])
            except Exception as ex:
                self.warning(f'{ex} {item}')
        return a_events

    def request_for_href(self, url):
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
        r = self.session.get(url, headers=headers)

        return BeautifulSoup(r.text, "lxml")

    def get_events(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'referer': 'https://crocus-hall.ru/',
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
            if 'Детский фестиваль «Счастливое детство»' == event[0]:
                continue
            self.register_event(event[0], event[1], date=event[2], venue=event[3])
