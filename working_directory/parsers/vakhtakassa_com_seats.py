from bs4 import BeautifulSoup
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class Vakhtakassa(SeatsParser):
    event = 'vakhtakassa.com'
    url_filter = lambda url: 'vakhtakassa.com' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.count_request = 0

    def before_body(self):
        self.session = ProxySession(self)

    def get_href(self, url, received_date, received_time):
        try:
            r = self.request_for_get_href(url)
            soup_for_href = BeautifulSoup(r.text, "lxml")

            json_text = soup_for_href.select('script#__NEXT_DATA__')[0].text
            json_text = json_text.replace('false', 'False').replace('true', 'True').replace('none', 'None').replace(
                'null', 'None')
            json_loads = eval(json_text)

            first_param_for_href = json_loads.get('props').get('pageProps').get('event').get('widget')
            second_param_for_href = None

            all_events = json_loads.get('props').get('pageProps').get('event').get('event').get('children')
            for event in all_events:
                date_event = event.get('date_start')
                time_event = event.get('time_start')
                if received_date == date_event and received_time == time_event:
                    second_param_for_href = event.get('id')
                    break

            if second_param_for_href is None:
                self.warning(f'Не найдено id {url}')
                return None

            href = f'https://widget-api.vakhtakassa.com/api/widget/{first_param_for_href}/ticket?lang=ru&currency=RUB&event={second_param_for_href}&is_landing=true'
            return href
        except Exception:
            if self.count_request < 5:
                self.count_request += 1
                return self.get_href(url, received_date, received_time)
            else:
                return None

    def parse_seats(self):
        month_num_by_str = {
            "Янв": '01', "Фев": '02', "Мар": '03', "Апр": '04',
            "Май": '05', "Июн": '06', "Июл": '07', "Авг": '08',
            "Сен": '09', "Окт": '10', "Ноя": '11', "Дек": '12',
        }
        day, month, time = str(self.date).split()

        self.count_request = 0
        int_month = month_num_by_str.get(month)
        href = self.get_href(self.url, f'2023-{int_month}-{day}', f'{time}:00')
        if href is None:
            self.error(f'Парсер vakhtakassa: c url {self.url} не вернул ссылку')
            return None

        json_data = self.request_parser(url=href)
        total_sector = []

        all_sector = json_data.get('sectors')
        for sector in all_sector:
            sector_name = sector.get('i'). replace(',', '')
            rows = sector.get('r')
            if not rows:
                continue

            total_seats_row_prices = {}
            for row in rows:
                row_name = row.get('i')
                seats = row.get('s')
                for seat in seats:
                    seat_name = seat.get('i')
                    price = seat.get('p')
                    total_seats_row_prices[(row_name, seat_name)] = price

            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    def request_for_get_href(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'vakhtakassa.com',
            # 'referer': 'https://vakhtakassa.com/events?',
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
        return r

    def request_parser(self, url):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'origin': 'https://widget-frame.vakhtakassa.com',
            'referer': 'https://widget-frame.vakhtakassa.com/',
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

    def body(self):
        all_sectors = self.parse_seats()

        for sector in all_sectors:
            self.register_sector(sector['name'], sector['tickets'])
