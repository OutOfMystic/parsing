from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession

class HcSalavatHockey(EventParser):
    proxy_check_url = 'https://tickets.hcsalavat.ru/ru'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tickets.hcsalavat.ru/ru'
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Referrer-Policy": "origin",
            'user-agent': self.user_agent
        }
       
    def before_body(self):
        self.session = ProxySession(self)


    def body(self):
        r = self.session.get(url=self.url, headers=self.headers, verify=False)
        soup = BeautifulSoup(r.text, 'lxml')

        events = soup.find_all(class_='events__item')
        
        a_events = []
        for event in events:
            title = event.find(class_='events__name').text.strip()

            time = [i.find(class_='time__text').text.strip() for i in event.find_all(class_='time')]
            time_write = f"{' '.join(time[0].split()[:3])} {time[-1]}"
            href = f"https://tickets.hcsalavat.ru/ru{event.find(class_='events__buy').get('href')}"
            a_events.append((title, href, time_write))
              
        for event in a_events:
            self.register_event(event_name=event[0], url=event[1],
                                                date=event[2], venue='УФА-АРЕНА')