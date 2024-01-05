import re
from datetime import datetime
from time import sleep

from bs4 import BeautifulSoup
from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split



class Redkassa(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.urls = [
            'https://redkassa.ru/venue/sochi_park',
            'https://redkassa.ru/venue/teatralniy_zal_mmdm',
            'https://redkassa.ru/venue/gubernskiy_teatr'
        ]
        self.KASSA = 'https://redkassa.ru/'
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
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

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def get_date_from_url(href):
        input_string = re.search(r'(?<=/)\d{2}.+', href).group(0)
        date_str, time_str = input_string.split('/')
        months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
        day, month, year = map(int, date_str.split('-'))
        month_text = months[month - 1]
        formatted_day = f"{day:02}"
        time_obj = datetime.strptime(time_str, "%H-%M")
        formatted_time = time_obj.strftime("%H:%M")

        return f"{formatted_day} {month_text} {year} {formatted_time}"
    

    def take_all_events(self, url):
        r = self.session.get(url, headers=self.headers)

        venue_id = double_split(r.text, '"venueId":', ',')
        venue_id = venue_id.strip(' "')

        a_events = []

        soup = BeautifulSoup(r.text, 'lxml')
        all_events = soup.find_all('li', {'class':'theatre-list__item'})
        a_events.extend(all_events)

        while len(all_events) >= 20:
            url_post = 'https://redkassa.ru/Catalog/RepertoireListingItems'
            headers2 = {
                    'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'accept-encoding': 'gzip, deflate, br',
                    'accept-language': 'ru,en;q=0.9',
                    'cache-control': 'max-age=0',
                    'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
                    'sec-ch-ua-mobile': '?0',
                    'Origin': self.KASSA,
                    'Referer': url,
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-user': '?1',
                    'upgrade-insecure-requests': '1',
                    'user-agent': self.user_agent,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            data = {
                'AvailableVenueIds[]': venue_id,
                'Skip': len(a_events),
                'Take': '20',
                'IsAvailableWithoutPicture': 'true',
                'IsRootCategoriesOnly': 'false',
                'IsPushkinCardOnly': 'false',
                'sortingAlias': 'bydate'
                }
            res = self.session.get(url_post, headers=headers2, data=data)
            soup = BeautifulSoup(res.text, 'lxml')
            all_events = soup.find_all('li', {'class':'theatre-list__item'})
            a_events.extend(all_events)
            sleep(4)
        return a_events 


    def parse_events(self, all_events):
        a_events = []

        # count_page = 1
        # while True:
        #     url = start_url + f'&page={count_page}'
        #     soup = self.requests_to_events(url)
        #     count_page += 1

        #     all_events = soup.select('li.theatre-list__item')
        #     if len(all_events) == 0:
        #         break

        for event in all_events:
            check_price = event.find('p', class_='event-snippet__price')
            if check_price is None:
                continue

            title_and_href = event.find('a', class_='event-snippet__title')
            title = title_and_href.text.strip()
            title = title.replace("'", '"')

            href = title_and_href.get('href')
            href = f'https://redkassa.ru{href}'

            date = event.find('span', class_='event-snippet__info-item').text.strip()

            if 'с' in date and 'по' in date:
                soup = self.requests_to_events(href)
                dates_and_venues = soup.select('tr.event-tickets__row')
                
                for date_and_venue in dates_and_venues:
                    href1 = date_and_venue.find('a', class_='event-tickets__btn')
                    if href1 is None:
                        continue
                    href1 = href1.get('href')
                    
                    normal_date = self.get_date_from_url(href1)

                    venue = date_and_venue.find('span', class_='bf-sector-title').text.strip()
                    venue = venue.replace("'", '"')
                    if 'ММДМ' in venue:
                        venue = 'Дом музыки' 

                    a_events.append([title, href1, normal_date, venue])

            else:
                date = date.split('.')
                date[1] = month_list[int(date[1])]
                normal_date = ' '.join(date)
                soup = self.requests_to_events(href)
 
                venue = soup.find('a', class_='event-header__location-link')
                if venue is None:
                    venue = soup.find('a', class_=['event-snippet__info-item', 'event-snippet__info-item--place'])
                venue = venue.text.strip()
                venue = venue.replace("'", '"')
                if 'ММДМ'  in venue:
                    venue = 'ММДМ Дом музыки' 

                a_events.append([title, href, normal_date, venue])

        return a_events

    def requests_to_events(self, url):
        r = self.session.get(url, headers=self.headers)
        return BeautifulSoup(r.text, 'lxml')

    def new_get_all_events(self, url):
        soup = self.requests_to_events(url)

        all_mounth = soup.find_all('div', class_=re.compile(r'dates-slider__item'))
        all_mounth_url = [ f"{self.KASSA}{i.find('a').get('href')}" for i in all_mounth if i.find('a') ]
        venue = soup.find('h1').text.strip()
        if 'ММДМ' in venue:
                venue = 'ММДМ Дом музыки'

        a_events = []
        for month_url in all_mounth_url:
            try:
                soup2 = self.requests_to_events(month_url)
                events = soup2.find_all('div', class_='afisha__row')
                for event in events:
                    events_box = event.find_all('div', class_='afisha__event-row')
                    for a_event in events_box:
                        a = a_event.find('a', class_='afisha__event-link')
                        title = a.text.strip()
                        href = f"{self.KASSA}{a.get('href')}"
                        date = self.get_date_from_url(a.get('href'))
                        a_events.append((title, href, date, venue))
            except Exception as ex:
                self.error(ex)
        return a_events


    async def body(self):
        a_events = []
        for url in self.urls:
            # Неверные url для seats парсера, если 2 или более ивента в 1 день
            #all_events = self.take_all_events(url)
            #a_events = self.parse_events(all_events)

            a_events += self.new_get_all_events(url)

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue=event[3])
                
