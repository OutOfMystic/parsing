import re
from typing import NamedTuple
from datetime import datetime
import locale

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.sessions import AsyncProxySession


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str
    venue: str

class ALL_Circus_from_ticket_place_Events(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.urls_ONE = {
            #'https://circus-saratov.ru/strashnaya-sila.html': ('Балаган', 'saratov', 'Цирк им. братьев Никитиных Саратов',
            #        'https://ticket-place.ru/calendar-widget/25?showId=112&dateFrom=&dateTo=&page='),
            #'https://www.circus-vladivostok.ru/novogodnee-shou-byt-po-semu.html': ('Быть по сему',
                                                                        #'vladivostok','Цирк Владивосток',
                        #'https://ticket-place.ru/calendar-widget/34?showId=169&dateFrom=&dateTo=&page=1&maxDays=4'),
            'https://circus-vladivostok.ru/tigry-na-zemle-i-v-vozduhe.html': ('Тигры на земле и в воздухе',
                                                                        'vladivostok','Цирк Владивосток',
                        'https://ticket-place.ru/calendar-widget/34?showId=179&dateFrom=&dateTo=&page=1&maxDays=4'),
            'https://www.circus-sochi.ru/tropic-show.html': ('ТРОПИК ШОУ',
                                                            'sochi' , 'Сочинский Государственный Цирк',
                        'https://ticket-place.ru/calendar-widget/26?showId=200&dateFrom=&dateTo=&page=1&maxDays=4'),
            'https://www.circus-saratov.ru/':
                ('Итальянский цирк "Слоны и тигры"',
                'saratov','Саратовский цирк',
                'https://ticket-place.ru/calendar-widget/25?showId=212&dateFrom=&dateTo=&page=1&maxDays=4'),
            'https://circus-tyumen.ru/taina-pirata.html':
                ('ТАЙНА ПИРАТА',
               'tyumen', 'Цирк Тюмень',
               'https://ticket-place.ru/calendar-widget/11?showId=193&dateFrom=&dateTo=&page=1&maxDays=4'),
        }
        self.urls_TWO = {
            # url: tuple('slug', 'venue') -> для поиска  ids, в вёрстке есть calendar__item!
            # url: list[id, 'slug', 'venue'] -> для поиска по ид всех похожих ивентов на ticket-place.ru/widget/{id}/similar
            # url: str(function) -> имя функции для поиска в вёрстке
            

            #'https://www.circus-ivanovo.ru/': ('ivanovo', 'Ивановский цирк'),
            #'https://princess.circus.team/': [1302, 'saratov', 'Цирк им. братьев Никитиных Саратов'],
            #'https://princess.circus.team/': 'princess_saratov',
            #'https://www.circus-sochi.ru/': 'sochi'

            'https://www.circus-samara.ru/': 'samara',
            'https://www.circus-nnovgorod.ru/': 'nnovgorod',
            'https://www.circus-stavropol.ru/': 'stavropol',
        }
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "sec-ch-ua": "\"Not/A)Brand\";v=\"99\", \"Google Chrome\";v=\"115\", \"Chromium\";v=\"115\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "user-agent": self.user_agent
            }
        

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def reformat_date(date):
        date = datetime.fromisoformat(date)
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        date_to_write = f'{date.strftime("%d")} {date.strftime("%b").capitalize()}' \
                             f' {date.strftime("%Y")} {date.strftime("%H:%M")}'
        return date_to_write

    async def princess_saratov(self):
        r = await self.session.get(url='https://princess.circus.team/', headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        ids = soup.find_all('a', attrs={'data-tp-event': re.compile(r'\d+')})
        ids = [i.get('data-tp-event') for i in ids if i]
        return ids, 'saratov' , 'Цирк им. братьев Никитиных Саратов'
    
    async def sochi(self):
        r = await self.session.get(url='https://www.circus-sochi.ru/', headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        ids = soup.find_all('a', attrs={'data-tp-event': re.compile(r'\d+')})
        ids = [i.get('data-tp-event') for i in ids if i]
        return ids, 'sochi' , 'Сочинский Государственный Цирк'

    async def samara(self):
        r = await self.session.get(url='https://www.circus-samara.ru/', headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        ids = soup.find_all('a', attrs={'data-tp-event': re.compile(r'\d+')})
        ids = [i.get('data-tp-event') for i in ids if i]
        return ids, 'samara', 'Самара цирк'

    async def nnovgorod(self):
        r = await self.session.get(url='https://www.circus-nnovgorod.ru/', headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        ids = soup.find_all('a', attrs={'data-tp-event': re.compile(r'\d+')})
        ids = [i.get('data-tp-event') for i in ids if i]
        return ids, 'nnovgorod', 'Цирк Нижний Новгород'

    async def stavropol(self):
        r = self.session.get(url='https://www.circus-stavropol.ru/', headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        ids = soup.find_all('a', attrs={'data-tp-event': re.compile(r'\d+')})
        ids = [i.get('data-tp-event') for i in ids if i]
        return ids, 'stavropol', 'Ставропольский цирк'

    async def load_all_events_ONE(self, url_strip, url_to_load):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'pragma': 'no-cache',
            'referer': url_strip,
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }

        all_events = []
        for i in range(1,8):
            #Please note URL may change!!!
            url = f'{url_to_load}{i}'
            r = await self.session.get(url, headers=headers)
            if r.ok:
                soup = BeautifulSoup(r.text, 'lxml')
                events_all = soup.find_all(class_=re.compile(r'calendar__item'))
                if len(events_all) == 0:
                    break
                all_events.extend(events_all)
            else:
                break
        return all_events
    
    def make_events_ONE(self, title, slug, venue, all_events):
        a_events = []
        for event in all_events:
            date_now = datetime.now()
            current_year = date_now.year
            current_month = date_now.month-1
            short_months_in_russian = [
            "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

            day = event.find(class_=re.compile(r'day')).text.strip()
            month = event.find(class_=re.compile(r'mounth')).text.strip()[:3].lower().replace('мая','май')
            month_index = short_months_in_russian.index(month)
            if month_index < current_month:
                current_year += 1

            times = event.find_all('a')
            for i in times:
                if 'Купить' not in i.text:
                    continue
                id = i.get('data-tp-event')
                time = i.text.split('—')[0].strip()
                full_date = f"{day} {month.capitalize()} {current_year} {time}"
                url = f"https://ticket-place.ru/widget/{id}/data|{slug}"
                a_events.append(OutputEvent(title=title, href=url, 
                                            date=full_date, venue=venue))
        return a_events
    
    async def load_all_visible_events_TWO(self, url):
        r = await self.session.get(url=url, headers=self.headers)
        soup = BeautifulSoup(r.text, 'lxml')
        self.debug(r.text)
        events_ids = soup.find_all('a', attrs={'data-tp-event': re.compile(r'\d+')})
        events_ids = [i.get('data-tp-event') for i in events_ids if i]
        return events_ids


    async def get_info_about_event_TWO(self, id, slug, venue):
        url_to_api = f'https://ticket-place.ru/widget/{id}/data'
        info_about = await self.session.get(url_to_api, headers=self.headers)
        info_about.encoding = 'utf-8'
        info_about = info_about.json()

        title = info_about.get("data").get("name")
        id = info_about.get("data").get("id")
        href = f'https://ticket-place.ru/widget/{id}/data|{slug}'
        date = self.reformat_date(info_about.get("data").get("datetime"))

        return OutputEvent(title=title, href=href, 
                                            date=date, venue=venue)
    
    
    async def load_all_dates_TWO(self, id, slug, venue):
        a_events = []
        url = f'https://ticket-place.ru/widget/{id}/similar'
        all_events_json = await self.session.get(url, headers=self.headers)
    
        for i in all_events_json.json().get("events"):
            title = i.get("name")
            id_new = i.get("id")
            href = f'https://ticket-place.ru/widget/{id_new}/data|{slug}'
            date = self.reformat_date(i.get("datetime"))
            a_events.append(OutputEvent(title=title, href=href, 
                                            date=date, venue=venue))

        return a_events

    async def body(self):
        a_events = []

        for url, info in self.urls_ONE.items():
            #self.debug(url)
            '''https://ticket-place.ru/calendar-widget/ для поиска events'''
            try:
                url_strip = re.search(r'(?<=://).+(?=/)', url)[0]
                title, slug, venue, url_to_load = info

                all_events = await self.load_all_events_ONE(url_strip, url_to_load)
                a_events_ONE = self.make_events_ONE(title, slug, venue, all_events)
                a_events.extend(a_events_ONE)
            except Exception as ex:
                self.warning(f'Some problem in {url} {info} {ex}')
        
        for url, info in self.urls_TWO.items():
            #self.debug(url)
            '''https://ticket-place.ru/widget/{id}/similar для поиска events'''
            try:
                events_box = set()

                if isinstance(info, tuple):
                    slug, venue = info
                    events_ids = await self.load_all_visible_events_TWO(url)
                    first_event = await self.get_info_about_event_TWO(events_ids[0], slug, venue)
                    events_box.add(first_event)

                elif isinstance(info, list):
                    evnt_id, slug, venue = info
                    try:
                        first_event = await self.get_info_about_event_TWO(evnt_id, slug, venue)
                        events_box.add(first_event)
                    except Exception:
                        ...
                    events_ids = await self.load_all_dates_TWO(evnt_id, slug, venue)
                    events_box.update(events_ids)
                    
                elif isinstance(info, str):
                    function = getattr(self, info)
                    events_ids, slug, venue = await function()
                    first_event = await self.get_info_about_event_TWO(events_ids[0], slug, venue)
                    events_box.add(first_event)

                count = 10
                while len(events_box) < len(events_ids) and count > 1:
                    id = events_ids[len(events_box)-1]
                    if count < 8:
                        if count == 7:
                            box_events_id = set(i.href.split('/')[-2] for i in events_box)
                            box = list(set(events_ids) - box_events_id)
                        from random import choice
                        id = choice(box)
                    to_a_events = await self.load_all_dates_TWO(id, slug, venue)
                    events_box.update(to_a_events)
                    count -= 1
                a_events.extend(events_box)

            except Exception as ex:
                self.warning(f'Some problem in {url} {info} {ex}')


        for event in a_events:
            #self.info(event)
            self.register_event(event_name=event.title ,url=event.href,
                                       date=event.date , venue=event.venue)
                
            