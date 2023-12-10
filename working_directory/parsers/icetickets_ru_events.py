from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils


class Icetickets(EventParser):
    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://icetickets.ru/'

    def before_body(self):
        self.session = ProxySession(self)

        self.our_places_data = [
            #'https://icetickets.ru/vid-meropriyatiya/shou',
            'https://icetickets.ru/vid-meropriyatiya/kreml',
            #'https://icetickets.ru/vid-meropriyatiya/balet',
            #'https://icetickets.ru/vid-meropriyatiya/myuzikly',
            #'https://icetickets.ru/vid-meropriyatiya/kontserty',
            #'https://icetickets.ru/vid-meropriyatiya/detyam',
            #'https://icetickets.ru/vid-meropriyatiya/spektakli',
            'https://icetickets.ru/place/zal-tserkovnykh-soborov-khrama-khrista-spasitelya-zal-tserkovnykh-soborov--000000578'
        ]

    def parse_events(self, url):
        a_events = []

        soup = self.get_events(url)
        all_events = soup.find_all('div', class_='col-sm-6')

        axaj_button = soup.find('div', class_='refresh-row')
        if axaj_button is not None and axaj_button.get('style') is None:
            data_to_url = axaj_button.find('a')
            id_for_requests = data_to_url.get('id')
            page = data_to_url.get('href').replace('#', '')
            while True:
                url = f'https://icetickets.ru/lib/custom_ajax.php?oper=event_list&guid={id_for_requests}&page={page}'
                axaj_soup = self.get_axaj_events(url)
                all_events_from_axaj = axaj_soup.find_all('div', class_='col-sm-6')
                if len(all_events_from_axaj) > 0:
                    all_events.extend(all_events_from_axaj)
                    page = str(int(page) + 1)
                else:
                    break

        
        for event in all_events:
            title_and_href = event.select('.event-card__title a')[0]
            title = title_and_href.text.strip()
    
            venue = event.select('.event-card__param.event-card__param--place a')[0].text.strip()
            if 'кремль' in venue.lower() or 'ГКД' in venue:
                venue = 'Кремлёвский дворец'

            href = title_and_href.get('href')
            href = 'https://icetickets.ru' + href
            try:
                soup = self.get_events(href)
                all_href_and_date = soup.find('select', class_='select-date-select')
                all_option = all_href_and_date.find_all('option', value=True)
                for href_and_date in all_option:
                    date = href_and_date.text.strip().split() #['2', 'декабря', '2023', 'Суббота,', '18:00', 'Купить']
                    if len(date) < 3:
                        continue
                    normal_date = f"{date[0]} {date[1].capitalize()[:3]} {date[2]} {date[-2]}"
            
                    href = href_and_date.get('value').strip('~')
                    href = f'https://icetickets.ru/event_tickets/?guid={href}'
                    if len(href) > 100:
                        continue

                    a_events.append([title, href, normal_date, venue])
            except Exception as ex:
                self.error(f' {title} NOT OUR PROBLEM! Maybe this url is 304 redirect! {self.url} {ex}')

        return a_events

    def get_axaj_events(self, url):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        r = self.session.get(url, headers=headers)
        return BeautifulSoup(r.text, 'lxml')

    def get_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Yandex";v="23"',
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
        return BeautifulSoup(r.text, 'lxml')

    def body(self):
        a_events = []
        for url in self.our_places_data:
            for event in self.parse_events(url):
                if event not in a_events:
                    self.register_event(event[0], event[1], date=event[2], venue=event[3])
                    a_events.append(event)
