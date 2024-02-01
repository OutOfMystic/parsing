from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession


class XKAvangarg(AsyncSeatsParser):
    url_filter = lambda url: 'tickets.hawk.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, all_sectors):
        for sector in all_sectors:
            if 'Сектор' not in sector['name']:
                if 'К' in sector['name']:
                    split_sector_name = sector['name'].split('К')
                    sector['name'] = split_sector_name[0] + 'K' + split_sector_name[1]
                if 'О' in sector['name']:
                    split_sector_name = sector['name'].split('О')
                    sector['name'] = split_sector_name[0] + 'O' + split_sector_name[1]
                if 'С' in sector['name']:
                    split_sector_name = sector['name'].split('С')
                    sector['name'] = split_sector_name[0] + 'C' + split_sector_name[1]
                if 'М' in sector['name']:
                    split_sector_name = sector['name'].split('М')
                    sector['name'] = split_sector_name[0] + 'M' + split_sector_name[1]
            if 'Сектор G-Drive Бизнес-клуб' in sector['name']:
                sector['name'] = 'Сектор G Drive Бизнес клуб'
            if 'Сектор FONBET Бизнес-клуб' in sector['name']:
                sector['name'] = 'Сектор FONBET Бизнес клуб'

    async def parse_seats(self, json_data):
        total_sector = []

        all_sectors = json_data.get('availSectors')

        for sector in all_sectors:
            sector_name = sector.get('name')
            param_for_request = sector.get('id')

            first_param_for_request = self.url.split('/')[-3]
            if 'Ложа' in sector_name:
                url = f'https://tickets.hawk.ru/webapi/seats/schema/{first_param_for_request}/{param_for_request}/lounge'
                json_data_for_this_sector = await self.request_for_seats_in_sector(url)

                count_seats = json_data_for_this_sector.get('quant')
                if count_seats > 0:
                    row = '1'
                    seat = '1'

                    count_seats = json_data_for_this_sector.get('capacity')
                    price = json_data_for_this_sector.get('pricePerSeat')
                    price = int(price * count_seats)

                    total_sector.append(
                        {
                            "name": sector_name,
                            "tickets": {(row, seat): price}
                        }
                    )
                    continue
            url = f'https://tickets.hawk.ru/webapi/seats/schema/{first_param_for_request}/{param_for_request}/build?'
            json_data_for_this_sector = await self.request_for_seats_in_sector(url)

            price_list = {}

            json_price_list = json_data_for_this_sector.get('allPrices')
            for price in json_price_list:
                price_id = str(price.get('zoneId'))
                price_count = int(price.get('price'))
                price_list[price_id] = price_count

            table_data = json_data_for_this_sector.get('seatSchemaHtml')
            table_data = BeautifulSoup(table_data, 'xml')

            total_seats_row_prices = {}

            all_row_in_this_sector = table_data.select('tr[name^="Ряд"]')
            for row_in_table in all_row_in_this_sector:
                active_seat_in_row = row_in_table.select('td[zone_id]')
                if len(active_seat_in_row) > 0:
                    row = row_in_table.get('name').split()[-1]
                    for seat_in_row in active_seat_in_row:
                        price_id_for_seat = str(seat_in_row.get('zone_id'))
                        price = price_list[price_id_for_seat]
                        seat = seat_in_row.text
                        total_seats_row_prices[(row, seat)] = price

            if total_seats_row_prices:
                total_sector.append(
                    {
                        "name": sector_name,
                        "tickets": total_seats_row_prices
                    }
                )

        return total_sector

    async def request_for_seats_in_sector(self, url):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'tickets.hawk.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers, ssl=False)
        return r.json()

    async def request_parser(self, url, data):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            # 'content-length': '16',
            'content-type': 'application/json',
            'host': 'tickets.hawk.ru',
            'origin': 'https://tickets.hawk.ru',
            # 'referer': 'https://tickets.hawk.ru/sectors/840',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = await self.session.post(url, headers=headers, json=data, ssl=False)
        return r.json()

    async def get_seats(self):
        data = {"seasonIds":[]}
        json_data = await self.request_parser(url=self.url, data=data)

        a_events = await self.parse_seats(json_data)

        return a_events

    async def body(self):
        all_sectors = await self.get_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            if '114 Айс Бункер клуб' in sector['name']:
                continue
            #self.debug(sector['name'], len(sector['tickets']))
            self.register_sector(sector['name'], sector['tickets'])
