import re

from bs4 import BeautifulSoup

from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils


class KVNParser(EventParser):
    proxy_check = NormalConditions()
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 2200
        self.driver_source = None
        self.url = 'https://domkvn.ru/afisha-1.html'
    
    def before_body(self):
        self.session = ProxySession(self)

    @staticmethod
    def date_reformat(date):
        #16 декабря в 18:30
        day, month, nothing, time = date.split()
        return f"{day} {month[:3].capitalize()} {time}"

    def get_url(self, url):
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
        r = self.session.get(url=url, headers=headers)
        return r
    
    def find_all_events(self, soup):
        kvn = soup.find_all(class_=re.compile(r'cat-Билеты-на-КВН'))
        a_events = []
        for event in kvn:
            try:
                title = event.find('h3', class_='mwall-title').text.strip()
                data_id = event.get('data-id')
                href_url = f"https://core.domkvn.ubsystem.ru/uiapi/event/ext-id-sale-status?glue=|&ext_ids={data_id}"
                
                href_json = self.get_url(href_url).json()
                href_id = href_json.get(data_id).get('id')
                href = f"https://core.domkvn.ubsystem.ru/uiapi/event/scheme?id={href_id}"
            
            
                date = self.date_reformat(event.find(class_='mwall-date').text.strip())
                
                a_events.append((title, href, date))
            except:
                self.warning(f' cannot load KVNevent')
                continue

        return a_events

    def body(self):
        r = self.get_url(self.url)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.find_all_events(soup)

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])
