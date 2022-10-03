from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from bs4 import BeautifulSoup
import re

class Parser(SeatsParser):
    event = 'tickets-star.com'
    url_filter = lambda event: 'tickets-star.com' in event

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 60
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def place_map(self,soup):
        s = []
        place1 = soup.find_all('div', class_='place1')
        for place in place1:
            t = place.get('title').translate({ord(i): None for i in '<strong><br/>'})
            print(t)
            sector = t.split('ряд')[0].strip()
            row = (' '.join(re.findall(r'ряд([^<>]+),', t))).strip()
            seat = (' '.join(re.findall(r'место([^<>]+) Стоимость', t))).strip()
            price = (' '.join(re.findall(r'Стоимость:([^<>]+) руб.', t))).strip()
            s.append([sector, row, seat, price])
        return s

    def place_btn(self,soup):
        s = []
        btns = soup.find_all('a', class_='btn')
        for btn in btns:
            if btn.text == 'выбрать билеты':
                resp_btn = self.session.get('https://www.tickets-star.com' + btn.get('href'))
                soup_btn = BeautifulSoup(resp_btn.text, 'lxml')
                borders = soup_btn.find_all('td', class_='table_border')
                for border in borders:
                    s.append(border.text.strip())
        s = list(filter(lambda x: x != 'положить в корзину', s))
        s = [s[x:4 + x] for x in range(0, len(s), 4)]

        return s

    def get_places(self):
        resp = self.session.get(self.url, headers={'user-agent': 'Custom'})
        soup = BeautifulSoup(resp.text, 'lxml')
        map_s = soup.find_all('div', class_='Map')
        if map_s:
            s = self.place_map(soup)
        else:
            s = self.place_btn(soup)
        return s

    def body(self):
        sector = []
        places = self.get_places()

        for place in places:
            if place[0] not in sector:
                sector.append(place[0])

        for each_sector in sector:
            seats = {}
            for section, row, seat, price in places:
                if each_sector == section:
                    seats[row, seat] = price
            self.register_sector(each_sector, seats)

