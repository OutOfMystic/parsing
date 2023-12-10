import json
import requests
from bs4 import BeautifulSoup
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils
from parse_module.utils.date import month_list


class Parser(EventParser):
    proxy_check_url = 'https://ticket.bolshoi.ru/shows'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://ticket.bolshoi.ru/shows'
        self.csrf = ''

    def before_body(self):
        self.session = ProxySession(self)

    def deception_request(self):
        url = 'https://vk.com/'
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
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
        self.debug(r.text)
        self.debug(r.cookies.get_dict())

    def main_page_request(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'connection': 'keep-alive',
            'DNT': '1',
            'host': 'ticket.bolshoi.ru',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0'
        }
        r = self.session.get(self.url, headers=headers)
        self.debug(r.text)
        self.debug(r.cookies)

    def get_csrf(self):
        url = 'https://ticket.bolshoi.ru/api/csrfToken'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'connection': 'keep-alive',
            'host': 'ticket.bolshoi.ru',
            'referer': self.url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        self.debug(r.text)

        return r.json()['_csrf']

    def get_events(self):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'connection': 'keep-alive',
            'host': 'ticket.bolshoi.ru',
            'referer': self.url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'X-CSRF-Token': self.csrf
        }
        r = self.session.get('https://ticket.bolshoi.ru/api/v1/client/shows', headers=headers)
        self.debug(self.csrf)
        self.debug(r.text)
        a_events = []
        for event in r.json():
            if not event['freeSeats']:
                continue
            date = event['specDate'].split('-')
            time = event['startTime'].split(':')
            full_date = f'{date[2]} {month_list[int(date[1])]} {date[0]} {time[0]}:{time[1]}'
            url = f'https://ticket.bolshoi.ru/show/{event["showId"]}'
            a_events.append([event['description'], url, full_date, event['hallName']])
        return a_events

    def body(self):
        self.deception_request()
        self.main_page_request()
        self.csrf = self.get_csrf()
        a_events = self.get_events()

        for event in a_events:
            self.debug(event)
            self.register_event(event[0], event[1], date=event[2], scene=event[3])
