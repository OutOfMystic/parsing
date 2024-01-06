from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class XKMetalurg(AsyncSeatsParser):
    event = 'tickets.metallurg.ru'
    url_filter = lambda url: 'tickets.metallurg.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def parse_seats(self, json_data):
        total_sector = []

        all_sectors = json_data.get('availSectors')

        for sector in all_sectors:
            sector_name = sector.get('name')
            param_for_request = sector.get('id')

            first_param_for_request = self.url.split('/')[-3]
            url = f'https://tickets.metallurg.ru/webapi/seats/schema/{first_param_for_request}/{param_for_request}/build'
            json_data_for_this_sector = self.request_for_price_in_sector(url)

            price_list = {}

            json_price_list = json_data_for_this_sector.get('seatSchemaPricesLegend')
            for price in json_price_list:
                price_id = str(price.get('zoneId'))
                price_count = int(price.get('price'))
                price_list[price_id] = price_count

            url = f'https://tickets.metallurg.ru/webapi/seats/{first_param_for_request}/{param_for_request}/available/list'
            json_data_for_this_sector = self.request_for_seats_in_sector(url)

            total_seats_row_prices = {}

            for seat_data in json_data_for_this_sector:
                row_and_seat = seat_data.get('name').split()
                row = row_and_seat[3]
                if sector_name == 'Ресторан':
                    row = '1'
                seat = row_and_seat[-1]
                price_id = str(seat_data.get('zoneId'))
                price = price_list.get(price_id)
                if price:
                    total_seats_row_prices[(row, seat)] = price

            if total_seats_row_prices:
                total_sector.append(
                    {
                        "name": sector_name,
                        "tickets": total_seats_row_prices
                    }
                )

        return total_sector

    def request_for_seats_in_sector(self, url):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'content-length': '2',
            'content-type': 'application/json',
            'host': 'tickets.metallurg.ru',
            'origin': 'https://tickets.metallurg.ru',
            'referer': 'https://tickets.metallurg.ru/calendar/928/18510',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = await self.session.post(url, headers=headers, json={})
        return r.json()

    def request_for_price_in_sector(self, url):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'tickets.metallurg.ru',
            'referer': 'https://tickets.metallurg.ru/calendar/928/18510',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        return r.json()

    def request_parser(self, url, data):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'content-length': '19',
            'content-type': 'application/json',
            'host': 'tickets.metallurg.ru',
            'origin': 'https://tickets.metallurg.ru',
            'referer': 'https://tickets.metallurg.ru/calendar/928',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = await self.session.post(url, headers=headers, json=data, verify=False)
        return r.json()

    def get_seats(self):
        data = {"searchFilter": []}
        json_data = self.request_parser(url=self.url, data=data)

        a_events = self.parse_seats(json_data)

        return a_events

    async def body(self):
        all_sectors = self.get_seats()

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
