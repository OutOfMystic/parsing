from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.provision import multi_try
from parse_module.utils import utils


class ProfticketParser(AsyncSeatsParser):
    event = 'spa.profticket.ru'
    url_filter = lambda url: 'spa.profticket.ru' in url
    proxy_check = SpecialConditions(url='https://spa.profticket.ru/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat_tickets(self, sector, f_row=None, f_seat=None):
        tickets_f = {}
        for (row, seat), price in sector['tickets'].items():
            c_row = f_row if f_row else row
            c_seat = f_seat if f_seat else seat
            tickets_f[(c_row, c_seat)] = price

        sector['tickets'] = tickets_f

    def reformat(self, sectors, place_name):
        # TODO на нашей схеме 'Бенуар, ложа левая' начинается с 3-го места, на этом сайте возможно с 1-го
        # TODO (свг элементы есть, но билетов нет чтоб проверить.)
        # TODO Ввиду отсутствия билетов не были настроены:
        # TODO Бельэтаж, место 1А; Бельэтаж, место 2А;
        reformat_dict_mht_main = {
            'бАЛКОН ПРАВАЯ НЕУДОБНОЕ': 'Балкон, правая сторона',
            'Балкон правая ограниченный обзор': 'Балкон, правая сторона',
            'Бельэтаж середина ограниченный обзор.': 'Балкон, середина',
            'Балкон правая сторона': 'Балкон, правая сторона',
            'Балкон середина': 'Балкон, середина',
            'Балкон середина ограниченный обзор': 'Балкон, середина',
            'Балкон левая сторона': 'Балкон, левая сторона',
            'Балкон левая ограниченный обзор': 'Балкон, левая сторона',
            'БАЛКОН ЛЕВАЯ НЕУДОБНОЕ': 'Балкон, левая сторона',
            'Бельэтаж ложа правая': 'Бельэтаж, ложа правая',
            'Бельэтаж откидное А': 'Бельэтаж, правая сторона (откидное А)',
            'Бельэтаж правая сторона': 'Бельэтаж, правая сторона',
            'Бельэтаж середина': 'Бельэтаж, середина',
            'Бельэтаж левая сторона': 'Бельэтаж, левая сторона',
            'Бельэтаж левая ограниченный обзор': 'Балкон, левая сторона',
            'Бельэтаж левая откидное огран.обзор': 'Балкон, левая сторона',
            'Бельэтаж откидное Б': 'Бельэтаж, левая сторона (откидное Б)',
            'Бельэтаж ложа левая': 'Бельэтаж, ложа левая',
            'Ложа бенуар правая': 'Бенуар, ложа правая',
            'Бенуар правая сторона': 'Бенуар, ложа правая',
            'Бенуар левая сторона': 'Бенуар, ложа левая',  # TODO спросить
            'Ложа бенуар левая': 'Бенуар, ложа левая',
            'Амфитеатр': 'Амфитеатр',
            'Амфитеатр откидное Б': 'Амфитеатр, откидное Б',
            'Партер откидное А': 'Партер, откидные А',
            'Партер': 'Партер',
            'Партер откидное Б': 'Партер, откидные Б'
        }

        reformat_dict_nikulina = {
            'Левая сторона партер': 'Партер левая сторона',
            'Правая сторона партер': 'Партер правая сторона',
            'Левая сторона амфитеатр': 'Амфитеатр левая сторона',
            'Правая сторона амфитеатр': 'Амфитеатр правая сторона',
            'Ложа партера': 'Ложа партера',
            'Ложа амфитеатра': 'Ложа амфитеатра',
            'Ложа дирекции-3': 'Ложа дирекции 3',
            'Ложа дирекции-2': 'Ложа дирекции 2',
            'Ложа дирекции-1': 'Ложа дирекции 1'
        }

        for sector in sectors:
            sector['name'] = sector['name'].replace('  ', ' ').replace(' неудобное', '')
            sector_name_l = sector['name'].lower()

            if 'мхт' in place_name:
                if 'основная' in self.scene.lower():
                    sector['name'] = reformat_dict_mht_main.get(sector['name'], sector['name'])

                    if sector['name'] in ['Партер, откидные А', 'Партер, откидные Б', 'Амфитеатр, откидное Б']:
                        self.reformat_tickets(sector, f_seat='1')
                    elif sector['name'] in ['Бельэтаж, правая сторона (откидное А)', 'Бельэтаж, левая сторона (откидное Б)',
                                            'Бельэтаж, место 1А']:
                        self.reformat_tickets(sector, f_seat='0')
                    elif sector['name'] in ['Бельэтаж, место 2А']:
                        self.reformat_tickets(sector, f_seat='2')

                    if sector['name'] in ['Бенуар, ложа левая', 'Бенуар, ложа правая']:
                        self.reformat_tickets(sector, f_row='0')

                # TODO Бывает такое что у ивента на сайте на малой сцене на ряды смещены? (или их меньше / больше)
                # TODO https://spa.profticket.ru/customer/54/shows/251/#5266 - 9 рядов, на 9-ом 22 места, у нас на 11-ом 22
                # TODO https://spa.profticket.ru/customer/54/shows/147/#5262 - то же самое, только еще снизу какой-то
                # TODO сектор в один ряд аааа
                # TODO https://spa.profticket.ru/customer/54/shows/156/#5263 - 10 рядов, на 10-ом 22
                # TODO https://spa.profticket.ru/customer/54/shows/45/#5256 - 12 рядов, на 12-ом 22, а у нас всего 11 рядов
                elif 'малая' in self.scene.lower():
                    if 'ПРИЕМНЫЙ ПОКОЙ (СЦЕНА)' in sector['name']:
                        sector['name'] = 'Партер'
                    # TODO столик отсутствует у нас на схеме
                    # TODO на другом ивенте вместо столиков 'приемный покой (сцена)', тоже отсутствует у нас на схеме

                # TODO https://spa.profticket.ru/customer/54/shows/229/#5271 - в галерее всего 10 место у нас 14
                # TODO в партере места странно разбросаны и в 5-ом ряду 21-о место, у нас 20
                elif 'новая' in self.scene.lower():
                    reformat_dict = {
                        'ГАЛЕРЕЯ': 'Галерея',
                        'Партер': 'Партер',
                        'Партер частично ограниченный просмотр': 'Партер',
                    }
                    sector['name'] = reformat_dict.get(sector['name'], sector['name'])

            elif 'цирк никулина' in place_name:
                sector['name'] = reformat_dict_nikulina.get(sector['name'], sector['name'])

    def get_show_info(self):
        url = f'https://widget.profticket.ru/api/event/show/?company_id={self.company_id}&show_id={self.show_id}&language=ru-RU'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
            'host': 'widget.profticket.ru',
            'origin': 'https://spa.profticket.ru',
            'referer': 'https://spa.profticket.ru/',
            'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)

        try:
            global_show_id = r.json()['response']['show']['id']
        except KeyError:
            self.error(f'error spa.proftickets.ru: {url}, {r.text}')
            return None

        place_name = r.json()['response']['show']['location_name'].lower()

        return global_show_id, place_name

    def get_tickets(self, global_show_id):
        url = f'https://widget.profticket.ru/api/event/scheme/?' \
              f'company_id={self.company_id}&' \
              f'global_show_id={global_show_id}&' \
              f'event_id={self.event_id}&' \
              f'language=ru-RU'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
            'host': 'widget.profticket.ru',
            'origin': 'https://spa.profticket.ru',
            'referer': 'https://spa.profticket.ru/',
            'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)

        try:
            data = r.json()['response']['items']
        except KeyError:
            data = []
            self.warning(f'{url}, {r.text}')

        return data

    async def body(self):
        data_or_none = self.get_show_info()
        if data_or_none is None:
            return
        global_show_id, place_name = data_or_none
        seat_data = self.multi_try(self.get_tickets, args=(global_show_id,))

        a_sectors = []
        for ticket in seat_data:
            if 'avail' not in ticket:
                continue
            if not ticket['avail']:
                continue

            sector_name = ticket['name_sec']
            row = str(ticket['row'])
            seat = str(ticket['seat'])
            price = int(float(ticket['price']))

            for sector in a_sectors:
                if sector_name == sector['name']:
                    sector['tickets'][row, seat] = price
                    break
            else:
                a_sectors.append({
                    'name': ticket['name_sec'],
                    'tickets': {(row, seat): price}
                })

        self.reformat(a_sectors, place_name)
        if len(a_sectors) == 0:
            return False
        else:
            for sector in a_sectors:
                if sector['name'] == 'Ложа дирекции 3':
                    continue
                self.register_sector(sector['name'], sector['tickets'])
