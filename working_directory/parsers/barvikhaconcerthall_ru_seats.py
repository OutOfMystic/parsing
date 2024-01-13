from bs4 import BeautifulSoup
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession


class BarvikhaConcertHall(AsyncSeatsParser):
    event = 'barvikhaconcerthall.ru'
    url_filter = lambda url: 'barvikhaconcerthall.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.svg_width_scene = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, a_sectors):
        scheme_width_59_table = {
            'Ложа Бенуара № 2 ПС': 'Ложа бенуара 2 ПС',
            'Ложа Бенуара № 1 ПС': 'Ложа бенуара 1 ПС',
            'Ложа Бенуара № 2 ЛС': 'Ложа бенуара 2 ЛС',
            'Ложа Бенуара № 1 ЛС': 'Ложа бенуара 1 ЛС',
            'Ложа Бенуара 2 ЛС (столы)': 'Ложа бенуара 2 ЛС',
            'Ложа Бенуара 1 ЛС (столы)': 'Ложа бенуара 1 ЛС',
            'Ложа Бенуара 2 ПС (столы)': 'Ложа бенуара 2 ПС',
            'Ложа Бенуара 1 ПС (столы)': 'Ложа бенуара 1 ПС',
            'Vip Ложа 12': 'VIP-ложа №12',
            'Vip Ложа 11': 'VIP-ложа №11',
            'Vip Ложа 10': 'VIP-ложа №10',
            'Vip Ложа 9': 'VIP-ложа №9',
            'Vip Ложа 8': 'VIP-ложа №8',
            'Vip Ложа 7': 'VIP-ложа №7',
            'Vip Ложа 6': 'VIP-ложа №6',
            'Vip Ложа 5': 'VIP-ложа №5',
            'Vip Ложа 4': 'VIP-ложа №4',
            'Vip Ложа 3': 'VIP-ложа №3',
            'Vip Ложа 2': 'VIP-ложа №2',
            'Vip Ложа 1': 'VIP-ложа №1',
            'Super VIP ложа': 'Super VIP-ложа',
            'VIP ЛОЖА': 'Супер VIP ложа',
            'Правительственная ложа 2 (столы)': 'Правительственная ложа 2',
            'Правительственная ложа 1 (столы)': 'Правительственная ложа 1',
            'Директорская ложа 2 (столы)': 'Директорская ложа 2',
            'Директорская ложа 1 (столы)': 'Директорская ложа 1',
            'ПАРТЕР (столы)': 'Столы',
        }
        scheme_without_table = {
            'Ложа Бенуара № 2 ПС': 'Бенуар, правая сторона',
            'Ложа Бенуара № 1 ПС': 'Бенуар, правая сторона',
            'Ложа Бенуара № 2 ЛС': 'Бенуар, левая сторона',
            'Ложа Бенуара № 1 ЛС': 'Бенуар, левая сторона',
            'Vip Ложа 12': 'Правая сторона',
            'Vip Ложа 11': 'Правая сторона',
            'Vip Ложа 10': 'Правая сторона',
            'Vip Ложа 9': 'Правая сторона',
            'Vip Ложа 8': 'Ложа 8',
            'Vip Ложа 7': 'Ложа 7',
            'Vip Ложа 6': 'Ложа 6',
            'Vip Ложа 5': 'Ложа 5',
            'Vip Ложа 4': 'Левая сторона',
            'Vip Ложа 3': 'Левая сторона',
            'Vip Ложа 2': 'Левая сторона',
            'Vip Ложа 1': 'Левая сторона',
            'Super VIP ложа': 'VIP ложа',
            'VIP ЛОЖА': 'VIP ложа',
            'Правительственная ложа № 2': 'Правительственная ложа',
            'Правительственная ложа № 1': 'Правительственная ложа',
            'Директорская ложа 2': 'Директорская ложа',
            'Директорская ложа 1': 'Директорская ложа',
            'ПАРТЕР': 'Партер',
        }

        scheme_width_112_table = {
            'Ложа Бенуара № 2 ПС': 'Ложа бенуара 2, правая сторона',
            'Ложа Бенуара № 1 ПС': 'Ложа бенуара 1, правая сторона',
            'Ложа Бенуара № 2 ЛС': 'Ложа бенуара 2, левая сторона',
            'Ложа Бенуара № 1 ЛС': 'Ложа бенуара 1, левая сторона',
            'Ложа Бенуара 2 ЛС (столы)': 'Ложа бенуара 2, левая сторон',
            'Ложа Бенуара 1 ЛС (столы)': 'Ложа бенуара 1, левая сторона',
            'Ложа Бенуара 2 ПС (столы)': 'Ложа бенуара 2, правая сторона',
            'Ложа Бенуара 1 ПС (столы)': 'Ложа бенуара 1, правая сторона',
            'Vip Ложа №12': 'VIP ложа 12',
            'Vip Ложа №11': 'VIP ложа 11',
            'Vip Ложа №10': 'VIP ложа 10',
            'Vip Ложа №9': 'VIP ложа 9',
            'Vip Ложа №8': 'VIP ложа 8',
            'Vip Ложа №7': 'VIP ложа 7',
            'Vip Ложа №6': 'VIP ложа 6',
            'Vip Ложа №5': 'VIP ложа 5',
            'Vip Ложа №4': 'VIP ложа 4',
            'Vip Ложа №3': 'VIP ложа 3',
            'Vip Ложа №2': 'VIP ложа 2',
            'Vip Ложа №1': 'VIP ложа 1',
            'VIP ЛОЖА': 'Супер VIP ложа',
            'Правительственная ложа 2 (столы)': 'Правительственная ложа 2',
            'Правительственная ложа 1 (столы)': 'Правительственная ложа 1',
            'Директорская ложа 2 (столы)': 'Директорская ложа 2',
            'Директорская ложа 1 (столы)': 'Директорская ложа 1',
            'ПАРТЕР (столы)': 'Партер столы',
        }

        scheme_width_91_table_8table_in_row = {
            'Ложа Бенуара № 2 ПС': 'Ложа бенуара 2, правая сторона',
            'Ложа Бенуара № 1 ПС': 'Ложа бенуара 1, правая сторона',
            'Ложа Бенуара № 2 ЛС': 'Ложа бенуара 2, левая сторона',
            'Ложа Бенуара № 1 ЛС': 'Ложа бенуара 1, левая сторона',
            'Ложа Бенуара 2 ЛС (столы)': 'Ложа бенуара 2, левая сторон',
            'Ложа Бенуара 1 ЛС (столы)': 'Ложа бенуара 1, левая сторона',
            'Ложа Бенуара 2 ПС (столы)': 'Ложа бенуара 2, правая сторона',
            'Ложа Бенуара 1 ПС (столы)': 'Ложа бенуара 1, правая сторона',
            'Vip Ложа 12': 'VIP-ложа №12',
            'Vip Ложа 11': 'VIP-ложа №11',
            'Vip Ложа 10': 'VIP-ложа №10',
            'Vip Ложа 9': 'VIP-ложа №9',
            'Vip Ложа 8': 'VIP-ложа №8',
            'Vip Ложа 7': 'VIP-ложа №7',
            'Vip Ложа 6': 'VIP-ложа №6',
            'Vip Ложа 5': 'VIP-ложа №5',
            'Vip Ложа 4': 'VIP-ложа №4',
            'Vip Ложа 3': 'VIP-ложа №3',
            'Vip Ложа 2': 'VIP-ложа №2',
            'Vip Ложа 1': 'VIP-ложа №1',
            'VIP ЛОЖА': 'Super VIP-ложа',
            'Правительственная ложа 2 (столы)': 'Правительственная ложа 2',
            'Правительственная ложа 1 (столы)': 'Правительственная ложа 1',
            'Директорская ложа 2 (столы)': 'Директорская ложа 2',
            'Директорская ложа 1 (столы)': 'Директорская ложа 1',
            'ПАРТЕР (столы)': 'Столы',
        }

        ref_dict = scheme_width_59_table
        if '63972601ca8b3156393981.svg' in self.svg_width_scene:
            ref_dict = scheme_width_59_table
        elif ('60a3c47765f7f268580790.svg' in self.svg_width_scene):
            ref_dict = scheme_without_table
        elif '61519c4b27146906666725.svg' in self.svg_width_scene:
            ref_dict = scheme_width_59_table
        elif '5fb3a3e778fc7478762967' in self.svg_width_scene:
            ref_dict = scheme_width_91_table_8table_in_row
        elif ('6543e79ddd645518651977.svg' in self.svg_width_scene or
              '64ec7d6b276c4254026456.svg' in self.svg_width_scene or 
              '654e1c8a9c5d8241852356.svg' in self.svg_width_scene or
              '655c8c67337c0493794593.svg' in self.svg_width_scene ):
            ref_dict = scheme_width_59_table
        elif ('655f466a54b6c198617702.svg' in self.svg_width_scene or
              '655f466a54b6c198617702.svg' in self.svg_width_scene  or 
              '6570705d1564f798193247.svg' in self.svg_width_scene ):
            ref_dict = scheme_width_112_table
        elif ('653a27c848451187877444' in self.svg_width_scene or
              '658ea246cf2e8401398561' in self.svg_width_scene):
            ref_dict = scheme_width_112_table
            ref_dict['VIP ЛОЖА'] = 'Супер VIP ложа'

        new_a_sectors = {}
        for sector, tickets in a_sectors.items():
            new_name = ref_dict.get(sector, sector)
            new_a_sectors.setdefault(new_name, {}).update(tickets)
        return new_a_sectors

    def parse_seats(self, json_data):
        json_data = json_data.get('DATA')
        #self.info(json_data)
        all_sector_dict = {}
        sector_data = json_data.get('segments')
        #self.info(sector_data, 'sector_data')
        for sector in sector_data:
            sector_id = sector.get('segmentId')
            sector_count = sector.get('segment')
            all_sector_dict[sector_id] = sector_count

        date_seats = {}
        seats_data = json_data.get('seats')
        for seat in seats_data:
            seat_place = seat.get('seat')
            seat_row = seat.get('row')
            seat_price = seat.get('price')
            seat_sector_id = seat.get('segmentId')

            seat_sector = all_sector_dict.get(seat_sector_id)

            if '60a3c47765f7f268580790.svg' in  self.svg_width_scene:
                if 'Правительственная ложа' in seat_sector or 'Директорская ложа' in seat_sector:
                    seat_row = f'Ложа {seat_sector[-1]}'
                elif 'Ложа Бенуара' in seat_sector:
                    seat_row = f'Ложа {seat_sector.split("№ ")[1][0]}'
                elif 'Vip Ложа' in seat_sector:
                    if '1' in seat_sector or '2' in seat_sector or '3' in seat_sector or '4' in seat_sector:
                        seat_row = f'Ложа {seat_sector[-1]}'
                    if '9' in seat_sector:
                        seat_row = 'Ложа 9'
                    if '10' in seat_sector:
                        seat_row = 'Ложа 10'
                    if '11' in seat_sector:
                        seat_row = 'Ложа 11'
                    if '12' in seat_sector:
                        seat_row = 'Ложа 12'

            if '612ce30db591f751824837.svg' in self.svg_width_scene:
                seat_sector = f'Стол №{seat_row}'
                seat_row = 1

            date_seats.setdefault(seat_sector, {}).update({
                (str(seat_row), str(seat_place), ): seat_price
                })
            
        return date_seats

    async def request_parser(self, url):
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'barvikhaconcerthall.ru',
            'referer': self.url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = await self.session.get(url, headers=headers)
        return r.json()

    async def request_parser_to_index(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'barvikhaconcerthall.ru',
            'referer': 'https://barvikhaconcerthall.ru/events/calendar/',
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
        r = await self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    async def get_seats(self):
        soup_to_index = await self.request_parser_to_index(self.url)
        data_to_parse = soup_to_index.find('div', class_='js-event-tickets')
        index = data_to_parse.get('data-code')
        self.svg_width_scene = data_to_parse.get('data-scheme')

        if self.svg_width_scene is None:
            raise ValueError(f'Нету данных о схеме: {self.url = }')

        url = f'https://barvikhaconcerthall.ru/widget/assets/php/tickets.v3.php?action=event-detail&index={index}'
        json_data = await self.request_parser(url)

        a_events = self.parse_seats(json_data)

        return a_events

    async def body(self):
        all_sectors = await self.get_seats()

        all_sectors = self.reformat(all_sectors)

        for sector, tickets in all_sectors.items():
            #self.info(sector, len(tickets))
            self.register_sector(sector, tickets)
