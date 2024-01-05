from typing import NamedTuple, Optional, Union
import re
from datetime import datetime
import locale

from bs4 import BeautifulSoup, ResultSet, Tag


from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from parse_module.coroutines import AsyncEventParser
from parse_module.drivers.proxelenium import ProxyWebDriver
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils import utils


class OutputEvent(NamedTuple):
    title: str
    href: str
    date: str


class CircusSpbRu(EventParser):
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 7600
        self.driver_source = None
        self.urls = {
            #'https://www.circus.spb.ru/': 'Страшная сила',
            'https://www.circus.spb.ru/novogodnee-predstavlenie.html': 'МАСКА',
            #'https://circus.spb.ru/balagan.html': 'Балаган',
            #'https://bezgranits.circus.team/': 'Фестиваль циркового искусства «Без границ»',
            #'https://circus.spb.ru/bolshaja-otkrytaja-repetitsija-legendarnyh-bratev-zapashnyh-v-tsirke-na-fontanke-.html': 'БОЛЬШАЯ ОТКРЫТАЯ РЕПЕТИЦИЯ БРАТЬЕВ ЗАПАШНЫХ',
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

    def before_body(self):
        self.session = ProxySession(self)

    @staticmethod
    def make_date(date):
        day, month = date.split()
        res = ' '.join([day, month[:3].capitalize()])
        return res

    def _parse_events(self, self_url: str, title: str) -> OutputEvent:
        if 'Без границ' in title:
            soup = self._requests_to_events(self_url)
            events = self._get_events_bez_granic(soup)
            a_events = self._parse_events_bez_granic(events, title)

        elif 'Балаган' in title:
            events = self._get_events_balagan_requests()
            ids = [i.find('a', attrs={'data-tp-event': re.compile(r'\d+')}) for i in events]
            ids = [i.get('data-tp-event') for i in ids]
            a_events = self.load_events(ids)
            #events = self._get_events_balagan_selenium(self_url)
            #a_events = self._parse_events_balagan(events)

        elif 'МАСКА' in title:
            all_events = self._get_events_maska()
            ids = [i.find('a', attrs={'data-tp-event': re.compile(r'\d+')}) for i in all_events]
            ids = [i.get('data-tp-event') for i in ids]
            a_events = self.load_events(ids)

        else:
            soup = self._requests_to_events(self_url)
            events = self._get_events_from_soup(soup)
            a_events = self._parse_events_from_soup(events, title)

        return a_events
    
    def load_events(self, ids):
        a_events = set()
        id_1, id_2 = ids[0], ids[-1]
        for id in (id_1, id_2):
            url = f'https://ticket-place.ru/widget/{id}/similar'
            all_events_json = self.session.get(url, headers=self.headers)
        
            for i in all_events_json.json().get("events"):
                title = i.get("name")
                id_new = i.get("id")
                href = f'https://ticket-place.ru/widget/{id_new}/data|spb'
                date = self.reformat_date(i.get("datetime"))
                a_events.add(OutputEvent(title=title, href=href, 
                                                date=date))

        return list(a_events)
    
    @staticmethod
    def reformat_date(date):
        date = datetime.fromisoformat(date)
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        date_to_write = f'{date.strftime("%d")} {date.strftime("%b").capitalize()}' \
                             f' {date.strftime("%Y")} {date.strftime("%H:%M")}'
        return date_to_write
    

    def _get_events_maska(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://circus.spb.ru/',
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
        for i in range(1,4):
            url = f'https://ticket-place.ru/calendar-widget/31?showId=152&dateFrom=&dateTo=&page={i}&maxDays=4'
            r = self.session.get(url, headers=headers)
            if r.ok:
                soup = BeautifulSoup(r.text, 'lxml')
                events_all = soup.find_all(class_=re.compile(r'calendar__item'))
                if len(events_all) > 0:
                    all_events.extend(events_all)
                    return all_events
            else:
                break
        return all_events
    
    def _parse_events_balagan(self, events_all):
        a_events = []
        title = 'Балаган'
        for event in events_all:
            day = event.find(class_=re.compile(r'day')).text.strip()
            month = event.find(class_=re.compile(r'mounth')).text.strip()[:3].capitalize()
            times = event.find_all('a')
            for i in times:
                if 'Купить' not in i.text:
                    continue
                id = i.get('data-tp-event')
                time = i.text.split('—')[0].strip()
                full_date = f"{day} {month} {time}"
                url = f"https://ticket-place.ru/widget/{id}/data|spb"
                a_events.append(OutputEvent(title=title, href=url, date=full_date))
        return a_events
    
    
    def _parse_events_bez_granic(self, events_all, title):
        a_events = []
        title = 'Фестиваль циркового искусства «Без границ»'
        for event in events_all:
            date = event.find('h2').text
            date = self.make_date(date)
            times = [ i.text for i in event.find_all(class_='text-block-11')]
            ids = [ i.find('a').get('data-tp-event') for i in event.find_all(class_='ticket-btn-wrp')]

            for time, id in zip(times, ids):
                full_date = f"{date} {time}"
                url = f"https://ticket-place.ru/widget/{id}/data|spb"
                a_events.append(OutputEvent(title=title, href=url, date=full_date))

        return a_events

    def _parse_events_from_soup(self, events: ResultSet[Tag], title: str) -> OutputEvent:
        for event in events:
            output_data = self._parse_data_from_event(event, title)
            for data in output_data:
                if data is not None:
                    yield data

    def _parse_data_from_event(self, event: Tag, title: str) -> Optional[Union[list[OutputEvent], None]]:
        output_list = []

        try:
            day = event.find('p', class_='day').text.strip()
        except AttributeError:
            return output_list
        month = event.find('p', class_='month').text.strip()[:3].title()

        all_time_in_day = event.find_all('a')
        for time_in_day in all_time_in_day:
            try:
                time = time_in_day.find('p').text
            except AttributeError:
                time = time_in_day.text
            time = time.replace('Купить на ', '')
            if len(time) < 5:
                continue

            normal_date = f'{day} {month} {time}'

            id_event = time_in_day.get('data-tp-event')
            href = f'https://ticket-place.ru/widget/{id_event}/data' + '|spb'
            output_list.append(OutputEvent(title=title, href=href, date=normal_date))
        return output_list

    def _get_events_from_soup(self, soup: BeautifulSoup) -> ResultSet[Tag]:
        events = soup.select('div.ticket_item')
        return events
    
    def _get_events_bez_granic(self, soup):
        events = soup.select_one('#ticket .program-wrp')
        events_all = events.find_all('div', id=re.compile(r'w-node'))
        return events_all
    
    def _get_events_balagan_requests(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'referer': 'https://circus.spb.ru/',
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
        for i in range(1,5):
            url = f'https://ticket-place.ru/calendar-widget/31?showId=107&dateFrom=&dateTo=&page={1}&maxDays=4'
            r = self.session.get(url, headers=headers)
            if r.ok:
                soup = BeautifulSoup(r.text, 'lxml')
                events_all = soup.find_all(class_=re.compile(r'calendar__item'))
                if len(events_all) == 0:
                    break
                all_events.extend(events_all)
            else:
                break
        return all_events

    def _get_events_balagan_selenium(self, self_url):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        with ProxyWebDriver(options=chrome_options) as driver:
            driver.get(self_url)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".tp-calendar__item")))
            html = driver.page_source

            soup = BeautifulSoup(html, 'lxml')
            button_load_more = soup.find('button', class_="tp-calendar__more")
            if button_load_more:
                data_count = button_load_more.get('data-count', 0)
                for i in range(int(data_count)+1):
                    wait = WebDriverWait(driver,5)
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.tp-calendar__more')))
                        btn = driver.find_element(By.CSS_SELECTOR, '.tp-calendar__more')
                        btn.click()
                    except TimeoutException as ex:
                        break
                html = driver.page_source 
                soup = BeautifulSoup(html, 'lxml')          

            events = soup.find('div', class_='tp-calendar-container')
            events_all = events.find_all(class_=re.compile(r'item'))
        return events_all

    def _requests_to_events(self, url: str) -> BeautifulSoup:
        url_strip = re.search(r'(?<=://).+(?=/)', url)[0]
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': url_strip,
            'pragma': 'no-cache',
            'referer': 'https://yandex.ru/',
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
        r = self.session.get(url, headers=headers)
        r.encoding = 'utf-8'
        return BeautifulSoup(r.text, 'lxml')

    def body(self) -> None:
        for self_url, title in self.urls.items():
            try:
                for event in self._parse_events(self_url, title):
                    self.register_event(event.title, event.href, 
                                        date=event.date, venue='Цирк на Фонтанке (СПБ)')
            except Exception as ex:
                self.error(f'{self_url} {title} {ex}' f'cannot load! maybe it dont have event?')
                raise
