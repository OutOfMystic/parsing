import re

from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils


class HcLadaHockeyTLTarena(EventParser):
    proxy_check_url = 'https://tickets.tlt-arena.ru/' 
    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.tlt-arena.ru/'
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': self.user_agent
        }

    def before_body(self):
        self.session = ProxySession(self)

    

    def body(self):
        r = self.session.get(url=self.url, headers=self.headers, verify=False)
        soup = BeautifulSoup(r.text, 'lxml')

        tables = soup.find_all('table', class_='table-choice')

        tr_box = []
        for table in tables:
            tr_box.extend([ i for i in table.find_all('tr') if i.find('td', class_='date')])
        
        a_events = []
        for event in tr_box:
            try:
                title = event.find('td').text.strip()

                date = event.find('td', class_='date').text #30 октября 2023, 19:00 (пн)
                day, month, year, time, day_name = date.split()
                full_date = f"{day.strip()} {month[:3].capitalize()} {year.strip(' ,')} {time.strip()}"

                href = event.find('a', class_='buy').get('href')
                href = f"https://tickets.tlt-arena.ru{href}"
            except Exception as ex:
                self.error(f'{ex} lada_tlt_arena_events')
            else:
                a_events.append((title, href, full_date))

        for event in a_events:
            self.register_event(event_name=event[0], url=event[1], date=event[2], venue='Лада-арена')