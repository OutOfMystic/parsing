import json
import secrets
import string
import requests
from bs4 import BeautifulSoup, PageElement
from loguru import logger

from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession
import re


class BolTheaterParser(EventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.our_urls = {
        }
        self.url = 'https://bol-theater.ru/afisha.html'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        month_years = [month_year.text.split() for month_year in soup.find_all('div', class_='afisha_month_link')]
        month_years = {month_year[0]: month_year[1] for month_year in month_years}
        a_events = []
        for event_card in soup.find_all('div', class_='afisha_monthes'):
            event_blocks = event_card.find_all('div', class_='td')
            date_block = event_blocks[0]
            date = self.format_date(date_block, month_years)

            title = event_blocks[2].find('div', class_='concert-title').text
            href_elem = event_blocks[4].find('a')
            # href_wlink = double_split(href_elem.get('onclick'), 'wlink=', "&")
            # href_date = double_split(href_elem.get('onclick'), 'date=', "';")
            # href = f'https://bol-theater.ru/{href_elem.get("href")}?wlink={href_wlink}&date={href_date}'
            href = 'https://bol-theater.ru/' + double_split(href_elem.get('onclick'), "document.location.href='", "';")

            scene = event_blocks[2].find('div', class_='concert-descr').text

            a_events.append([title, href, date, scene])

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def format_date(self, date_block, month_years):
        day = date_block.find('div', class_='concert-title').text
        month_time = date_block.find_all('div', class_='concert-descr')
        month = month_time[0].text.split(',')[0]
        year = month_years[month]
        month = month[:3]
        time = month_time[1].text

        return f'{day} {month} {year} {time}'

    def get_events(self):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'bol-theater.ru',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.user_agent,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        r = self.session.get(self.url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.parse_events(soup)

        return a_events

    def body(self):
        a_events = self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], scene=event[3])

