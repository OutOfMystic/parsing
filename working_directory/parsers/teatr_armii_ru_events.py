from datetime import datetime
import locale

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils


class Parser(EventParser):

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 1200
        self.driver_source = None
        self.url = 'https://www.afisha.ru/wl/29/api?site=teatrarmii.ru'
    
    def before_body(self):
        self.session = ProxySession(self)

    def get_xsrf_token(self, url):
        headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Encoding':'gzip, deflate, br',
                    'Accept-Language':'en-US,en;q=0.9,ru;q=0.8',
                    'Cache-Control':'max-age=0',
                    'Connection':'keep-alive',
                    'User-Agent': self.user_agent}

        get_xsrf_token = self.session.get(url=url, headers=headers)
        try:
            # soup = BeautifulSoup(get_xsrf_token.text, 'lxml')
            # XSRF_TOKEN = soup.find(attrs={'name':'csrf-token'}).get('content')
            XSRF_TOKEN = get_xsrf_token.headers['Set-Cookie'].split(';')[0].split('=')[-1]
        except KeyError:
            if count < 7:
                count += 1
                self.warning(f' try to find XApplication token ArmiiTeatr + {count}')
                self.proxy = self.controller.proxy_hub.get(url=self.proxy_check_url)
                self.session = ProxySession(self)
                return self.get_xsrf_token(count)
            else:
                return None
            
        return XSRF_TOKEN

    def get_all_events(self, xsrf_token, count=0):
        headers = {'Accept':'application/json, text/plain, */*',
                    'Accept-Encoding':'gzip, deflate, br',
                    'Accept-Language':'en-US,en;q=0.9,ru;q=0.8',
                    'Connection':'keep-alive',
                    'Content-Length':'0',
                    'Dnt':'1',
                    'X-Xsrf-Token':xsrf_token
                    }

        events_url = 'https://www.afisha.ru/wl/29/api/events?lang=en-US&sid='
        current_data = {'lang': 'ru'}
        res = self.session.post(events_url, headers=headers, data=current_data)
        try:
            json = res.json()
            return json
        except Exception as ex:
            count += 1
            self.error(f' cannot load {events_url} {ex} try +={count}')
            self.proxy = self.controller.proxy_hub.get(url=self.proxy_check_url)
            self.session = ProxySession(self)
            return self.get_all_events(xsrf_token, count)
    
    @staticmethod
    def work_with_data(date:str):
        '''time in ISO FORMAT -> 2021-08-10 18:20:34'''
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        _date = datetime.fromisoformat(date)
        day_month = f"{str(_date.day)} {_date.strftime('%b').capitalize()}"
        time = _date.strftime('%H:%M')
        date_to_write = f'{day_month} {_date.year} {time}' # 30 Июн 2023 19:30
        return date_to_write
    
    def make_event(self, event):
        
        title = event['name'].strip()
        href = self.url + f"#/place/{event['id']}"
        date = self.work_with_data(event['date'])
        scene = f"Театр Российской армии - {event['location_name'].strip(' .')}"
        
        return title, href, date, scene

    def body(self):
        XSRF_TOKEN = self.get_xsrf_token(self.url)
        all_events_list = self.get_all_events(XSRF_TOKEN)

        for event in all_events_list:
            event_to_write = self.make_event(event)
            self.register_event(event_to_write[0], event_to_write[1],
                                date=event_to_write[2])
