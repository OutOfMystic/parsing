import re

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession


class BiletovedParsSeats(AsyncSeatsParser):
    event = 'biletoved.com'
    url_filter = lambda url: 'biletoved.com' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1600
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

    def load_tickets(self, soup2):
        all_tickets = soup2.find_all(class_='product-modification-item')
        all_tickets_online = [i for i in all_tickets if 'Электронный билет' in i.find(class_='mobile-kind-type').text]
        a_tickets = {}
        for name in all_tickets_online:
            details = name.find(class_='kind-details').find_all(class_="kind-tr")[-1]
            options = details.find(class_='kind-name').find('span').text

            sector = options.split(':')[0]

            row = re.search(r'(?<=ряд) *\d+', options)[0].strip()

            places = re.search(r'(?<=места) *(.*)', options)[0]
            places = re.findall(r'\d+', places)
            
            price = name.find(class_='price-current').find('strong').text
            price = int(price.replace('\xa0', '').replace(' ', ''))

            for place in places:
                a_tickets.setdefault(sector, {}).update({
                    (row, place): price
                })

        return a_tickets

    @staticmethod
    def reformat_bkz(a_sectors):
        a_sectors_new = {}
        for sector, tickets in a_sectors.items():
            if sector == 'Балкон':
                for row_place, price in tickets.items():
                    row, place = map(int, row_place)
                    if row in (1,2,3,4,5,6,7):
                        new_sector_name = "Балкон (места с ограниченной видимостью)"
                        a_sectors_new.setdefault(new_sector_name, {}).update({
                            (str(row), str(place)): price
                        })
                    else:
                        a_sectors_new.setdefault(sector, {}).update({
                            (str(row), str(place)): price
                        })
            else:
                a_sectors_new.setdefault(sector, {}).update(tickets)
        return a_sectors_new
   
    async def body(self):
        if self.place == 'БКЗ Октябрьский':
            r2 = await self.session.get(url=self.url, headers=self.headers)
            soup2 = BeautifulSoup(r2.text, 'lxml')

            a_sectors = self.load_tickets(soup2)
            a_sectors = self.reformat_bkz(a_sectors)
        else:
            raise SystemError(f'need to write seats for {self.url}')

        for sector_name, tickets in a_sectors.items():
            #self.info(sector_name, len(tickets))
            self.register_sector(sector_name, tickets)
        #self.check_sectors()