import datetime
from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.utils.date import month_num_by_str
from parse_module.manager.proxy.instances import ProxySession


class OperettaParser(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.our_urls = {
        }
        self.url = 'https://mosoperetta.ru/afisha/'

    def main_page_request(self):
        headers = {
            'Host': 'mosoperetta.ru',
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        r = self.session.get(self.url, headers=headers)

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []
        month = soup.find('span', class_='b-calendar__header-item').text.strip()
        month = month[:3].capitalize()

        all_date_cells = soup.find_all('td', class_='b-calendar-table__cell')
        date_cells = [cell for cell in all_date_cells if 'is-empty' not in cell['class']]
        for date_cell in date_cells:
            date_div = date_cell.find('div', class_='b-calendar-table__date')
            day = date_div.text.strip()

            events_title_time = date_cell.find_all('div', class_='b-calendar-table__perf')

            for event_title_time in events_title_time:
                time = event_title_time.find('div', class_='time').text.split()[0].strip()
                date = self.format_date(day, month, time)

                title_href = event_title_time.find('a', class_='ellipsis order-link')

                if not title_href:
                    continue

                title = title_href.text.strip()
                href = title_href['href']
                href = 'https://mosoperetta.ru' + href

                a_events.append([title, href, date])

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def format_date(self, d, m, time):
        today = datetime.date.today()
        current_year = today.year
        current_month = today.month

        m_num = month_num_by_str[m]
        y = current_year if current_month <= m_num else current_year + 1

        return f'{d} {m} {y} {time}'

    def get_events(self, date=None):
        url = 'https://mosoperetta.ru/index.php/tools/packages/nd_theme/calendar'
        headers = {
            'Host': 'mosoperetta.ru',
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Length': '41',
            'Origin': 'https://mosoperetta.ru',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://mosoperetta.ru/afisha/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        data = {
            'theme_pkg_handle': 'nd_theme',
            'lock_minutes': '15',
        }

        if date:
            month_data = {
                'date': date,
                'dest': 'next'
            }

            data.update(month_data)

        r = self.session.post(url, headers=headers, data=data, verify=False)

        count = 5
        while not r.ok and count > 0:
            self.debug(f'{self.proxy.args = }, {self.session.cookies = } kassir events')
            self.proxy = self.controller.proxy_hub.get(self.proxy_check)
            self.session = ProxySession(self)
            r = self.session.post(url, headers=headers, data=data, verify=False)
            count -= 1

        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.parse_events(soup)
        date = soup.find('input', {'id': 'sendDate'})['value']

        return a_events, date

    def body(self):
        date = None
        a_events = []

        for i in range(3):
            next_a_events, next_date = self.get_events(date)

            date = next_date
            a_events += next_a_events

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])
