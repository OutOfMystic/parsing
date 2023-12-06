import locale
from datetime import datetime

from bs4 import BeautifulSoup
from loguru import logger

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class CircusKislovodsk(EventParser):
    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.circus-kislovodsk.ru/'
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "sec-ch-ua": "\"Not/A)Brand\";v=\"99\", \"Google Chrome\";v=\"115\", \"Chromium\";v=\"115\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Referer": "https://ticket-place.ru/widget/1013",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "user-agent": self.user_agent
        }

    def before_body(self):
        self.session = ProxySession(self)

    @staticmethod
    def reformat_date(date):
        date = datetime.fromisoformat(date)
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        date_to_write = date.strftime("%d ") + \
            date.strftime("%b ").capitalize() + \
            date.strftime("%H:%M")
        return date_to_write

    def find_all_events(self, page):
        soup = BeautifulSoup(page.text, 'lxml')
        events = soup.select('div.ticket_item')
        events_id =[x.get('data-tp-event') for j in  [i.find_all('a') for i in events] for x in j]
        return events_id
    
    def get_info_about_event(self, id):
        url_to_api = f'https://ticket-place.ru/widget/{id}/data'
        info_about = self.session.get(url_to_api, headers=self.headers)
        info_about.encoding = 'utf-8'
        info_about = info_about.json()

        title = info_about.get("data").get("name")
        id = info_about.get("data").get("id")
        href = f'https://ticket-place.ru/widget/{id}/data|kislovodsk'
        date = self.reformat_date(info_about.get("data").get("datetime"))

        return title, href, date

    def load_all_dates(self, id):
        a_events = []
        url = f'https://ticket-place.ru/widget/{id}/similar'
        all_events_json = self.session.get(url, headers=self.headers)

        for i in all_events_json.json().get("events"):
            title = i.get("name")
            id = i.get("id")
            href = f'https://ticket-place.ru/widget/{id}/data|kislovodsk'
            date = self.reformat_date(i.get("datetime"))
            a_events.append((title, href, date))

        return a_events

    def body(self):
        page = self.session.get(self.url, headers=self.headers)
        events_ids = self.find_all_events(page)

        a_events = set()
        first_event = self.get_info_about_event(events_ids[0])
        a_events.add(first_event)

        count = 10
        while len(a_events) < len(events_ids) and count > 1:
            id = events_ids[len(a_events)]
            to_a_events = self.load_all_dates(id)
            a_events.update(to_a_events)
            count -= 1

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue='Кисловодский цирк')
        logger.debug('bodied')

            

