from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from bs4 import BeautifulSoup
from parse_module.utils.parse_utils import double_split


class Redkassa(AsyncSeatsParser):
    event = 'redkassa.ru'
    url_filter = lambda url: 'redkassa.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, a_sectors):
        gubernskii = {
            'Балкон, Левая сторона': 'Балкон',
            'Балкон, Правая сторона': 'Балкон',
            'Партер, Левая сторона': 'Партер',
            'Партер, Правая сторона': 'Партер'
        }       
        vtb_arena = {
            'Танцевальный партер': 'Танцпол',
            'ТАНЦПОЛ': 'Танцпол',
            'Фан зона': 'Фан-зона',
            'ФАНЗОНА': 'Фан-зона',
            'SUPER FAN – МЕСТО ВНУТРИ СЦЕНЫ': 'Фан-зона',
            'Ложа B22 (11 персон)': 'Ложа B22',
            'Ложа A10 (9 персон)': 'Ложа A10',
            'Ложа A12 (10 персон)': 'Ложа A12',
            'Партер A106': 'Сектор A106'
        }
        vtb_arena_second = {# ВТБ Арена-стадион им. Льва Яшина (Фан, Танцпол)
            'Ложа A12': 'VIP A12',
            'Ложа C1 (на 13 персон)': 'VIP C1 (целиком)',
            'Фан-зона': 'Фан зона',
            'Танцевальный партер': 'Танцпол'
        }
        luzhniki = {}

        ref_dict = {}
        if 'губернский театр' in self.venue.lower():
            ref_dict = gubernskii
        if "втб арена" in self.venue.lower():
            if self.scheme.name == 'ВТБ Арена-стадион им. Льва Яшина (Фан, Танцпол)':
                ref_dict = vtb_arena_second
            elif 'Лужники' in self.venue:
                ref_dict = luzhniki
            else:
                ref_dict = vtb_arena
        if 'Сочи Парк Арена' in self.venue:
            ref_dict = {
                'VIP СЕКТОР A (с ограниченной видимостью)': 'VIP-сектор A (ограниченная видимость)',
                'VIP СЕКТОР C (с ограниченной видимостью)': 'VIP-сектор C (ограниченная видимость)',
                'VIP СЕКТОР C': 'VIP-сектор C',
                'VIP СЕКТОР A': 'VIP-сектор A',
                'VIP СЕКТОР B': 'VIP-сектор B'
                }

        for sector in a_sectors:
            if "втб арена" in self.venue.lower():
                sector['name'] = sector['name'].replace(' (ограниченная видимость)', '')
                if len(sector['name']) == 4:
                    sector['name'] = 'Сектор ' + sector['name']
                elif len(sector['name']) <= 3:
                    sector['name'] = 'Ложа ' + sector['name']
                else:
                    sector['name'] = ref_dict.get(sector['name'], sector['name'])
                if self.scheme.name == 'ВТБ Арена-стадион им. Льва Яшина (Фан, Танцпол)':
                    sector['name'] = ref_dict.get(sector['name'], sector['name'])
            elif 'Лужники' in self.venue:
                if 'Сектор' in sector['name']:
                    sector['name'] = sector['name'][:8] + ' ' + sector['name'][8:]
                else:
                    sector['name'] = 'Сектор ' + sector['name'].replace(' (VIP)', '')
            else:
                sector['name'] = ref_dict.get(sector['name'], sector['name'])

    async def parse_seats(self):
        total_sector = []

        seance_id = await self.get_seance_id()
        json_data = await self.request_ro_json_data(seance_id)
        if json_data is None:
            return []
        json_data = json_data.get('entrances')
        if len(json_data) > 0:
            json_data = json_data[0]
        else:
            return []

        all_sector_with_data = {}
        all_sectors = json_data.get('sectors')
        for sector in all_sectors:
            sector_name = sector.get('name')

            all_seats_in_sector = {}
            fan_zone_and_dance_floor = sector.get('sectorSeats')
            if len(fan_zone_and_dance_floor) != 0:
                continue
                """ Фанзона, Танцевальный партер """
                for zone in fan_zone_and_dance_floor:
                    price = zone['price']
                    amount = zone['freeSeatsCount']
                    self.register_dancefloor(sector_name, price, amount)

            all_rows = sector.get('rows')
            for row in all_rows:
                row_number = row.get('name')
                all_seats = row.get('seats')
                for seat in all_seats:
                    price = seat.get('price')
                    seat_number = seat.get('name')

                    all_seats_in_sector[(row_number, seat_number)] = int(price)
            all_sector_with_data[sector_name] = all_seats_in_sector

        for sector, total_seats_row_prices in all_sector_with_data.items():
            total_sector.append(
                {
                    "name": sector,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    async def request_ro_json_data(self, seance_id):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://redkassa.ru',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        url = 'https://redkassa.ru/Quota/GetQuota'
        data = {
            "seanceId": seance_id,
            "rowId": None
        }
        r = await self.session.post(url, headers=headers, json=data)
        if r.status_code != 200:
            return None
        return r.json()

    async def get_seance_id(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
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
        r = await self.session.get(self.url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')
        script_with_seance_id = soup.select('body main script')[1].text
        seance_id = double_split(script_with_seance_id, '{"seanceId":"', '","eventId"')
        return seance_id

    async def body(self):
        a_sectors = await self.parse_seats()

        self.reformat(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
        #self.check_sectors()
