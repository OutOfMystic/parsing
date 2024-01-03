import json
import secrets
import string
import requests
from bs4 import BeautifulSoup, PageElement
from loguru import logger

from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.manager.proxy.instances import ProxySession
import re


class Parser(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.our_urls = {
            'https://biletcentr.com/cat/176/CategoryId/2/': '*', #theatre_all
            #'https://biletcentr.com/cirk/': '*',
            'https://biletcentr.com/cat/229/StageId/63/': '*',  # Цирк вернадского
            'https://biletcentr.com/cirk-na-cvetnom/': '*', # Никулина цирк на цветном
            #'https://biletcentr.com/cat/229/StageId/55/': '*',  # Цирк на цветном
            'https://biletcentr.com/cat/229/PlaceId/36/': '*', #armii teatr
        }

    def before_body(self):
        self.session = ProxySession(self)

    def r_str(self):
        letters_and_digits = string.ascii_letters + string.digits
        crypt_rand_string = ''.join(secrets.choice(
            letters_and_digits) for i in range(16))
        return (crypt_rand_string)

    def get_places(self, soup):
        places = []

        place_btns = soup.find_all('a', class_='btn')
        for place_btn in place_btns:
            href = place_btn.get('href')
            place_row = place_btn.parent.parent.parent
            place_name = place_row.find('h2').text.strip()

            places.append({
                'name': place_name,
                'url': 'https://biletcentr.com' + href,
                'short_url': href,
            })

        return places

    def get_events(self, soup):
        a_events = []

        all_events_soups = [soup]
        bt_areas = soup.find_all('div', class_='bt_area')

        if not bt_areas:
            return a_events

        if bt_areas[-1].text == 'Показать еще события':
            php_id = self.get_uri(soup)
            r_str = self.r_str()

            while True:
                more_soup, resp_pr = self.load_more_events(php_id, r_str)
                all_events_soups.append(more_soup)

                if resp_pr <= 0:
                    break

        for events_soup in all_events_soups:
            bt_areas = events_soup.find_all('div', class_='bt_area')

            if not bt_areas:
                continue

            last = -1 if bt_areas[-1].get('id') == 'LoadMore' else len(bt_areas)
            for bt_area in bt_areas[:last]:
                if 'купить' not in bt_area.text.lower():
                    continue

                event_row = bt_area.parent.parent
                href = 'https://biletcentr.com' + bt_area.find('a', class_='btn').get('href')
                title = event_row.find('h2').text.strip()
                full_place = event_row.find('div', class_='rep_date').text.strip().split(', ')
                venue = self.format_venue(full_place[0])
                scene = 'not_present'
                if len(full_place) > 1:
                    scene = full_place[-1]

                date = event_row.find('div', class_='rep_23').text.strip()
                date = self.format_date(date)

                a_events.append((title, href, date, scene, venue))

        return a_events

    def format_venue(self, venue):
        if '(' in venue and ')' in venue:
            city = double_split(venue, '(', ')')
            venue = venue.replace(f'({city})', '').strip()

        return venue

    def get_uri(self, soup):
        soup_txt = str(soup)
        p_id = double_split(soup_txt, "RequestUri=", "'")
        return p_id

    def load_more_events(self, php_id, r_str):
        url_p = 'https://biletcentr.com/Scripts/LoadMoreRepertoire.script.php'
        url_pr = 'https://biletcentr.com/Scripts/LoadMoreRepertoireNextCount.script.php'
        headers = {'cookie': 'PHPSESSID='f'{r_str}'}
        payload = {'RequestUri': php_id}
        resp_p = self.session.post(url_p, data=payload, headers=headers)
        resp_pr = self.session.post(url_pr, data=payload, headers=headers)
        more_soup = BeautifulSoup(resp_p.text, 'lxml')
        resp_pr = int(resp_pr.text)

        return more_soup, resp_pr

    def format_date(self, date):
        date = date.split(',')[0] + date.split(',')[2]
        day, month, y, t = date.strip().split(' ')

        if len(day) == 1:
            day = '0' + day

        month = month[:3].capitalize()

        date_f = f'{day} {month} {y} {t}'
        return date_f

    def is_places_page(self, soup):
        all_places = soup.find_all('div', id='allplacelist')
        if len(all_places):
            return True

    def url_request(self, url):
        r = self.session.get(url, headers={'user-agent': self.user_agent})
        soup = BeautifulSoup(r.text, 'lxml')

        return soup

    def get_afisha_urls(self, our_url, our_places):
        afisha_urls = []
        soup = self.url_request(our_url)

        if self.is_places_page(soup):
            places = self.get_places(soup)

            if our_places == '*':
                for place in places:
                    afisha_urls.append(place['url'])
            else:
                for our_place_short in our_places:
                    for place in places:
                        if our_place_short.lower() in place['name'].lower():
                            afisha_urls.append(place['url'])
                            break
        else:
            afisha_urls.append(our_url)

        return afisha_urls

    def body(self):
        afisha_urls = []
        for our_url, our_places in self.our_urls.items():
            afisha_urls += self.get_afisha_urls(our_url, our_places)

        a_events = []
        for url in afisha_urls:
            soup = self.url_request(url)
            a_events += self.get_events(soup)

        a_events = list(set(a_events))

        skip_events = []

        for event in a_events:
            if event[1] in skip_events:
                continue
            # if 'Цирк на Вернадского' in event[3]: #Вернадский цирк отсеиваем
            #     if  any([i in event[2] for i in [ 
            #             '03 Янв 2024 10:00', '03 Янв 2024 13:00', '03 Янв 2024 16:00', '03 Янв 2024 19:00',
            #     ]]):
            #         continue
            # elif 'Цирк на Цветном бульваре' in event[4]:
            #     if any([i in event[2] for i in [ 
            #             '13 Янв 2024 14:30', '13 Янв 2024 18:00', '20 Янв', '21 Янв'
            #             ]]):
            #         continue
            self.register_event(event[0], event[1], date=event[2], scene=event[3], venue=event[4])
