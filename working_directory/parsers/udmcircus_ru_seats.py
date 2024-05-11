from bs4 import BeautifulSoup
import re

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.models.parser import SeatsParser

class CircusIzevskSeats(AsyncSeatsParser):
    event = 'https://quicktickets.ru/izhevsk-cirk'
    url_filter = lambda url: 'quicktickets.ru/izhevsk-cirk' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 2200
        self.driver_source = None
        self.id = self.make_id()
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "api-id": "quick-tickets",
            "cache-control": "no-cache",
            "dnt": "1",
            "origin": "https://hall.quicktickets.ru",
            "priority": "u=1, i",
            "referer": "https://hall.quicktickets.ru/",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": self.user_agent
        }

    def make_id(self):
        # self.url ilike 'https://quicktickets.ru/izhevsk-cirk/s596'
        last_path = self.url.split('/')[-1]
        id_number = re.search(r'\d+', last_path)
        return id_number[0]

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def get_and_find_authorization_token(self):
        headers_html = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "dnt": "1",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent
        }
        #self.url ilike 'https://quicktickets.ru/izhevsk-cirk/s596'
        r = await self.session.get(self.url, headers=headers_html)
        soup = BeautifulSoup(r.text, 'lxml')
        content_container = soup.find('div', class_='session-content')
        script_tag = content_container.find('script').text
        token_pattern = re.compile(r"params: {token: '(([^']+))'")
        token_match = token_pattern.search(script_tag)
        token = token_match[1]
        return token

    async def load_all_places_in_the_building(self, authorization_token):
        self.headers['authorization'] = f"Basic {authorization_token}"
        url = f'https://api.quicktickets.ru/v1/hall/hall?scope=qt&panel=site&\
                    user_id=0&organisation_alias=izhevsk-cirk&elem_type=session&elem_id={self.id}'
        r = await self.session.get(url, headers=self.headers)
        r_json = r.json()
        all_places = r_json["response"].get('places')
        return all_places

    async def load_all_free_places_you_can_buy(self):
        url_free_palces = f'https://api.quicktickets.ru/v1/anyticket/anyticket?scope=qt&'\
                f'panel=site&user_id=0&organisation_alias=izhevsk-cirk&elem_type=session&elem_id={self.id}'
        r2 = await self.session.get(url_free_palces, headers=self.headers)
        all_free_places_json = r2.json().get('response').get('places')
        return all_free_places_json

    def make_tickets_structure(self, all_places_in_the_circus, all_free_places):
        a_events = {}
        for free_place in all_free_places:
            info_about_place = all_places_in_the_circus.get(free_place)
            if info_about_place:
                name_of_sector = info_about_place.get('block')
                price = info_about_place.get('price')
                number_of_seat = info_about_place.get('place')
                row_number = info_about_place.get('series')

                a_events.setdefault(name_of_sector, {}).update({(row_number, number_of_seat): price})
        return a_events

    async def body(self):
        authorization_token = await self.get_and_find_authorization_token()
        all_places_in_the_circus = await self.load_all_places_in_the_building(authorization_token)
        all_free_places = await self.load_all_free_places_you_can_buy()

        a_sectors = self.make_tickets_structure(all_places_in_the_circus, all_free_places)

        for sector, tickets in a_sectors.items():
            #self.info(sector, tickets)
            self.register_sector(sector, tickets)
        #self.check_sectors()