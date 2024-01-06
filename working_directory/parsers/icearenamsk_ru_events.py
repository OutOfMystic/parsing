
from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession

from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup

class IceArenaMsk(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        
        self.delay = 3600
        self.headers = {
            'authority': 'icearenamsk.ru',
            'accept': '*/*',
            'accept-language': 'ru,en;q=0.9',
            # 'cookie': '_ym_uid=1702465901593502570; _ym_d=1702465901; tmr_lvid=c9210f722195e5d861d65d4f6c987c5c; tmr_lvidTS=1702465931046; BX_USER_ID=0b32a62d4f9e49d68b5f75e421c74a0a; _ym_isad=1; _ym_visorc=w; tmr_detect=1%7C1702570139375; BITRIX_BQ_COLOSSEO_BASKET_LAST_ACTION=1702570139; PHPSESSID=411ahuHNvgFiryL8NgCOct19MysrtC1l',
            'referer': 'https://icearenamsk.ru/afisha-and-tickets/afisha/',
            'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.1077 YaBrowser/23.9.1.1077 Yowser/2.5 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
    
    async def before_body(self):
        self.session = AsyncProxySession(self)
        
    def _parse_date_string(self, date):
        # Словарь с соответствием русских месяцев числовым значениям
        months = {
            'января': 1,
            'февраля': 2,
            'марта': 3,
            'апреля': 4,
            'мая': 5,
            'июня': 6,
            'июля': 7,
            'августа': 8,
            'сентября': 9,
            'октября': 10,
            'ноября': 11,
            'декабря': 12
        }

        parts = date.split()

        day = int(parts[0])
        month = months[parts[1]]
        hour, minute = map(int, parts[2].split(':'))

        current_year = datetime.now().year
        result_date = datetime(current_year, month, day, hour, minute)

        return result_date
    
    def _parse_events(self, soup : BeautifulSoup) -> Optional[list]:
        a_events = []
        
        links = soup.find_all('a')
        if len(links) == 0:
            return # Выходим из работы программы

        for link in links:
            href = "https://icearenamsk.ru/" + link['href']
            title: str = link.find('div', class_='r-afisha__card-title').text
            title = title.replace("'", '"')
            venue = link.find('div', class_='r-afisha__card-venue').text
            date = link.find('span', class_='r-afisha__card-date').text
            time = link.find('span', class_='r-afisha__card-time').text
            
            date_time = date + " " + time
            datetime_date = self._parse_date_string(date_time)
            a_events.append((title, href, datetime_date, venue))
        
        return a_events
            
    async def _get_events(self) -> list:
        a_events = []
        
        for offset in range(0, 100, 9):
            params = {
                '': 'undefined',
                'pagination_ajax': 'y',
                'offset': str(offset),
            }
            
            r_text = await self.session.get_text('https://icearenamsk.ru/afisha-and-tickets/afisha/', params=params, headers=self.headers)
            
            soup = BeautifulSoup(r_text, 'lxml')
            
            parsed_events : Optional[list] | None = self._parse_events(soup)
            
            if parsed_events is not None:
                a_events += parsed_events
            
        return a_events
    
    
    async def body(self):
        
        a_events = await self._get_events()
            
        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue=event[3])