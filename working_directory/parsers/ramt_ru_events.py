import re
import json
from datetime import datetime

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.utils import utils


class AfishaEvents(AsyncEventParser):
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.domain = 'https://ramt.ru/afisha/'
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Referrer-Policy": "origin",
            'User-Agent': self.user_agent
        }
        

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def make_date(date):
        '''бро, если будущий месяц имеет индекс в списке short_months_in_russian 
            меньше чем текущий - то это следующий год'''
        date_now = datetime.now()
        current_year = date_now.year
        current_month = date_now.month-1
        short_months_in_russian = [
        "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

        day_month, time = map(lambda el: el.get_text() ,date.find_all(class_='afisha-card__date'))
        day, month, *other = map(str.strip ,day_month.split())
        month = month[:3].lower().replace('мая','май')
        month_find = short_months_in_russian.index(month)
        time = time.strip()

        if month_find < current_month:
            current_year += 1

        return f"{day} {month.capitalize()} {current_year} {time}"
    
    def take_all_sessions(self, soup):
        all_events = soup.find_all('div', class_='afisha-list__item')
        events_with_details = [i for i in all_events if i.find(class_='afisha-card__details')]
        a_box = {}
        for event in events_with_details:
            title = event.find(class_='afisha-card__title').text.strip()

            date = event.find(class_='afisha-card__info')
            date_to_write = self.make_date(date)

            ticket_wrap = event.find(class_='afisha-card__tickets-wrap')
            if ticket_wrap:
                ticket = ticket_wrap.find(lambda tag: 'ticket' in tag.name)
                session_id = ticket.get('data-session-id')
            else:
                continue
            a_box[session_id] = (title, date_to_write, session_id)
        return a_box

    async def request_to_yandex(self, box, client_key):
        a_events = []
        params = {
            'sessions_ids' : box,
            'clientKey': client_key
        }
        url= 'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/sale-available'
        r2 = await self.session.get(url=url, headers=self.headers, params=params)

        session_box = double_split(r2.text, '"sessions":', ']')
        session_box = json.loads(session_box+']')

        for event in session_box:
            if event.get("saleStatus") == 'available':
                title, date, session_id = self.session_dict.get(event['key'])
                href = f'https://widget.afisha.yandex.ru/w/sessions/{session_id}?clientKey={client_key}'
                a_events.append((title, date, href, session_id, client_key))
        return a_events


    async def body(self):
        r = await self.session.get(url=self.domain, headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')

        self.session_dict = self.take_all_sessions(soup)

        client_key = double_split(r.text, "setDefaultClientKey',", "']")
        client_key = client_key.strip("' ")

        params_count = 40    
        sesson_box = list(self.session_dict.keys())
        a_events = []
        for i in range(0, len(sesson_box), params_count):
            box = sesson_box[i:i+params_count]
            cut_events = await self.request_to_yandex(box, client_key)
            a_events.extend(cut_events)
            
        for event in a_events:
            event_params = {"client_key":event[4],
                            "session_id":event[3]}
            self.register_event(event[0], event[2], date=event[1],
                                  event_params=str(event_params).replace("'", "\""), venue='РАМТ')
            
