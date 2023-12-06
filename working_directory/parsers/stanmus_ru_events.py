from bs4 import BeautifulSoup
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class Parser(EventParser):

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://stanmus.ru/shows/'

    def before_body(self):
        self.session = ProxySession(self)

    def get_events(self, products_about, year):
        a_events = []

        for product in products_about:
            title = product.find('a', class_='h3-blue').getText().strip()

            if 'экскурсия' in title.lower():
                continue

            btn_price = product.find('a', class_='btn--price')

            if not btn_price:
                continue

            btn_text = btn_price.text.strip().lower()
            if 'подписаться' in btn_text or 'скоро в продаже' in btn_text:
                continue

            href = btn_price.get('href', False)

            if not href:
                continue

            product_date = product.find('h4').getText().strip().split()
            day, month, time = [product_date[i] for i in range(len(product_date)) if i != 2]
            month = month[:3].capitalize()
            date = f'{day} {month} {year} {time}'

            scene = product.find('div', class_='product__data').getText().strip()

            a_events.append([title, href, date, scene])

        return a_events

    def parse_show_list(self, month_params='', return_soup=False):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip,deflate,br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
            'host': 'stanmus.ru',
            'sec-ch-ua': '"Chromium";v="106","Google Chrome";v="106","Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url + month_params, headers=headers)

        soup = BeautifulSoup(r.text, 'lxml')
        products_about = soup.find_all('div', class_='product__about')

        if return_soup:
            return soup, products_about
        else:
            return products_about

    def get_months_params(self, soup):
        months_params = []
        for category_month in soup.find_all('div', class_='category-month__item'):
            month_params = category_month['data-url'].split('/')[-1]
            months_params.append(month_params)

        return months_params

    def body(self):
        init_month_soup, init_products = self.parse_show_list(return_soup=True)
        months_params = self.get_months_params(init_month_soup)
        init_year = months_params[0].split('_')[-1].strip()
        months_params = months_params[1:]

        a_events = self.get_events(init_products, init_year)
        for month_params in months_params:
            products_about = self.parse_show_list(month_params)
            year = month_params.split('_')[-1].strip()
            month_events = self.get_events(products_about, year)
            a_events += month_events

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], scene=event[3])

