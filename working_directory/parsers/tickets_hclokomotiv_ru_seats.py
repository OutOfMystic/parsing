import json
from bs4 import BeautifulSoup
from parse_module.coroutines import AsyncSeatsParser
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Cska(AsyncSeatsParser):
    event = 'tickets.hclokomotiv.ru'
    url_filter = lambda url: 'tickets.hclokomotiv.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_seats(self, soup):
        get_all_view_id = soup.find_all('g', attrs={'mode': '1'})
        get_all_text = soup.select('svg > text')

        count_text = 0
        all_view_id = {}
        for view_id in get_all_view_id:
            if view_id.get('free') != '0':
                sector = view_id.find('text')
                if sector is None:
                    sector = get_all_text[count_text]
                    count_text += 1
                if sector is not None:
                    sector = sector.text
                    if sector.isdigit():
                        sector = 'Сектор ' + sector
                    all_view_id[view_id.get('view_id')] = sector

        # csrf_token = soup.find('input').get('value')
        total_sector = []
        for view_id, sector_name in all_view_id.items():
            csrf_token = '3p19HqpKF8jdvkM3lJcgwcVoe9-4Q4Ij5gyZGaYMDKGNpCd18B5cgrLcbk3XrnaX8TkJl-Bx-BCeTtZM0EVpxg=='
            data = {
                "event_id": self.url[-3:],
                "view_id": view_id,
                "clear_cach": "false",
                "_csrf-frontend": csrf_token
            }
            url = 'https://tickets.hclokomotiv.ru/event/get-actual-places'
            json_data = self.get_data(url=url, data=data, csrf_token=csrf_token)
            data = json.loads(json_data)

            zones = {}
            get_zones = data.get('zones')
            for zone in get_zones:
                if zone.get('free') != 0:
                    str_zone = str(zone.get('zone'))
                    price_zone = int(zone.get('price_view_id'))
                    zones[str_zone] = price_zone

            places = data.get('places')
            values = places.get('values')

            ticets_in_sector = {}
            for value in values:
                place_data = value.get('id')
                index_sector = place_data.index('s')
                index_row = place_data.index('r')
                index_seat = place_data.index('p')
                # sector = place_data[index_sector + 1:index_row]
                row = place_data[index_row + 1:index_seat]
                seat = place_data[index_seat + 1:]

                price_zone = str(value.get('z'))
                price = zones.get(price_zone)
                ticets_in_sector[(row, seat)] = price

            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": ticets_in_sector
                }
            )

        return total_sector

    def get_data(self, url, data, csrf_token):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'tickets.hclokomotiv.ru',
            'Cache-Control': 'no-cache',
            'Cookie': '_csrf-frontend=3251f61bde014dd3f8cc19fe64618b091b05078ef5f1eca94822eef09777cbada%3A2%3A%7Bi%3A0%3Bs%3A14%3A%22_csrf-frontend%22%3Bi%3A1%3Bs%3A32%3A%22S9ZkZTKJob-zC9VV4QrHX2z3xBOUvIeg%22%3B%7D; city_id=3; session=0lntfljg5mj7n7l88gli0lj36c'
        }
        r = self.session.get(url, headers=headers, data=data)
        return r.text

    def request_parser(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'referer': 'https://tickets.hclokomotiv.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def get_seats(self):
        soup = self.request_parser(url=self.url)

        a_events = self.parse_seats(soup)

        return a_events

    async def body(self):
        all_sectors = self.get_seats()

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
