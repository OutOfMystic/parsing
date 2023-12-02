from bs4 import BeautifulSoup
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class Parser(EventParser):
    proxy_check_url = 'https://www.ticketland.ru/'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 1800
        self.driver_source = None
        self.url = 'https://www.ticketland.ru/teatry/'

    def before_body(self):
        self.session = ProxySession(self)

        self.our_places_data = {
            'https://sochi.ticketland.ru/teatry/': [
                'zimniy-teatr-sochi',
            ],
            'https://spb.ticketland.ru/teatry/': [
                'aleksandrinskiy-teatr',
                'bdt-imtovstonogova',
            ],
            'https://www.ticketland.ru/teatry/': [
                'teatr-lenkom',
                'mkht-im-chekhova',
                'mkhat-im-m-gorkogo',
                'malyy-teatr',
                'teatr-imeni-evgeniya-vakhtangova',
                'simonovskaya-scena-teatra-imeni-evgeniya-vakhtangova',
                'teatr-satiry',
                'teatr-operetty',
                'masterskaya-p-fomenko',
                'gosudarstvennyy-teatr-naciy',
                'teatr-ugolok-dedushki-durova',
                'moskovskiy-teatr-sovremennik',
            ],
            'https://www.ticketland.ru/cirki/': [
                'bolshoy-moskovskiy-cirk',
            ],
            'https://www.ticketland.ru/drugoe/': [
                'mts-live-kholl-moskva',
            ],
            'https://www.ticketland.ru/koncertnye-zaly/': [
                'gosudarstvennyy-kremlevskiy-dvorec',
            ],
        }

    def get_events(self, link, places_url):
        l = 0
        achtung = None
        while achtung == None:
            add_link = link + f'LoadBuildingPopularJS/?page={l}&dateStart=0&dateEnd=0&dateRangeCode=default'
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                          'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru,en;q=0.9',
                'cache-control': 'max-age=0',
                'connection': 'keep-alive',
                'host': 'www.ticketland.ru',
                'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.user_agent
            }
            if 'spb' in link:
                headers['host'] = 'spb.ticketland.ru'
            elif 'sochi' in places_url:
                headers['host'] = 'sochi.ticketland.ru'

            r = self.session.get(add_link, headers=headers)
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.find_all('div', class_='col')
            achtung = soup.find('p', class_='mb-2')
            for card in cards:
                href = card.find('a', class_='card__image-link').get('href')
                link_ = link.split('w')[0] + places_url.split('/')[2] + href
                for event in self.get_cards(link_):
                    yield event
            l += 1

    def get_cards(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'www.ticketland.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        old_url = None
        if 'spb' in url:
            headers['host'] = 'spb.ticketland.ru'
            old_url = 'spb'
            url = url.split('/')[-2]
            url = 'https://spb.ticketland.ru/teatry/aleksandrinskiy-teatr/' + url
        elif 'sochi' in url:
            headers['host'] = 'sochi.ticketland.ru'
            old_url = 'sochi'
            url = url.split('/')[-2]
            url = 'https://sochi.ticketland.ru/teatry/zimniy-teatr-sochi/' + url

        r = self.session.get(url, headers=headers)
        # time.sleep(1)

        soup = BeautifulSoup(r.text, 'lxml')
        cards1 = soup.find_all('article', class_='show-card')
        cards2 = soup.find_all('article', class_='show-card--active')
        cards = cards1 + cards2
        list_btn = []
        for card in cards:
            dm, year = card.find_all(class_='show-card__dm')
            event_name = card.find('meta')['content']
            day, month = dm.get_text().strip().split(' ')
            year = year.get_text().strip()
            month = month[:3].capitalize()
            time_ = card.find(class_='show-card__t').get_text().strip()
            formatted_date = f'{day} {month} {year} {time_}'
            btn = card.find(class_='btn btn--primary')
            if btn is None or btn in list_btn:
                continue
            list_btn.append(btn)
            url = btn['href']
            if old_url == 'spb':
                url = 'https://spb.ticketland.ru' + url
            elif 'sochi' == old_url:
                url = 'https://sochi.ticketland.ru' + url
            else:
                url = 'https://www.ticketland.ru' + url
            yield event_name, url, formatted_date

    def get_links_teatrs(self, pagecount, places_url, our_places):
        links_venues = []
        for p in range(1, int(pagecount) + 1):
            api = places_url + f"?page={p}&tab=all"
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                          'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru,en;q=0.9',
                'cache-control': 'max-age=0',
                'connection': 'keep-alive',
                'host': 'www.ticketland.ru',
                'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.user_agent
            }
            if 'spb' in places_url:
                headers['host'] = 'spb.ticketland.ru'
            elif 'sochi' in places_url:
                headers['host'] = 'sochi.ticketland.ru'

            r = self.session.get(api, headers=headers)
            soup = BeautifulSoup(r.text, 'lxml')
            items = soup.find_all('div', class_='card-search')
            for item in items:
                link_src = item.find('a', class_='card-search__name')
                venue = link_src.text.strip()
                url_parts = places_url.split('/')
                link = url_parts[0] + '//' + url_parts[2] + link_src.get('href')
                links_venues.append((link, venue))

        our_links_venues = {}
        for our_place in our_places:
            for link, venue in links_venues:
                if venue == 'Большой Московский цирк':
                    venue = 'Цирк на Вернадского'
                if our_place in link:
                    our_links_venues[link] = venue
        return our_links_venues

    def request_to_ticketland(self, url, headers=None):
        r = self.session.get(url, headers=headers)
        r_text = r.text
        if '<div id="id_spinner" class="container"><div class="load">Loading...</div>' in r_text:
            raise Exception('Запрос с загрузкой')
        return r_text

    def body(self):
        for places_url, our_places in self.our_places_data.items():
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru,en;q=0.9',
                'cache-control': 'max-age=0',
                'connection': 'keep-alive',
                'host': 'www.ticketland.ru',
                'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': self.user_agent
            }
            if 'spb' in places_url:
                headers['host'] = 'spb.ticketland.ru'
            elif 'sochi' in places_url:
                headers['host'] = 'sochi.ticketland.ru'

            r = self.session.get(places_url, headers=headers)
            soup = BeautifulSoup(r.text, 'lxml')
            papers = soup.find_all('li', class_='search-pagination__item')
            if papers:
                last_paper = papers[-1]
                pagecount = last_paper.get('data-page-count')
            else:
                pagecount = 1
            for link, venue in self.get_links_teatrs(pagecount, places_url, our_places).items():
                for event in self.get_events(link, places_url):
                    self.register_event(event[0], event[1], date=event[2], venue=venue)
                # self.proxy = self.controller.proxy_hub.get(url=self.proxy_check_url)
