from datetime import datetime
import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.manager.proxy.check import SpecialConditions


class BankBiletovEvents(AsyncEventParser):
    proxy_check = SpecialConditions(url='https://afisha.yandex.ru/')
    def __init__(self, *args):
        super().__init__(*args)
        self.delay = 3600
        self.driver_source = None
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            'user-agent': self.user_agent
        }
    
    async def before_body(self):
        self.session = AsyncProxySession(self)
        self.yandex_session = AsyncProxySession(self)

    async def load_all_urls_and_dates_and_titles(self, place_url):
        r = await self.session.get(url=place_url, headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        
        box_urls_and_dates = []
        box_events = soup.find(attrs={'id':'show-events'})
        events = box_events.find_all(class_='event')
        scheme_url = 'https://bankbiletov.ru'
        elements_with_tag_a = [i for i in events if i.find('a')]
        for element in elements_with_tag_a:
            title = element.find(class_='title').text.strip()
            a_tag = element.find('a')
            url = f"{scheme_url}{a_tag.get('href')}"
            date_list = element.find(class_='date').text.split()
            date_to_write = self.make_date(date_list)

            box_urls_and_dates.append((url, date_to_write, title))
        return box_urls_and_dates

    @staticmethod
    def make_date(date_list: list)-> str:
        '''бро, если будущий месяц имеет индекс в списке short_months_in_russian 
                меньше чем текущий - то это следующий год'''
        
        day, month, time, day_name = date_list  #['2', 'фев', '19:00', 'Пт']
        month.lower().replace('мая','май')

        short_months_in_russian = [
        "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        
        date_now = datetime.now()
        current_year = date_now.year
        current_month = date_now.month-1
        
        month_find = short_months_in_russian.index(month)

        if month_find < current_month:
                current_year += 1

        return f"{day} {month.capitalize()} {current_year} {time}"
    
    async def make_events_to_write_in_db(self, event_urls):
        a_events = []
        for url, date, title in event_urls:
            url_to_db, event_params = await self.load_yandex_session(url)
            a_events.append((title, url_to_db, date, event_params))
        return a_events

    async def load_yandex_session(self, url):
        r1 = await self.session.get(url, headers=self.headers)
        soup1 = BeautifulSoup(r1.text, 'lxml')

        all_scripts = soup1.find_all('script')
        dealer_script = [i for i in all_scripts if 'YandexTicketsDealer' in i.text]
        if len(dealer_script) >= 1:
            dealer_script = dealer_script[0]
        else:
            self.info('Look at script, you must find yandex_session_key')
        
        clientKey = re.search(r"setDefaultClientKey', *'([\w\-]+)", dealer_script.text).group(1)
        sessionKey = re.search(r"dealer.Widget\('([\w\-\@]+)", dealer_script.text).group(1)

        sessionKeyNew = False
        for i in range(0,40):
            yandex = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{sessionKey}?clientKey={clientKey}&req_number={i}'
            sessionKeyNew = await self.yandex_request(yandex)
            if sessionKeyNew:
                break

        if sessionKeyNew:
            url_to_database = f'https://widget.afisha.yandex.ru/w/sessions/{sessionKeyNew}?clientKey={clientKey}&embed=true&widgetName=w1'
            event_params = str({'client_key': clientKey,
                                            'session_id': sessionKeyNew}).replace("'", "\"")
        else:
            url_to_database = f'https://widget.afisha.yandex.ru/w/sessions/{sessionKey}?clientKey={clientKey}&embed=true&widgetName=w1'
            event_params = str({'client_key': clientKey,
                                'session_id': sessionKey}).replace("'", "\"")
            
        return url_to_database, event_params


    async def yandex_request(self, url):
        r2 = await self.yandex_session.get(url, headers=self.headers)
        if r2.status_code == 200 and  'application/json' in r2.headers.get('Content-Type'):
            try:
                answer = r2.json()
                sessionKey = answer.get('result').get('session').get('key')
            except KeyError:
                return False
            else:
                return sessionKey
            

    async def body(self):
        all_urls = [
            ('https://bankbiletov.ru/venue/33067', 'Симфоропольский цирк им. Тезикова'),
        ]
        for place_url, venue in all_urls:
            try:
                event_urls = await self.load_all_urls_and_dates_and_titles(place_url)
                #self.info(event_urls)

                a_events = await self.make_events_to_write_in_db(event_urls)

            except Exception as ex:
                self.warning(f'Wrong in place {venue}: {place_url} {ex}')
                raise
            else:
                for event in a_events:
                    #self.info(event)
                    self.register_event(event[0], event[1], date=event[2],
                                            event_params=event[3], venue=venue)
            