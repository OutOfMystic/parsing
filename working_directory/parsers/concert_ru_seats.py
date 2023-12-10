from bs4 import BeautifulSoup
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.parse_utils import double_split


class Concert(SeatsParser):
    event = 'www.concert.ru'
    url_filter = lambda url: 'www.concert.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, a_sectors):
        kreml_reformat_dict = {
            'Ложа балкона левая': 'Ложа балкона, левая сторона',
            'Ложа балкона правая': 'Ложа балкона, правая сторона',
            'Балкон, прав.ст. откидное': 'Балкон, правая сторона (откидные)',
            'Балкон, лев.ст. откидное': 'Балкон, левая сторона (откидные)',
            'Балкон середина': 'Балкон, середина',
            'Балкон правая сторона': 'Балкон, правая сторона',
            'Балкон левая сторона': 'Балкон, левая сторона',
            'Амфитеатр правая сторона': 'Амфитеатр, правая сторона',
            'Амфитеатр левая сторона': 'Амфитеатр, левая сторона',
            'Амфитеатр середина': 'Амфитеатр, середина',
            'Партер середина': 'Партер, середина',
            'Партер левая сторона': 'Партер, левая сторона',
            'Партер правая сторона': 'Партер, правая сторона',
            'Сектор VIP - A': 'VIP A',
            'Сектор VIP - B': 'VIP B',
            'Сектор VIP - C': 'VIP C',
        }
        crocus_sity_hall_reformat_dict = {
            '': '',
        }
        ice_palace_reformat_dict = {
            '': '',
        }
        tchaikovsky_conservatory_reformat_dict = {
            '1-й Амфитеатр правая сторона': 'Первый амфитеатр, правая сторона',
            '1-й Амфитеатр середина': 'Первый амфитеатр, середина',
            '1-й Амфитеатр левая сторона': 'Первый амфитеатр, левая сторона',
            '2-й Амфитеатр левая сторона': 'Второй амфитеатр, левая сторона',
            '2-й Амфитеатр середина': 'Второй амфитеатр, середина',
            '2-й Амфитеатр правая сторона': 'Второй амфитеатр, правая сторона',
            'Ложа 9': 'Второй амфитеатр, ложа 9',
            'Ложа 10': 'Второй амфитеатр, ложа 10',
        }
        house_of_music_reformat_dict = {
            'Ложа №1': 'Ложа партера №1',
            'Ложа №2': 'Ложа партера №2',
            'Ложа №3': 'Ложа партера №3',
            'Ложа №4': 'Ложа партера №4',
            'Амфитеатр. Левая сторона': 'Амфитеатр, левая сторона',
            'Амфитеатр. Середина': 'Амфитеатр, середина 1',
            'Амфитеатр. Правая сторона': 'Амфитеатр, правая сторона',
            'Бельэтаж (правая сторона)': 'Бельэтаж, правая сторона',
            'Бельэтаж (левая сторона)': 'Бельэтаж, левая сторона',
            'Балкон. Левая сторона': 'Балкон, середина',
            'Балкон. Середина': 'Балкон, левая сторона',
            'Балкон. Правая сторона': 'Балкон, правая сторона',
        }

        ref_dict = {}
        if 'кремлевский дворец' in self.venue.lower():
            ref_dict = kreml_reformat_dict
        elif 'крокус сити холл' in self.venue.lower():
            ref_dict = crocus_sity_hall_reformat_dict
        elif 'ледовый дворец' in self.venue.lower():
            ref_dict = ice_palace_reformat_dict
        elif 'консерватория им. п.и.чайковского - большой зал' in self.venue.lower():
            ref_dict = tchaikovsky_conservatory_reformat_dict
        elif 'дом музыки' in self.venue.lower():
            ref_dict = house_of_music_reformat_dict

        for sector in a_sectors:
            if 'мегаспорт' in self.venue.lower():
                sector['name'] = sector['name'].replace(' / -', '')
                if sector['name'] == 'VIP C0':
                    sector['name'] = 'Сектор C0'
            else:
                sector['name'] = ref_dict.get(sector['name'], sector['name'])

    def parse_seats(self):
        total_sector = []
        soup = self.request_parser(url=self.url)

        all_sector = {}
        all_row = soup.select('tr[id^="ticketGroup"]')
        for row in all_row:
            sector_name = row.find('div', class_='ticketsTable__type').text.strip().replace(' / -', '')
            row_number = row.find('div', class_='ticketsTable__row').text.strip().split()[0]
            price = row.find('div', class_='ticketsTable__price').text.strip()
            price = int(price.replace('руб.', '').replace(' ', ''))

            data_to_seats = row.find('a', class_='chooseTicketButton').get('onclick')
            data_to_seats = double_split(data_to_seats, '(', ', this)')
            data_to_seats = data_to_seats.replace("'", '').split(', ')
            seats_soup = self.request_to_seats(data_to_seats)

            all_seats = seats_soup.find_all('tr', class_='ticketsTable__item')
            for seat in all_seats:
                seat_number = seat.find('div', class_='ticketsTable__itemSeats').text.strip()

                if all_sector.get(sector_name):
                    dict_sector = all_sector[sector_name]
                    dict_sector[(row_number, seat_number,)] = price
                else:
                    all_sector[sector_name] = {(row_number, seat_number,): price}

        for sector_name, total_seats_row_prices in all_sector.items():
            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def request_to_seats(self, data):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'content-length': '192',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': 'www.concert.ru',
            'origin': 'https://www.concert.ru',
            'referer': 'https://www.concert.ru/teatry/spektakl-prodavets-igrushek/09-04-2023-18-00/',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            'subTicketsGroupNumber': data[0],
            'subTicketsActionId': data[1],
            'subTicketsActionDateId': data[2],
            'subTicketsActionSeatsSubTypeId': data[3],
            'subTicketsPrice': data[4],
            'subTicketsRowNumber': data[5],
            'X-Requested-With': 'XMLHttpRequest'
        }
        url = 'https://www.concert.ru/SubTickets'
        r = self.session.post(url, headers=headers, data=data)
        return BeautifulSoup(r.text, 'lxml')

    def request_parser(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'www.concert.ru',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def body(self):
        all_sectors = self.parse_seats()

        self.reformat(all_sectors)

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
