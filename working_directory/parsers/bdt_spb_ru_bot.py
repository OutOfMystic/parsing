import json
import asyncio
import itertools
from datetime import datetime
from typing import NamedTuple, Optional, Union

from requests.exceptions import JSONDecodeError
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils.parse_utils import double_split
from parse_module.utils.date import month_list
from parse_module.coroutines import AsyncEventParser


class TicketData(NamedTuple):
    place_data: str
    data_tickets_cypher: str
    tariff_id: int


class UserData(NamedTuple):
    email: str
    first_name: str
    last_name: str


class BdtSpbBot(AsyncEventParser):
    proxy_check = SpecialConditions(url='https://spb.ticketland.ru/')

    def __init__(self, *args: list, **extra: dict) -> None:
        super().__init__(*args, **extra)
        self.driver_source = None

        self.BOT_TOKEN_1 = '6028219837:AAEJARbm2MmOb6Xp44HtEOMeQ-LG3lMtsJo'
        self.BOT_TOKEN_2 = '6034622109:AAEKT9609vkJrpLwa-8MuIydllhTzeJwHIY'
        self.BOT_TOKEN_3 = '6033589055:AAE5XdOnnqIMza0mzGM3PBIqiNkOjTiVgMk'
        self.BOT_TOKEN_4 = '6243523201:AAHU_3Lq4sxpo_ka06M1AHg11_zztSU7d6Y'
        self.BOT_TOKEN_5 = '5882380456:AAF_7iqftkn_6gs71jmASnuecNewt7MaSP8'
        self.bots = [
            TeleBot(self.BOT_TOKEN_1),
            TeleBot(self.BOT_TOKEN_2),
            TeleBot(self.BOT_TOKEN_3),
            TeleBot(self.BOT_TOKEN_4),
            TeleBot(self.BOT_TOKEN_5),
        ]
        self.generate_bots = itertools.cycle(self.bots)
        self.all_chat_id = [
            '1495697329',
            '454746771',
            '454277155',
            '1653020880',
            '763239734',
            '236726824',
            '1128666119',
            '647298152',
            '1700684820',
            '378191576',
            '346819032',
            '472533395',
        ]

        self.csrf = None
        self.max_ticket_in_basket = 4

        self.urls = []
        self.event_name = 'ЛЕТО ОДНОГО ГОДА'
        # self.event_name = 'ДЖУЛЬЕТТА'
        self.event_date = None

        self.users_data = [
            UserData(email='knzejiusrh@rambler.ru', first_name='Алиса', last_name='Семина'),
            UserData(email='nptbcgdtmh@rambler.ru', first_name='Сергей', last_name='Кузнецов'),
            UserData(email='sdyyowgvay@rambler.ru', first_name='Максим', last_name='Игнатьев'),
            UserData(email='sfsfxfqgok@rambler.ru', first_name='Артём', last_name='Маркин'),
            UserData(email='mqqfiggxsa@rambler.ru', first_name='Ксения', last_name='Котова'),
            UserData(email='lnboxwdzpb@rambler.ru', first_name='Савелий', last_name='Васильев'),
            UserData(email='gnmkbvewdy@rambler.ru', first_name='Ксения', last_name='Орлова'),
            UserData(email='vouywyehes@rambler.ru', first_name='Александр', last_name='Черкасов'),
            UserData(email='fcinvmfdnt@rambler.ru', first_name='Василий', last_name='Архипов'),
            UserData(email='jdfotpuiqy@rambler.ru', first_name='Тимофей', last_name='Королев'),
            UserData(email='ptjexbdlio@rambler.ru', first_name='Максим', last_name='Королев'),
            UserData(email='tznpxgkxuz@rambler.ru', first_name='Варвара', last_name='Смирнова'),
            UserData(email='eknnlkiekp@rambler.ru', first_name='Ксения', last_name='Фролова'),
            UserData(email='hjbgnvvczg@rambler.ru', first_name='Дамир', last_name='Петров'),
            UserData(email='tudlzjbffr@rambler.ru', first_name='Максим', last_name='Щербаков'),
            UserData(email='zuiipublai@rambler.ru', first_name='Эмилия', last_name='Морозова'),
            UserData(email='ipgadijyhy@rambler.ru', first_name='Максим', last_name='Ларионов'),
            UserData(email='dzavznbydj@rambler.ru', first_name='Борис', last_name='Алексеев'),
            UserData(email='aozycpbqvw@rambler.ru', first_name='Мирон', last_name='Герасимов'),
            UserData(email='cgplyrzyiv@rambler.ru', first_name='Анна', last_name='Вавилова'),
            UserData(email='nnvjvznntn@rambler.ru', first_name='Нелли', last_name='Захарова'),
            UserData(email='syadhtmbaw@rambler.ru', first_name='Артём', last_name='Воробьев'),
            UserData(email='ljtiteifgj@rambler.ru', first_name='Алина', last_name='Суслова'),
            UserData(email='szkchjgivk@rambler.ru', first_name='Илья', last_name='Сергеев'),
            UserData(email='gyxibysbjv@rambler.ru', first_name='Марк', last_name='Сергеев'),
            UserData(email='kbnwybibdq@rambler.ru', first_name='София', last_name='Самсонова'),
            UserData(email='xemcatvxac@rambler.ru', first_name='Анна', last_name='Михайлова'),
            UserData(email='tgtmzogjpg@rambler.ru', first_name='Марк', last_name='Назаров'),
            UserData(email='adidmssjok@rambler.ru', first_name='Александр', last_name='Майоров'),
            UserData(email='iuzayrpxfz@rambler.ru', first_name='Матвей', last_name='Панфилов'),
            UserData(email='lumrwygzvz@rambler.ru', first_name='Роман', last_name='Сидоров'),
            UserData(email='muzbtgqdif@rambler.ru', first_name='Маргарита', last_name='Попова'),
            UserData(email='gykylgujsd@rambler.ru', first_name='Алия', last_name='Юдина'),
            UserData(email='bvyejffjmm@rambler.ru', first_name='Софья', last_name='Тимофеева'),
            UserData(email='djcjydbocy@rambler.ru', first_name='Аделина', last_name='Фомина'),
            UserData(email='vcyytbpovx@rambler.ru', first_name='Артём', last_name='Зайцев'),
            UserData(email='jesbrcyjjo@rambler.ru', first_name='Егор', last_name='Кузнецов'),
            UserData(email='bygaecsmjm@rambler.ru', first_name='Ева', last_name='Егорова'),
            UserData(email='ewohlgulnf@rambler.ru', first_name='Амира', last_name='Андреева')
        ]
        self.generate_accounts = itertools.cycle(self.users_data)

        self.tickets_data_to_buy = {
            # 'Ложа №18 бельэтажа, левая сторона': '*',
            # 'Партер левая сторона': {
            #     'place_row': ['3'],
            #     'place_seat': [str(seat) for seat in range(58, 62)],
            #     'place_price': 2600
            # },
            # 'Партер правая сторона': '*',
            # 'Бельэтаж левая сторона': {
            #     'place_row': ['5'],
            # }
            '*': 501
        }
        self.all_ticket_in_event = {}
        self.tickets_already_sent = {}

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def _parse_free_tickets(self, soup: BeautifulSoup, event_date: str) -> list[TicketData]:
        self.csrf = soup.find('meta', attrs={'name': 'csrf-token'}).get('content')
        data_to_url = soup.select('body script')[0].text
        data_to_url = double_split(data_to_url, 'webPageId: ', ',')

        url = (
            f'https://spb.ticketland.ru/hallview/map/{data_to_url}/'
            f'?json=1&all=1&isSpecialSale=0&tl-csrf={self.csrf}'
        )
        json_data = await self._request_to_place(url)
        return self._get_free_tickets(json_data, event_date)

    def _get_free_tickets(self, json_data: json, event_data: str) -> list[TicketData]:
        free_tickets = []

        try:
            all_places = json_data.get('places')
        except AttributeError:
            return []
        for place in all_places:
            place_sector_name = place.get('section').get('name')
            place_row = place['row']
            place_seat = place['place']
            place_price = place['price']

            place_id = int(place['id'])
            data_tickets_cypher = place['cypher']
            self.all_ticket_in_event[place_id] = data_tickets_cypher

            if self._filter_ticket(place_sector_name, place_row, place_seat, place_price):
                place_data = f'{place_sector_name} Ряд {place_row} Место {place_seat} Цена {place_price}'
                if self.tickets_already_sent.get(event_data) is not None and place_data in list(self.tickets_already_sent[event_data].keys()):
                    continue
                tariff_id = place['tariff']

                free_tickets.append(
                    TicketData(
                        place_data=place_data,
                        data_tickets_cypher=data_tickets_cypher,
                        tariff_id=tariff_id
                    )
                )
        return free_tickets

    def _filter_ticket(self, place_sector_name: str, place_row: str, place_seat: str, place_price: int) -> bool:
        price = self.tickets_data_to_buy.get('*')
        if price is not None and place_price <= price:
            return True
        if_sector_name = self.tickets_data_to_buy.get(place_sector_name)
        if if_sector_name is None:
            return False
        elif if_sector_name != '*':
            row_data_to_buy = if_sector_name.get('place_row')
            if row_data_to_buy is not None and place_row not in row_data_to_buy:
                return False
            seat_data_to_buy = if_sector_name.get('place_seat')
            if seat_data_to_buy is not None and place_seat not in seat_data_to_buy:
                return False
            price_data_to_buy = if_sector_name.get('place_price')
            if price_data_to_buy is not None and place_price > price_data_to_buy:
                return False
        return True

    async def _request_to_place(self, url: str) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'spb.ticketland.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        response = await self.session.get(url, headers=headers)
        return response.json()

    async def _find_main_event(self) -> None:
        while True:
            await self._get_href_to_main_event()
            if len(self.urls) != 0:
                break
            await asyncio.sleep(15)

    async def _get_href_to_main_event(self) -> None:
        urls = []

        url = 'https://bdt.spb.ru/afisha'
        soup = await self._requests_to_events(url)
        all_month = soup.select('ul.dirmenu li a[href^="/afisha/?month="]')
        for next_month_href in range(len(all_month) + 1):
            all_event_date = soup.select(
                'div.afisha-row.d-flex.flex-column.flex-wrap.flex-md-row.flex-md-nowrap.pb-3.mb-3.border-bottom'
            )
            for event_date in all_event_date:
                date = event_date.find('span', class_='day').text.strip()
                date = date.split('/')
                date[1] = month_list[int(date[1])]

                all_event = event_date.select('div.d-flex.flex-wrap.flex-md-row.flex-md-nowrap.pt-3.pt-md-0')
                for event in all_event:
                    title = event.find('a', class_='text-secondary')
                    if title is None:
                        title = event.select('span.text-secondary a span')
                        if len(title) == 0:
                            title = event.select('span.text-secondary span b')
                            if len(title) == 0:
                                title = event.select('span.text-secondary p span')
                        try:
                            title = title[0]
                        except IndexError:
                            continue
                    title = title.text.strip()
                    if title.lower() != self.event_name.lower():
                        continue
                    time = event.find('em', class_='color-bdt').text.strip().split('в ')[-1]
                    normal_date = ' '.join(date) + ' ' + time
                    if self.event_date is not None and normal_date != self.event_date:
                        continue
                    href = event.find('a', class_='tl_afisha')
                    if href is None:
                        continue
                    urls.append((href.get('href'), normal_date))

            if next_month_href < len(all_month):
                url = f'https://bdt.spb.ru{all_month[next_month_href].get("href")}'
                soup = await self._requests_to_events(url)
        self.urls = urls

    async def _requests_to_events(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
        response = await self.session.get(url, headers=headers)
        return BeautifulSoup(response.text, 'lxml')

    async def _check_self_url(self, url) -> BeautifulSoup:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'spb.ticketland.ru',
            'pragma': 'no-cache',
            'referer': 'https://bdt.spb.ru/',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        response = await self.session.get(url, headers=headers)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'lxml')
        else:
            self.error(f'Ссылка на мероприятие для откупки билетов вернула код ответа {response.status_code}')
            await self._find_main_event()
            return await self._check_self_url(url)

    def _requests_to_set_ticket_in_basket(self, session: ProxySession, ticket: TicketData, count_tickets_in_basket: int) -> bool:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': 'spb.ticketland.ru',
            'origin': 'https://spb.ticketland.ru',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            'cypher': ticket.data_tickets_cypher,
            'tax': ticket.tariff_id,
            'tl-csrf': self.csrf
        }
        url = 'https://spb.ticketland.ru/hallPlace/select/'
        response = session.post(url, headers=headers, data=data)

        if response.status_code != 200 or response.json()['result'] is not True:
            # with open('request_to_basket.json', 'w', encoding='utf-8') as file:
            #     json.dump(response.json(), file, indent=4, ensure_ascii=False)
            self.error(f'Запрос в корзину завершился не успешно {ticket.place_data}')
            return False
        elif len(list(response.json()['ticketHashList'].keys())) != count_tickets_in_basket + 1:
            self.warning(f'В корзине уже находились билеты')
            return response.json()['ticketHashList']
        return True

    def _requests_to_delete_ticket_in_basket(self, session: ProxySession, tickets_in_basket: dict[int, str]) -> bool:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': 'spb.ticketland.ru',
            'origin': 'https://spb.ticketland.ru',
            'pragma': 'no-cache',
            'referer': self.url,
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        url = 'https://spb.ticketland.ru/hallPlace/deselect/'
        for ticket_id in tickets_in_basket.keys():
            data = {'cypher': self.all_ticket_in_event[int(ticket_id)]}
            response = session.post(url, headers=headers, data=data)

            if response.status_code != 200:
                self.warning(f'Запрос на удаление билета из корзины вернул код ответа {response.status_code}')
        if response.json().get('ticketHashList') is None or len(response.json()['ticketHashList']) != 0:
            self.success(f'Запросы на удаление билетов из корзины не удалил все билеты')
            return False
        return True

    def _create_anonymous_order(self, session: ProxySession, user_data: UserData) -> json:
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': 'spb.ticketland.ru',
            'origin': 'https://spb.ticketland.ru',
            'pragma': 'no-cache',
            'referer': 'https://spb.ticketland.ru/shopcart/',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            'email': user_data.email,
            'name': user_data.first_name,
            'surname': user_data.last_name,
            'patronymic': '',
            'phone': '',
            'pushkinCardInfo': '',
            'pc': '',
            'payment': 'card',
            'token': '',
            'cookies': '',
        }
        url = 'https://spb.ticketland.ru/order/createAnonymousOrder/'
        response = session.post(url, headers=headers, data=data)

        if response.status_code != 200:
            self.error(f'Запрос на создание анонимного заказа завершился с кодом ответа {response.status_code}')
            return None
        try:
            json_data = response.json()
        except JSONDecodeError:
            with open('anonumous_order.html', 'w', encoding='utf-8') as file:
                file.write(response.text)
            self.error(f'Запрос на создание анонимного заказа вернулся с неожиданным json')
            return None
        if json_data['error'] != 0:
            with open('anonumous_order_error.json', 'w', encoding='utf-8') as file:
                json.dump(response.json(), file, indent=4, ensure_ascii=False)
            self.error(f'Запрос на создание анонимного заказа вернулся с ошибкой в теле ответа')
            return None
        return json_data

    def _create_paybox_card(self, session: ProxySession, json_data_anonymous_order: json) -> json:
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': 'spb.ticketland.ru',
            'origin': 'https://spb.ticketland.ru',
            'pragma': 'no-cache',
            'referer': 'https://spb.ticketland.ru/shopcart/',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            'sessOrderId': json_data_anonymous_order['params']['sessOrderId'],
            'paymentWay': json_data_anonymous_order['params']['paymentWay']
        }
        url_to_card = 'https://spb.ticketland.ru' + json_data_anonymous_order['url']
        response = session.post(url_to_card, headers=headers, json=data)

        if response.status_code != 200:
            self.error(f'Запрос на создание оплаты через карту завершился с кодом ответа {response.status_code}')
            return None
        try:
            return response.json()
        except JSONDecodeError:
            with open('create_paybox_card.html', 'w', encoding='utf-8') as file:
                file.write(response.text)
            self.error(f'Запрос на создание оплаты через карту вернулся с неожиданным json')
            return None

    def _create_paybox_sbp(self, session: ProxySession, json_data_anonymous_order: json) -> json:
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'host': 'spb.ticketland.ru',
            'origin': 'https://spb.ticketland.ru',
            'pragma': 'no-cache',
            'referer': 'https://spb.ticketland.ru/shopcart/',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-requested-with': 'XMLHttpRequest'
        }
        data = {
            'sessOrderId': json_data_anonymous_order['params']['sessOrderId'],
            'paymentWay': json_data_anonymous_order['params']['paymentWay']
        }
        url_to_sbp = 'https://spb.ticketland.ru' + json_data_anonymous_order['url']
        response = session.post(url_to_sbp, headers=headers, json=data)
        if response.status_code != 200:
            self.error(f'Запрос на создание QR кода завершился с кодом ответа {response.status_code}')
            return None
        json_data = response.json()
        if json_data['error'] is True:
            self.error(f'Запрос на создание QR кода вернулся с ошибкой в теле ответа')
            return None
        return json_data

    def _buy_tickets(self, ticket_to_new_threading_basket: list[TicketData], event_date: str,  session: ProxySession) -> None:
        ticket_in_basket = []
        for ticket in ticket_to_new_threading_basket:
            response_status_or_dict_tickets = self._requests_to_set_ticket_in_basket(
                session,
                ticket,
                len(ticket_in_basket)
            )
            if response_status_or_dict_tickets is True:
                ticket_in_basket.append(ticket)
            elif isinstance(response_status_or_dict_tickets, dict):
                self._requests_to_delete_ticket_in_basket(session, response_status_or_dict_tickets)

                ticket_in_basket = []
                for ticket in ticket_to_new_threading_basket:
                    if self._requests_to_set_ticket_in_basket(session, ticket, len(ticket_in_basket)):
                        ticket_in_basket.append(ticket)
                break

        user_data = next(self.generate_accounts)
        json_data_anonymous_order = self._create_anonymous_order(session, user_data)
        if json_data_anonymous_order is not None:
            # json_data_order = self._create_paybox_sbp(session, json_data_anonymous_order)
            json_data_order = self._create_paybox_card(session, json_data_anonymous_order)
            if json_data_order is not None:
                self._output_data(ticket_in_basket, json_data_order, event_date)

    def _set_tickets_in_basket(self, free_tickets: list[TicketData], event_date) -> None:
        if len(free_tickets) == 0:
            return
        this_index = 0
        while True:
            ticket_to_new_threading_basket = free_tickets[this_index:self.max_ticket_in_basket+this_index]
            self.threading_try(self._buy_tickets,
                               args=(ticket_to_new_threading_basket, event_date, self.session),
                               raise_exc=False,
                               tries=1)
            self.proxy = self.controller.proxy_hub.get(self.proxy_check)
            self.before_body()

            this_index += self.max_ticket_in_basket
            if len(free_tickets) <= this_index:
                break

    async def threading_body(self, url: str, event_date: str) -> None:
        soup = await self._check_self_url(url)
        free_tickets = await self._parse_free_tickets(soup, event_date)
        self._set_tickets_in_basket(free_tickets, event_date)

    async def body(self):
        self.threading_try(self._delete_tickets_in_skip_ticket_dict, raise_exc=False, tries=3)
        while True:
            await self._find_main_event()
            for url, event_date in self.urls:
                self.threading_try(await self.threading_body, args=(url, event_date), raise_exc=False, tries=1)
            await asyncio.sleep(60)

    def _output_data(self, ticket_in_basket: list[TicketData], json_data_order: json, event_date: str) -> None:
        datetime_now = datetime.now()
        message = self.event_name + ' ' + event_date + '\n'

        price = 0
        for ticket in ticket_in_basket:
            message += ticket.place_data + '\n'
            price += int(ticket.place_data.split()[-1])
            try:
                self.tickets_already_sent[event_date][ticket.place_data] = datetime.timestamp(datetime_now)
            except KeyError:
                self.tickets_already_sent[event_date] = {ticket.place_data: datetime.timestamp(datetime_now)}

        message += f'Общая цена <b>{price}</b>\n'
        # message = json_data_order['qrCode']['payload'] + '\n'
        message += json_data_order['url'] + '?mdOrder=' + json_data_order['get']['mdOrder'] + '\n'

        bot_to_send_message = next(self.generate_bots)
        for chat_id in self.all_chat_id:
            try:
                bot_to_send_message.send_message(chat_id, message, parse_mode='HTML')
            except ApiTelegramException:
                continue

    async def _delete_tickets_in_skip_ticket_dict(self) -> None:
        while True:
            if len(self.tickets_already_sent) > 0:
                ticket_to_del = []
                datetime_timestamp_now = datetime.timestamp(datetime.now())
                for ticket_data_in_event_date in self.tickets_already_sent.values():
                    for ticket_data, ticket_timestamp in ticket_data_in_event_date.items():
                        if (datetime_timestamp_now - ticket_timestamp) > 15 * 60:
                            ticket_to_del.append(ticket_data)
                    for ticket_data in ticket_to_del:
                        del self.tickets_already_sent[ticket_data_in_event_date][ticket_data]
            await asyncio.sleep(60)
