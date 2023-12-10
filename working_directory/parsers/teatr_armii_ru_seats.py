from time import sleep

from bs4 import BeautifulSoup

from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils


class ArmyParser(SeatsParser):
    event = 'teatrarmii.ru'
    url_filter = lambda url: 'teatrarmii.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 3600
        self.driver_source = None
        self.event_id = self.url.split('/')[-1]
    
    def before_body(self):
        self.session = ProxySession(self)
    
    def get_xsrf_token(self, count=0):
        url = 'https://www.afisha.ru/wl/29/api?site=teatrarmii.ru'
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
    
    def get_list_with_all_seats(self, xsrf_token, count=0):
        headers = {'Accept':'application/json, text/plain, */*',
                    'Accept-Encoding':'gzip, deflate, br',
                    'Accept-Language':'en-US,en;q=0.9,ru;q=0.8',
                    'Connection':'keep-alive',
                    'Content-Type':'application/x-www-form-urlencoded',
                    'Dnt':'1',
                    'X-Xsrf-Token':xsrf_token
                    }
        url='https://www.afisha.ru/wl/29/api/events/info?lang=ru&sid='
        
       
        try:   
            resp = self.session.post(url,data={'event_id':{self.event_id}}, headers=headers)
            resp = resp.json()
            list_with_places = resp['places']
            scene = resp['event']["location_name"]
        except:
            if count < 5:
                count += 1
                self.proxy = self.controller.proxy_hub.get(url=self.proxy_check_url)
                self.session = ProxySession(self) 
                self.warning(f' cannot load {url} try +={count}')
                count += 1
                return self.get_list_with_all_seats(xsrf_token, count)
            else:
                return None
    
        return list_with_places, scene


    @staticmethod
    def get_seat_with_no_row(seat):
        #экспериментальная схема замечено
        if seat <= 12:
            return '1'
        elif seat >= 13 and seat <=24:
            return '2'
        elif seat >= 25 and seat <=36:
            return '3'
        elif seat >= 37 and seat <=42:
            return '4'
        else:
            return '5'

    def sorted_list_active_place_only(self, box: list, scene: str) -> dict[str, dict[tuple[str, str], int]]:
        tickets_data = {}
        for seat in box:
            if seat['price'] > 0:
                if seat['row'] == '--':
                    seat['row'] = self.get_seat_with_no_row(int(seat['seat']))
                try:
                    old_tickets = tickets_data[seat['sector']['name']]
                    tickets_data[seat['sector']['name']] = old_tickets | {(seat['row'],seat['seat']):seat['price']}
                except KeyError:
                    tickets_data[seat['sector']['name']] = {(seat['row'],seat['seat']):seat['price']}
        return tickets_data

    def body(self):
        XSRF_TOKEN = self.get_xsrf_token()
        list_with_all_seats, scene = self.get_list_with_all_seats(XSRF_TOKEN)
        active_seats = self.sorted_list_active_place_only(list_with_all_seats, scene)
        for sector_name, tickets in active_seats.items():
            self.register_sector(sector_name, tickets)
