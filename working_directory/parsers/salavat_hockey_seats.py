import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.manager.proxy.sessions import AsyncProxySession


class Hc_Salavat_Seats(AsyncSeatsParser): 
    proxy_check = NormalConditions()
    event = 'https://tickets.hcsalavat.ru/ru'
    url_filter = lambda url: 'hcsalavat.ru' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 3200
        self.driver_source = None
        self.event_id_ = self.url.split('/')[-1]
        self.headers1 = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Referer": "https://tickets.hcsalavat.ru/ru/",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': self.user_agent
            }
       
    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def reformat_seats(name):
        if 'ровень' in name:
            name = re.search(r'Сектор \d+', name)[0]
        elif 'vip' in name.lower():
            num = name.split()[-1].strip()
            name = f"VIP-ложа №{num}",
        elif 'ложа' in name.lower():
            num = name.split()[-1].strip()
            name = f'Ложа №{num}'
        return name

    async def load_zones(self, csrf_token):
        headers2 =  {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-csrf-token": csrf_token,
            "x-requested-with": "XMLHttpRequest",
            "Referer": self.url,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
            }
        
        url_zones = f"https://tickets.hcsalavat.ru/event/get-zones?event_id={self.id}"
        r2 = await self.session.get(url=url_zones, headers=headers2, ssl=False)

        zones = {}
        for i in r2.json()['zones'].items():
            zones[int(i[0])] = int(i[1].get('price'))

        #{64: 400, 65: 450, 75: 450, 69: 450, ...}
        return zones

    async def load_one_zone_tickets(self, zone, csrf_token):
        headers3 = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            "sec-ch-ua-mobile": "?0",
            'sec-ch-ua-platform': '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-csrf-token": csrf_token,
            "x-requested-with": "XMLHttpRequest",
            "Referer": self.url,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        }

        url_post = 'https://tickets.hcsalavat.ru/event/get-actual-places'
        data = {'event_id': self.id,
           'view_id': zone,
           'clear_cache':'false',
           'csrf-frontend': csrf_token}
        r3 = await self.session.post(url=url_post, headers=headers3, data=data, ssl=False)

        status = r3.json()['places']['type']
        seat_name = self.reformat_seats(self.sectors_info[zone])
        if status == 'busy':
            busy_seats =  set(i['id'] for i in r3.json()['places']['values'])
            get_svg = 'https://tickets.hcsalavat.ru/event/get-svg-places'
            r4 = await self.session.post(url=get_svg, headers=headers3, data=data, ssl=False)
            for i in r4.json()["places"].items():
                places = set(i[1]).difference(busy_seats)
                price = self.zones.get(int(i[0]))
                tickets = {}
                for j in places:
                    row = re.search(r'(?<=r)\d+', j)[0]
                    place = re.search(r'(?<=p)\d+', j)[0]
                    tickets.update({
                        (str(row), str(place)) : int(price)
                    })
                self.a_sectors.setdefault(seat_name, {}).update(tickets)

        elif status == 'free':
            tickets = {}
            for i in r3.json()['places']['values']:
                row = re.search(r'(?<=r)\d+', i['id'])[0]
                place = re.search(r'(?<=p)\d+', i['id'])[0]
                price = self.zones.get(int(i['z']))
                tickets.update({
                        (str(row), str(place)) : int(price)
                    })
            self.a_sectors.setdefault(seat_name, {}).update(tickets)

        
    async def body(self) -> None:
        self.id = self.url.split('=')[-1]
        r1 = await self.session.get(url=self.url, headers=self.headers1, ssl=False)
        soup = BeautifulSoup(r1.text, 'lxml')
        csrf_token = soup.find('meta', {'name':'csrf-token'}).get('content')

        g = soup.find_all('g', {'free':lambda s: s and int(s) > 0})
        self.sectors_info = {int(i.get('view_id')): i.get('sector_name') for i in g}

        self.zones = await self.load_zones(csrf_token)

        self.a_sectors = {}
        for zone in self.sectors_info.keys():
            try:
                await self.load_one_zone_tickets(zone, csrf_token)
            except Exception as ex:
                self.error(f"{ex}cannot load one of the sectors")

        for sector, tickets in self.a_sectors.items():
            #self.debug(sector, len(tickets))
            self.register_sector(sector, tickets)
        #self.check_sectors()

