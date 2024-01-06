import json
from time import sleep
from datetime import datetime

from bs4 import BeautifulSoup
from telebot import TeleBot

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils import utils


class TNA(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3200
        self.driver_source = None
        self.urls = [
            'https://tna-tickets.ru/sport/akbars/',
            'https://tna-tickets.ru/',
        ]
        self.BOT_TOKEN = '6002068146:AAHx8JmyW3QhhFK5hhdFIvTXs3XFlsWNraw'
        self.telegram_bot = TeleBot(self.BOT_TOKEN)

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def parse_events(self, soup):
        a_events = []

        items_list = soup.find_all('div', class_='tickets_item')
        items_list += soup.find_all('div', class_='home_events_item')

        for item in items_list:
            try:
                title = item.find_all('b')
                first_team = title[0].text
                second_team = title[1].text
                title = first_team[:first_team.index(' (')] + ' - ' + second_team[:second_team.index(' (')]
            except IndexError:
                title = item.select('div.home_events_item_info a')[0].text.replace("'", '"')
            
            date_now = datetime.now()
            current_year = date_now.year
            current_month = date_now.month-1
            short_months_in_russian = [
            "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

            try:
                date_and_time = item.find('div', class_='tickets_item_date').text
                day, month, time = date_and_time.replace(' /', '').split()
                month = month[:3].strip().replace('мая','май')
                month_find = short_months_in_russian.index(month)
                #date_and_time[1] = date_and_time[1].title()[:3]
                if month_find < current_month:
                    current_year += 1
                normal_date = f"{day} {month.title()} {current_year} {time.strip()}"

            except AttributeError:
                date_and_time = item.find('div', class_='home_events_item_date').text
                date, time = date_and_time.split('/')
                day, month = date.split()
                month = month[:3]
                month_find = short_months_in_russian.index(month)
                time = time.replace(' ', '')

                if month_find < current_month:
                    current_year += 1
                normal_date = f"{day} {month.title()} {current_year} {time.strip()}"

            parametr_for_get_href = item.find('a').get('href')
            url = f'https://tna-tickets.ru{parametr_for_get_href}'
            soup = await self.request_for_href(url)

            try:
                href = soup.select('.event_view_header .border_link')[0].get('href')
            except IndexError:
                href = soup.find('a', class_='ticket-link').get('href')
            href = f'https://tna-tickets.ru{href}'

            a_events.append([title, href, normal_date])

        return a_events

    async def request_for_href(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/web'
                      'p,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'tna-tickets.ru',
            'referer': 'https://tna-tickets.ru/sport/akbars/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = await self.session.get(url, headers=headers)

        return BeautifulSoup(r.text, "lxml")

    async def get_events(self, url: str):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/we'
                      'bp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'tna-tickets.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
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

        soup = BeautifulSoup(r.text, 'lxml')

        a_events = await self.parse_events(soup)

        return a_events

    def check_new_events(self, a_events):
        events_new = { f"{i[0]} {i[2]}": i[1] for i in a_events}
        chat_id = '-1001823568418'
        flag = 0

        with open('files/events/akbars_events.json', 'r', encoding='utf-8') as file:
            events_old = json.load(file)
            for name, url in events_new.items():
                if name not in events_old:
                    flag = 1
                    message = f'New event \n{name}\n {url}'
                    self.telegram_bot.send_message(chat_id, message, parse_mode='HTML')
        if flag:
            with open('files/events/akbars_events.json', 'w',encoding='utf-8') as file2:
                json.dump(events_new, file2, indent=4, ensure_ascii=False)

    async def body(self):
        for url in self.urls:
            a_events = await self.get_events(url)
            
            if url == 'https://tna-tickets.ru/sport/akbars/':
                try:
                    self.check_new_events(a_events)
                except Exception as ex:
                    self.error(ex, 'Exception in tickets_tna_ru_events, problems with TG bot')

            for event in a_events:
                self.register_event(event[0], event[1], date=event[2])
