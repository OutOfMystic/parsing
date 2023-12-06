from bs4 import BeautifulSoup
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split


class TNA(SeatsParser):
    event = 'tna-tickets.ru'
    url_filter = lambda url: 'tna-tickets.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, all_sectors):
        for sector in all_sectors:
            if 'Фан-зона' in sector['name'] and 'сторона' in sector['name']:
                split_sector_name = sector['name'].split()
                sector['name'] = split_sector_name[0] + ', ' + ' '.join(split_sector_name[1:])

    def parse_seats(self, soup):
        total_sector = []

        event_id = self.url.split('=')[-1]
        # access_token = 'f82ClAPmEt2QvK66XPzZgzbAMfh1WlR_'
        script_with_token = soup.select('body script')[0].text
        access_token = double_split(script_with_token, 'API_ACCESS_TOKEN:"', '"}')
        url_to_data = f'https://api.tna-tickets.ru/api/v1/booking/{event_id}/sectors?access-token={access_token}'
        json_data = self.get_price_list_or_seats_or_sectors(url_to_data)

        all_sectors = json_data.get('result')
        for sector in all_sectors:
            sector_name = sector.get('name')
            sector_id = sector.get('sector_id')

            url = f'https://api.tna-tickets.ru/api/v1/booking/{event_id}/seats-price?access-token={access_token}&sector_id={sector_id}'
            get_price_list = self.get_price_list_or_seats_or_sectors(url)

            price_data = {}

            price_list = get_price_list.get('result')
            for price in price_list:
                price_count = int(price.get('price').split('.')[0])
                price_id = str(price.get('zone_id'))
                price_data[price_id] = price_count


            url = f'https://api.tna-tickets.ru/api/v1/booking/{event_id}/seats?access-token={access_token}&sector_id={sector_id}'
            get_seats_list = self.get_price_list_or_seats_or_sectors(url)

            total_seats_row_prices = {}

            all_seats_in_sector = get_seats_list.get('result')
            for seat_in_sector in all_seats_in_sector:
                try:
                    sector_row_seat = seat_in_sector.get('name')
                    sector_and_row_seat = sector_row_seat.split(' Ряд ')
                    row, seat = sector_and_row_seat[-1].split(' Место ')
                except ValueError:  # Фан-зона
                    continue

                price = seat_in_sector.get('zone_id')
                price = price_data.get(price)

                if price is not None:
                    total_seats_row_prices[(row, seat)] = price

            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def get_price_list_or_seats_or_sectors(self, url):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'api.tna-tickets.ru',
            'origin': 'https://tna-tickets.ru',
            'referer': 'https://tna-tickets.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        return r.json()

    def request_parser(self, url):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'tna-tickets.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def get_seats(self):
        soup = self.request_parser(url=self.url)

        a_events = self.parse_seats(soup)

        return a_events

    def body(self):
        all_sectors = self.get_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])