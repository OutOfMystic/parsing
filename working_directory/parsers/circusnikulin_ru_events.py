import json
import requests
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils import utils
from parse_module.utils.date import month_list
from parse_module.utils.parse_utils import lrsplit, double_split
from itertools import groupby


class Parser(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.circusnikulin.ru/tickets'
        self.company_id = ''

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def get_events(self, events_data):
        a_events = []
        for date_dict in events_data:
            for event in date_dict['events']:
                # if not event['has_free_places']:
                #     continue

                title = event['show_name']
                day, month, year = event['date_parts']['date'].split()
                time = event['begin_time']
                date = f'{day} {month[:3].capitalize()} {year} {time}'
                scene = event['location_scene']

                event_id = event['id']
                show_id = event['show_id']
                href = f'https://spa.profticket.ru/customer/{self.company_id}/shows/{show_id}/#{event_id}'
                a_events.append([title, href, date, scene, self.company_id, event_id, show_id])

        return a_events

    async def get_events_request(self, date, page=1, period_id=4):
        # date - 2023.01
        url = f'https://widget.profticket.ru/api/event/list/?company_id={self.company_id}&type=events&page={page}&period_id={period_id}&date={date}&language=ru-RU'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
            'host': 'widget.profticket.ru',
            'origin': 'https://spa.profticket.ru',
            'referer': 'https://spa.profticket.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)

        return r.json()['response']['items']

    async def get_months_request(self, period_id=0):
        url = f'https://widget.profticket.ru/api/event/list-filter/?company_id={self.company_id}&period_id={period_id}&language=ru-RU'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
            'host': 'widget.profticket.ru',
            'origin': 'https://spa.profticket.ru',
            'referer': 'https://spa.profticket.ru/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)

        return r.json()['response']['months']['months_by_year']

    def get_dates(self, months_by_year):
        dates = []
        for year, year_dict in months_by_year.items():
            for month_dict in year_dict.values():
                day, month, fake_year = month_dict['date'].split('.')
                date = f'{year}.{month}'

                dates.append(date)
        return dates

    async def get_request(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
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
        r = await self.session.get(self.url, headers=headers)

        # def decode_brotli(text):
        #     from brotli import decompress
        #     return decode(text.encode('UTF-8'), 'unicode-escape')
        #
        # r_text = decode_unicode_escape(r.text)
        
        self.company_id = double_split(r.text, 'https://widget.profticket.ru/customer/', '/shows')

        return r.text

    async def body(self):
        await self.get_request()
        dates = self.get_dates(await self.get_months_request())

        a_events = []
        for date in dates:
            a_events += self.get_events(await self.get_events_request(date))

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], scene=event[3], company_id=event[4], event_id=event[5], show_id=event[6])
