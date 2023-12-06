import json
import datetime
import time

from requests.exceptions import ProxyError
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils.date import month_list
from parse_module.utils.parse_utils import double_split
from parse_module.utils.captcha import image
from parse_module.drivers.proxelenium import ProxyWebDriver


class YandexAfishaParser(EventParser):
    proxy_check_url = 'https://afisha.yandex.ru/'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 7200
        self.driver_source = None
        self.our_urls = {
            'https://afisha.yandex.ru/moscow/concert/places/vk-stadium': '*',                    # Вк Арена
            'https://afisha.yandex.ru/moscow/concert/places/tsska-arena': '*',                   # ЦСКА Арена
            'https://afisha.yandex.ru/ufa/sport/places/ufa-arena': '*',                          # Уфа Арена
            'https://afisha.yandex.ru/vladivostok/concert/places/fetisov-arena': '*',            # Фетисов Арена
            'https://afisha.yandex.ru/khabarovsk/other/places/platinum-arena': '*',              # Платинум Арена
            'https://afisha.yandex.ru/saint-petersburg/concert/places/iubileinyi-spb': '*',      # Юбилейный
            'https://afisha.yandex.ru/moscow/concert/places/vtb-arena': '*',                     # ВТБ Арена
            'https://afisha.yandex.ru/moscow/other/places/megasport': '*',                       # Мегаспорт
            'https://afisha.yandex.ru/novosibirsk/other/places/ledovyi-dvorets-sibir': '*',      # ЛД Сибирь
            'https://afisha.yandex.ru/omsk/other/places/g-drive-arena': '*',                     # G-Drive Арена
            'https://afisha.yandex.ru/kazan/concert/places/tatneft-arena': '*',                  # Татнефть Арена
            'https://afisha.yandex.ru/moscow/concert/places/crocus-city-hall': '*',              # Крокус
            'https://afisha.yandex.ru/moscow/concert/places/vegas-city-hall-msk': '*',           # Vegas City Hall
            'https://afisha.yandex.ru/moscow/concert/places/backstage': '*',                     # Ресторан Backstage
            'https://afisha.yandex.ru/moscow/sport/places/bolshaia-sportivnaia-arena-luzhniki': '*',  # Лужники
            'https://afisha.yandex.ru/moscow/sport/places/dvorets-gimnastiki-iriny-viner-usmanovoi': '*',  # Лужники Дворец гимнастики Ирины Винер-Усмановой
            'https://afisha.yandex.ru/saint-petersburg/concert/places/bkz-oktiabrskii': '*',  # БКЗ «Октябрьский»
            'https://afisha.yandex.ru/moscow/concert/places/kremlevskii-dvorets': '*',  # Кремльвский дворец
            'https://afisha.yandex.ru/moscow/concert/places/mts-live-holl': '*',  # MTC Live Холл
            'https://afisha.yandex.ru/moscow/theatre/places/sovremennik': '*',  # Театр Современник
            'https://afisha.yandex.ru/moscow/concert/places/zelionyi-teatr-vdnkh/schedule': '*',  # Зелёный театр ВДНХ
            'https://afisha.yandex.ru/moscow/concert/places/zelionyi-teatr': '*',  # Зелёный театр
            # 'https://afisha.yandex.ru/organizer/teatr-baleta-borisa-eifmana?city=saint-petersburg': '*'  # Балет Ейфмана
            'https://afisha.yandex.ru/moscow/concert/places/kontsertnyi-zal-gostinitsy-kosmos': '*',  # Концертный зал гостиницы «Космос»
            'https://afisha.yandex.ru/saint-petersburg/sport/places/gazprom-arena': '*',  # Газпром Арена
            'https://afisha.yandex.ru/moscow/concert/places/dom-muzyki': '*',  # Дом музыки
            'https://afisha.yandex.ru/saint-petersburg/theatre/places/mikhailovskii-teatr': '*',  # Михайловский питер
            'https://afisha.yandex.ru/moscow/concert/places/shore-house': '*',  # Shore House
        }
        self.special_url = {
            # 'https://afisha.yandex.ru/moscow/selections/standup': '*',  # Стендап
        }
        self.csrf = ''
        self.our_places_short = []
        self.place = {}

    def before_body(self):
        self.session = ProxySession(self)
        self.our_places_short = []

    def get_dict_from_body(self, body, keyword):
        if keyword not in body:
            raise RuntimeError(f'[req_err] request doesnt contain needed keyword: {body[:1000]} {self.proxy.__str__() = }')

        body = body.replace('undefined', 'null')
        data_str = double_split(body, keyword, "};") + '}'
        data_dict = json.loads(data_str)

        return data_dict

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

    def main_page_request(self):
        url = 'https://afisha.yandex.ru/'

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
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
        r = self.check_captcha(r, url, headers)

    def get_places(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, utf-8',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        r = self.check_captcha(r, self.url, headers)

        window_data = self.get_dict_from_body(r.text, "window['__initialState'] = ")
        api_data = self.get_dict_from_body(r.text, "window['__apiParams'] = ")
        self.csrf = api_data['csrf']

        places = {}
        for place in window_data['places'].values():
            place_f = {
                'title': place['title'],
                'id': place['id'],
                'url': 'https://afisha.yandex.ru' + place['url'],
                'short_url': place['url'],
                'city_id': place['city']['id'],
            }
            places[place['title']] = place_f

        return places

    def place_request(self, place_url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
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
        r = self.session.get(place_url, headers=headers)
        r = self.check_captcha(r, place_url, headers)

        window_data = self.get_dict_from_body(r.text, "window['__initialState'] = ")
        api_data = self.get_dict_from_body(r.text, "window['__apiParams'] = ")

        place_info = list(window_data['place'].values())[0]
        self.place = {
            'title': place_info['title'],
            'id': place_info['id'],
            'url': 'https://afisha.yandex.ru' + place_info['url'],
            'short_url': place_info['url'],
            'city_id': place_info['city']['id'],
        }

        # TODO Иногда просто не понятно каким образом client_key не тот что на сайте, а какой-то другой
        client_key = self.get_client_key(r.text)

        request_id = api_data['requestId']
        dates = self.get_dates(r.text)

        return client_key, request_id, dates

    def get_dates(self, body):
        soup = BeautifulSoup(body, 'lxml')
        dates = {}

        if '"month-picker":' in body:
            month_picker = double_split(body, '"month-picker":', '},"') + '}'
            month_picker = json.loads(month_picker)

            for date_info in month_picker['groups']:
                dates[date_info['date']] = date_info['period']
        else:
            stage_list = soup.find('div', class_='schedule-stage-list')

            if not stage_list:
                return dates

            state = '{' + double_split(str(stage_list), '"state":{', "}") + '}'
            state = json.loads(state)
            dates[state['date']] = state['period']

        return dates

    def get_client_key(self, body):
        page_data_params = '{"b-page"' + double_split(body, 'data-bem=\'{"b-page"', "'")
        page_data_params = json.loads(page_data_params)

        client_key = page_data_params['i-ticket-dealer']['key']

        return client_key

    def schedule_events_request(self, request_id, date, period):
        # https://afisha.yandex.ru/api/places/561f5a0137753641a354609b/schedule_other?date=2023-01-02&period=30&city=moscow&_=1670503199058
        # БЕЗ ПОСЛЕДНЕГО ПАРАМЕТРА РАБОТАЕТ
        # Это какой-то непонятный счетчик запросов. Увеличивается на единицу после каждого запроса

        url = f'https://afisha.yandex.ru/api/places/{self.place["id"]}/schedule_other?date={date}&period={period}&city={self.place["city_id"]}'
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
            'referer': self.place['url'],
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest',
            'X-Parent-Request-Id': str(request_id),
            'X-Retpath-Y': self.place['url'],
            'user-agent': self.user_agent,
        }
        r = self.session.get(url, headers=headers)
        r = self.check_captcha(r, url, headers)

        if 'schedule' not in r.text or 'items' not in r.text:
            raise RuntimeError(f'[req_err] schedule_events_request doesnt contain needed parameters: {r.text[:400]}')

        return r.json()['schedule']['items']

    def get_place_events(self, date_items, client_key):
        a_events = []
        for date_item in date_items:
            for event_info in date_item['sessions']:
                if not event_info['session']['ticket']:
                    continue
                if event_info['session']['ticket']['saleStatus'] != 'available':
                    continue

                title = event_info['event']['title']

                year, month, day = event_info['session']['date'].split('-')
                month = month_list[int(month)]
                time = event_info['session']['datetime'].split('T')[-1]
                time = ':'.join(time.split(':')[:-1])
                date = f'{day} {month} {year} {time}'

                scene = event_info['session']['hall']

                # TODO Спросить оставлять ли эти параметры - &fullscreen=true&lang=ru (Все и без них работает)
                # TODO Спросить че делать с ga_cookie
                # TODO %3D%3D иногда так, иногда ==   Понять какую ссылку проставлять (вроде = надо)
                # href - https://widget.afisha.yandex.ru/w/sessions/MTI5OXwzODU2NnwxNjEwNzd8MTY3MDg2MDgwMDAwMA%3D%3D?widgetName=w2&gaCookie=GA1.2.1365591005.1665960316&clientKey=bb40c7f4-11ee-4f00-9804-18ee56565c87&fullscreen=true&lang=ru
                # href - https://widget.afisha.yandex.ru/w/sessions/NjI3fDMyNTgxOXwxNDMyNjg2fDE2NzIzMjk2MDAwMDA%3D?widgetName=w2&gaCookie=GA1.2.1365591005.1665960316&clientKey=bb40c7f4-11ee-4f00-9804-18ee56565c87&lang=ru
                session_id = event_info['session']['ticket']['id'].replace('=', '%3D')
                widget_name = 'w2'  # Непонятно откуда брать, ссылка рабочая при любом значении этого параметра

                # href = f'https://widget.afisha.yandex.ru/w/sessions/{session_id}?widgetName={widget_name}&clientKey={client_key}&lang=ru'
                href = f'https://widget.afisha.yandex.ru/w/sessions/{session_id}?widgetName={widget_name}&lang=ru'

                event_params = {
                    'client_key': client_key,
                    'session_id': session_id,
                }

                a_events.append([title, href, date, scene, event_params])

        return a_events

    def check_captcha(self, r, old_url, old_headers):
        if '<div class="CheckboxCaptcha" ' not in r.text:
            return r
        return self.handle_smart_captcha(r.url, old_url, old_headers)

    def handle_smart_captcha(self, url, old_url, old_headers):
        r = self.selenium_smart_captha(url)
        # r = self.session.get(old_url, headers=old_headers)
        return r

    def selenium_smart_captha(self, url: str):
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument('--headless=new')
        driver = ProxyWebDriver(proxy=self.proxy, chrome_options=chrome_options)

        try:
            driver.get(url=url)
            time.sleep(1)
            r = self.solve_smart_captcha_checkbox(driver)
            driver.get(url=r.url)
            r = self.solve_smart_captcha_image(driver)
        except TimeoutException as e:
            self.bprint('Яндекс капча не пройдена: что-то не работает')
            raise ProxyError(e)
        finally:
            driver.quit()
        return r

    def solve_smart_captcha_checkbox(self, driver):
        body = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        ).get_attribute('innerHTML')

        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        aes_key = driver.find_element(By.CSS_SELECTOR, 'input[name=aesKey]').get_attribute('value')
        sign_key = driver.find_element(By.CSS_SELECTOR, 'input[name=signKey]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')

        data = {
            'rdata': r_data,
            'aesKey': aes_key,
            'signKey': sign_key,
            'pdata': pdata
        }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'content-length': '5650',
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'afisha.yandex.ru',
            'origin': 'https://afisha.yandex.ru',
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
        url = f'https://afisha.yandex.ru{href}'
        r = self.session.post(url, timeout=10, headers=headers, data=data)
        return r

    def solve_smart_captcha_image(self, driver):
        img_captha = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.AdvancedCaptcha-View img"))
        )
        img_captha_href = img_captha.get_attribute('src')

        r = self.session.get(img_captha_href, stream=True)
        if r.status_code == 200:
            with open('afisha_catcha.png', 'wb') as f:
                for chunk in r:
                    f.write(chunk)

        with open('afisha_catcha.png', 'rb') as img:
            word_from_img = image(file=img)

        body = driver.find_element(By.CSS_SELECTOR, 'body').get_attribute('innerHTML')
        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        aes_key = driver.find_element(By.CSS_SELECTOR, 'input[name=aesKey]').get_attribute('value')
        sign_key = driver.find_element(By.CSS_SELECTOR, 'input[name=signKey]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')

        data = {
            'rep': word_from_img,
            'rdata': r_data,
            'aesKey': aes_key,
            'signKey': sign_key,
            'pdata': pdata
        }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'content-length': '5650',
            'content-type': 'application/x-www-form-urlencoded',
            'host': 'afisha.yandex.ru',
            'origin': 'https://afisha.yandex.ru',
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
        url = f'https://afisha.yandex.ru{href}&rep={word_from_img}'
        r = self.session.post(url, timeout=10, headers=headers, data=data)
        return r

    def _get_total_events(self, url: str) -> tuple[int, str, str]:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
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
        r = self.session.get(url, headers=headers)
        r = self.check_captcha(r, url, headers)

        client_key = self.get_client_key(r.text)
        request_id = double_split(r.text, '"request-id":"', '"')
        total = int(double_split(r.text, '"total":', '}'))
        return total, request_id, client_key

    def _get_card_with_event(self, total_events: int, request_id: str, client_key: str, url: str) -> list:
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest',
            'X-Parent-Request-Id': request_id,
            'X-Retpath-Y': url,
            'user-agent': self.user_agent
        }
        offset = 0
        limit = 12
        final_event = []
        while total_events != offset:
            url = f'https://afisha.yandex.ru/api/events/selection/standup?limit={limit}&offset={offset}&hasMixed=0&city=moscow'
            r = self.session.get(url, headers=headers)
            r = self.check_captcha(r, url, headers)

            card_event_from_request = r.json()['data']
            for card in card_event_from_request:
                card = card['event']
                title = card['title']
                href_to_all_date = card['url']
                href_to_all_date = 'https://afisha.yandex.ru' + href_to_all_date
                try:
                    dates_and_venues_and_hrefs = self._get_all_date_and_venue(href_to_all_date, client_key)
                except AttributeError:
                    continue
                for data in dates_and_venues_and_hrefs:
                    normal_date, venue, href, event_params = data
                    final_event.append((title, href, normal_date, '', event_params, venue))

            offset += limit
            if (total_events - offset) < 12:
                limit = total_events - offset
            if offset == total_events:
                break
        return final_event

    def _get_event_data_from_soup(self, event: Tag, client_key: str) -> tuple[str, str, str, dict[str, str]]:
        json_data = event.get('data-bem')
        json_data = json.loads(json_data)
        venue = json_data['widget-date-filter__item']['place']['title']

        date = event.find('span', class_='session-date__day').text.split()
        date[1] = date[1][:3].title()
        time = event.find('span', class_='session-date__time').text
        normal_date = ' '.join(date) + ' ' + time

        session_id = event.find('input').get('value')
        href = 'https://widget.afisha.yandex.ru/w/sessions/' + session_id + '?widgetName=w2&lang=ru'

        event_params = {'client_key': client_key, 'session_id': session_id}
        return normal_date, venue, href, event_params

    def _get_event_data_from_page_with_many_month(
            self, event: Tag, event_id: str, request_id: str, client_key: str, href_to_all_date: str
    ) -> list[tuple[str, str, str, dict[str, str]]]:
        all_event_data = []

        json_data_in_text = json.loads(event.get('data-bem'))
        month_groups = json_data_in_text['month-picker']['groups']
        for group in month_groups:
            date = group['date']
            period = group['period']
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru,en;q=0.9',
                'cache-control': 'no-cache',
                'connection': 'keep-alive',
                'host': 'afisha.yandex.ru',
                'pragma': 'no-cache',
                'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'x-requested-with': 'XMLHttpRequest',
                'X-Parent-Request-Id': request_id,
                'X-Retpath-Y': href_to_all_date,
                'user-agent': self.user_agent
            }
            url = f'https://afisha.yandex.ru/api/events/{event_id}/schedule_other?date={date}&period={period}&city=moscow'
            r = self.session.get(url, headers=headers)
            r = self.check_captcha(r, url, headers)

            json_data = r.json()
            items = json_data['items']
            for item in items:
                times_and_venues = item['sessions']
                for time_and_venue in times_and_venues:
                    venue = time_and_venue['place']['title']

                    date = time_and_venue['session']['datetime']
                    date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
                    normal_date = f'{date.day} {month_list[int(date.month)]} {date.year} {date.hour}:{date.minute}'

                    session_id = time_and_venue['session']['ticket']
                    if session_id is None:
                        continue
                    session_id = session_id['id']
                    href = 'https://widget.afisha.yandex.ru/w/sessions/' + session_id + '?widgetName=w2&lang=ru'

                    event_params = {'client_key': client_key, 'session_id': session_id}

                    all_event_data.append((normal_date, venue, href, event_params))
        return all_event_data

    def _get_all_date_and_venue(self, href_to_all_date: str, client_key: str) -> list[tuple]:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
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
        r = self.session.get(href_to_all_date, headers=headers)
        r = self.check_captcha(r, href_to_all_date, headers)

        dates_and_venues_and_hrefs = []
        soup = BeautifulSoup(r.text, 'lxml')
        all_events_first = soup.select('label.radio-button__radio.widget-date-filter__item')
        for event in all_events_first:
            if 'widget-date-filter__item_disabled_yes' in event.attrs.get('class'):
                continue
            data = self._get_event_data_from_soup(event, client_key)
            dates_and_venues_and_hrefs.append(data)

        all_events_second = soup.select('ul.tabs-menu.tabs-menu_size_m.tabs-menu_theme_normal')
        if len(all_events_second) > 0:
            event_id = double_split(r.text, '"event_id":"', '"')
            request_id = double_split(r.text, '"request-id":"', '"')
            data = self._get_event_data_from_page_with_many_month(
                all_events_second[0], event_id, request_id, client_key, href_to_all_date
            )
            dates_and_venues_and_hrefs.extend(data)

        if len(all_events_first) == 0 and len(all_events_second) == 0:
            venue = soup.find('span', class_='event-concert-description__place-name').text

            date = soup.find('span', class_='session-date__day').text.replace(',', '').split()
            date[1] = date[1][:3].title()
            time = soup.find('span', class_='session-date__time').text
            normal_date = ' '.join(date) + ' ' + time

            session_id = double_split(r.text, '"hasTicketsWidget":"', '"')
            href = 'https://widget.afisha.yandex.ru/w/sessions/' + session_id + '?widgetName=w2&lang=ru'

            event_params = {'client_key': client_key, 'session_id': session_id}

            dates_and_venues_and_hrefs.append((normal_date, venue, href, event_params))

        return dates_and_venues_and_hrefs

    def body(self):
        # places = self.get_places()
        for url in self.our_urls:
            client_key, request_id, dates = self.place_request(url)
            venue = self.place['title']

            # date - 2023-01-02; period - 30
            for date, period in dates.items():
                date_items = self.schedule_events_request(request_id, date, period)
                a_events = self.get_place_events(date_items, client_key)
                for event in a_events:
                    event_params = str(event[4]).replace("'", "\"")
                    self.register_event(event[0], event[1], date=event[2], scene=event[3],
                                        event_params=event_params, venue=venue)
        for url in self.special_url:
            total_events, request_id, client_key = self._get_total_events(url)
            final_event = self._get_card_with_event(total_events, request_id, client_key, url)
            for event in final_event:
                event_params = str(event[4]).replace("'", "\"")
                self.register_event(event[0], event[1], date=event[2], scene=event[3],
                                    event_params=event_params, venue=event[5])
