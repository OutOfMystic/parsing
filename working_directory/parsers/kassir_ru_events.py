from datetime import datetime
from urllib.parse import urlparse

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class KassirParser(AsyncEventParser):
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.new_urls = {
             #'https://msk.kassir.ru/koncertnye-zaly/zelenyiy-teatr-vdnh': '*', #Зелёный театр
             #'https://msk.kassir.ru/teatry/mdm': '*', # Московский дворец молодёжи
             #'https://msk.kassir.ru/drugoe/krasnaya-ploschad': '*', #Красная площадь
             #'https://msk.kassir.ru/teatry/rossijskoj-armii': '*', # Театр Армии
             'https://sochi.kassir.ru/teatry/zimniy-teatr': '', # Зимний театр Сочи
             'https://msk.kassir.ru/teatry/teatr-sovremennik': '*', # Театр Современник
             'https://msk.kassir.ru/koncertnye-zaly/gosudarstvennyj-kremlevskij-dvorec': '*', #Kreml dvorec
             'https://msk.kassir.ru/teatry/teatr-satiryi': '*', # teatr satiry
             'https://kzn.kassir.ru/cirki/tsirk-2': '*',  # kazanskii cirk
             'https://msk.kassir.ru/teatry/operetty': '*', #mosoperetta 
             'https://msk.kassir.ru/sportivnye-kompleksy/vtb-arena-tsentralnyiy-stadion-dinamo': '*', # Dinamo MSK stadium
             'https://msk.kassir.ru/sportivnye-kompleksy/dvorets-sporta-megasport': '*', # megasport
             #'https://sochi.kassir.ru/koncertnye-zaly/kontsertnyiy-zal-festivalnyiy': '*', #fistivalnii sochi
             #'https://msk.kassir.ru/teatry/ermolovoj': '*', # ermolovoi theatre
             #'https://msk.kassir.ru/teatry/teatr-im-vlmayakovskogo': '*', #Majakousogo theatre moscow
             'https://omsk.kassir.ru/sportivnye-kompleksy/g-drive-arena': '*',# G-Drive Арена omsk
             'https://kzn.kassir.ru/koncertnye-zaly/dvorets-sportakazan': '*',#Дворец спорта Казань
             'https://msk.kassir.ru/sportivnye-kompleksy/cska-arena': 'cska', #cska arena
             'https://msk.kassir.ru/teatry/mossoveta': '*', #mossoveta
        }

    async def before_body(self):
        self.session = AsyncProxySession(self)


    @staticmethod
    def format_date(date):
        return datetime.fromisoformat(date)

    @staticmethod
    def reformat_date(date):
        date_to_write = date.strftime("%d ") + \
                        date.strftime("%b ").capitalize() + \
                            date.strftime("%Y %H:%M")
        return date_to_write
    
    async def new_get_events(self, url):
        self.new_headers = {
            "accept": "*/*",
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'Connection': 'keep-alive',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            "Referer": "https://msk.kassir.ru/",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            'user-agent': self.user_agent
        }
        url_to_pars = urlparse(url)
        slug = url_to_pars.path #/koncertnye-zaly/zelenyiy-teatr-vdnh
        self.domain = url_to_pars.netloc #msk.kassir.ru
        url_to_api = f'https://api.kassir.ru/api/page-kit?slug={slug}&domain={self.domain}'

        # Здесь пока не будем менять логику
        get_events = await self.session.get(url_to_api, headers=self.new_headers)

        count = 5
        while not get_events.ok and count > 0:
            self.error(f'{self.proxy.args}, {self.session.cookies} kassir events')
            self.proxy = self.controller.proxy_hub.get(self.proxy_check)
            self.session = AsyncProxySession(self)
            get_events = await self.session.get(url_to_api, headers=self.new_headers)
            count -= 1

        a_events = []
        # with open('TEST1.json', 'w', encoding='utf-8') as file:
        #     json.dump(get_events.json(), file, indent=4, ensure_ascii=False) 
        total_count = get_events.json()['kit']['searchResult']["pagination"]["totalCount"]
        self.new_venue_id = get_events.json()['kit']["venue"]['id']
        
        self.venue_name = get_events.json()['kit']["venue"]['name']
        if self.venue_name in self.venue_to_replace:
            self.venue_name = self.venue_to_replace.get(self.venue_name)

        events = [i for i in get_events.json()['kit']['searchResult']['items']]
        a_events.extend(events)

        page = 2
        len_a_events = len(a_events)
        while len(a_events) < total_count and len_a_events > 0:
            pagination_url = f'https://api.kassir.ru/api/search?currentPage={page}'\
                                f'&pageSize=30&venueId={self.new_venue_id}&domain={self.domain}'
            response = await self.session.get(pagination_url, headers=self.new_headers)
            events = [i for i in response.json()['items']]
            a_events.extend(events)
            page += 1
            len_a_events = len(events)

        return a_events
    

    async def new_get_all_dates_from_event(self, url):
        r = await self.session.get(url, headers=self.new_headers)
        # with open('TEST2.json', 'w', encoding='utf-8') as file:
        #     json.dump(r.json(), file, indent=4, ensure_ascii=False) 
        if r.json()['kit'].get("eventBuckets"):
            box = r.json()['kit']["eventBuckets"][0]['events']
        elif r.json()['kit'].get("events"):
            box = r.json()['kit']["events"]
        ids = [i.get('id') for i in box]
        dates = [self.format_date(i["beginsAt"]) for i in box]
        dates = [self.reformat_date(i) for i in dates]

        return zip(ids,dates)

    async def new_reformat_events(self, a_events):
        events_to_write = []
        for event in a_events:
            title = event["object"]["title"].replace("'", "")
            self.id = event["object"]['id']
            url_all_events = f'https://{self.domain}/{event["object"]["urlSlug"]}'
            
            if event["object"].get('beginsAt') is not None: # only 1 event
                url_to_write = f'https://api.kassir.ru/api/event-page-kit/{self.id}?domain={self.domain}'
                date_start = self.format_date(event["object"].get("beginsAt"))
                date = self.reformat_date(date_start)
                events_to_write.append((title, url_to_write, date,
                                         self.venue_name, self.id, self.domain, url_all_events))

            elif event["object"].get("dateRange"): # more then 1 event
                slug = event["object"]["urlSlug"]
                url = f'https://api.kassir.ru/api/page-kit?slug={slug}&domain={self.domain}'
                try:
                    all_dates = await self.new_get_all_dates_from_event(url)
                    for id, date in all_dates:
                        url_to_write = f'https://{self.domain}/{slug}#{id}'
                        events_to_write.append((title, url_to_write, date,
                                                 self.venue_name, id, self.domain, url_all_events))
                except Exception as ex:
                    self.error(f'{ex} troubles bro.')
                    raise
        return events_to_write

    async def body(self):
        #('Ледовое шоу Евгения Плющенко «Русалочка»', 'https://schematr.kassir.ru/widget/?key=3a78a0c2-f33b-b849-851e-c1ba595f54bd&eventId=2012603', '28 Дек 2023 19:00', 'ВТБ Арена'),
        self.venue_to_replace = {
            'Красная площадь': 'Кремлёвский дворец',
            'Государственный Кремлевский Дворец (ГКД)': 'Кремлёвский дворец',
            'ЦИРК': 'Казанский цирк',
            'Московский театр оперетты': 'Театр Оперетты',
            'Концертный зал Фестивальный': '(КЗ) "Фестивальный"',
            'Театр им. Вл.Маяковского': 'Театр Маяковского',
            'Дворец спорта': 'Дворец спорта «ДС-Казань»'
        }

        a_events = []
        for url, venue_id in self.new_urls.items():
            self.info('Kassir seats',url)
            try:
                events = await self.new_get_events(url)
                all_dates = await self.new_reformat_events(events)
                a_events.extend(all_dates)
            except Exception as ex:
                self.warning(f'{ex}, {url} cannot load!')
                raise

        for event in a_events:
            if event[2] == '' or 'абонемент' in event[0].lower() or '—' in event[2]:
                continue
            elif 'ЦСКА Арена' in event[3]:
                if 'новогодняя история игрушек' not in event[0].lower():
                    continue
            try:
                self.register_event(event[0], event[1], date=event[2],
                                     venue=event[3], id=event[4], domain=event[5], url_all_events=event[6])
                self.debug(event)
            except Exception as ex:
                self.error(f'{ex}, {event} cannot save to DB!')
