import json
import datetime
import time
import base64

from requests.exceptions import ProxyError
from bs4 import BeautifulSoup, Tag
from selenium.webdriver import ChromeOptions
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image, ImageOps


from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import ProxySession
from parse_module.utils.date import month_list
from parse_module.utils.parse_utils import double_split
from parse_module.utils.captcha import yandex_afisha_coordinates_captha
from parse_module.drivers.proxelenium import ProxyWebDriver


class YandexAfishaParser(EventParser):
    proxy_check_url = 'https://afisha.yandex.ru/'

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 7200
        self.driver_source = None
        self.our_urls = {
           #'https://afisha.yandex.ru/moscow/concert/places/vk-stadium': '*',                    # Вк Арена
            'https://afisha.yandex.ru/moscow/concert/places/tsska-arena': '*',                   # ЦСКА Арена
           #'https://afisha.yandex.ru/ufa/sport/places/ufa-arena': '*',                          # Уфа Арена
           # 'https://afisha.yandex.ru/vladivostok/concert/places/fetisov-arena': '*',            # Фетисов Арена
           #'https://afisha.yandex.ru/khabarovsk/other/places/platinum-arena': '*',              # Платинум Арена
            'https://afisha.yandex.ru/saint-petersburg/concert/places/iubileinyi-spb': '*',      # Юбилейный
            'https://afisha.yandex.ru/moscow/concert/places/vtb-arena': '*',                     # ВТБ Арена
            'https://afisha.yandex.ru/moscow/other/places/megasport': '*',                       # Мегаспорт
           #'https://afisha.yandex.ru/novosibirsk/other/places/ledovyi-dvorets-sibir': '*',      # ЛД Сибирь
            'https://afisha.yandex.ru/omsk/other/places/g-drive-arena': '*',                     # G-Drive Арена
            'https://afisha.yandex.ru/kazan/concert/places/tatneft-arena': '*',                  # Татнефть Арена
            'https://afisha.yandex.ru/moscow/concert/places/crocus-city-hall': '*',              # Крокус
            'https://afisha.yandex.ru/moscow/concert/places/vegas-city-hall-msk': '*',           # Vegas City Hall
            'https://afisha.yandex.ru/moscow/concert/places/backstage': '*',                     # Ресторан Backstage
            #'https://afisha.yandex.ru/moscow/sport/places/bolshaia-sportivnaia-arena-luzhniki': '*',  # Лужники
           # 'https://afisha.yandex.ru/moscow/sport/places/dvorets-gimnastiki-iriny-viner-usmanovoi': '*',  # Лужники Дворец гимнастики Ирины Винер-Усмановой
            'https://afisha.yandex.ru/saint-petersburg/concert/places/bkz-oktiabrskii': '*',  # БКЗ «Октябрьский»
           # 'https://afisha.yandex.ru/moscow/concert/places/kremlevskii-dvorets': '*',  # Кремльвский дворец
           # 'https://afisha.yandex.ru/moscow/concert/places/mts-live-holl': '*',  # MTC Live Холл
            'https://afisha.yandex.ru/moscow/theatre/places/sovremennik': '*',  # Театр Современник
           # 'https://afisha.yandex.ru/moscow/concert/places/zelionyi-teatr-vdnkh': '*',  # Зелёный театр ВДНХ
           # 'https://afisha.yandex.ru/moscow/concert/places/zelionyi-teatr': '*',  # Зелёный театр
           #'https://afisha.yandex.ru/organizer/teatr-baleta-borisa-eifmana?city=saint-petersburg': '*'  # Балет Ейфмана
           # 'https://afisha.yandex.ru/moscow/concert/places/kontsertnyi-zal-gostinitsy-kosmos': '*',  # Концертный зал гостиницы «Космос»
           # 'https://afisha.yandex.ru/saint-petersburg/sport/places/gazprom-arena': '*',  # Газпром Арена
           # 'https://afisha.yandex.ru/moscow/concert/places/dom-muzyki': '*',  # Дом музыки
            'https://afisha.yandex.ru/saint-petersburg/theatre/places/mikhailovskii-teatr': '*',  # Михайловский питер
           # 'https://afisha.yandex.ru/moscow/concert/places/shore-house': '*',  # Shore House
            'https://afisha.yandex.ru/moscow/theatre/places/teatr-satiry': '*',  # Театр сатиры
           #'https://afisha.yandex.ru/moscow/theatre/places/teatr-rossiiskoi-armii': '*',  # Театр армии
            'https://afisha.yandex.ru/moscow/theatre/places/gelikon-opera': '*',  # Геликон-опера
            'https://afisha.yandex.ru/sochi/theatre/places/zimnii-teatr': '*',  # Зимний театр
            'https://afisha.yandex.ru/kazan/circus_show/places/tsirk-kazan': '*',  # Казанский цирк
            'https://afisha.yandex.ru/moscow/theatre/places/planeta-kvn': '*',  # Планета КВН
            'https://afisha.yandex.ru/moscow/concert/places/barvikha-luxury-village': '*',  # Барвиха Luxury Village
            #'https://afisha.yandex.ru/sochi/concert/places/sochi-park-arena': '*',  # Сочи Парк Арена
            'https://afisha.yandex.ru/sochi/sport/places/lds-aisberg': '*',  # ЛДС «Айсберг»
            'https://afisha.yandex.ru/simferopol/circus_show/places/tsirk-im-tezikova': '*', # Симферопольский Цирк
            #'https://afisha.yandex.ru/moscow/theatre/places/mdm-msk': '*', # МДМ
            #'https://afisha.yandex.ru/moscow/circus_show/places/tsirk-nikulina-na-tsvetnom-bulvare': '*', #цирк никулина
            'https://afisha.yandex.ru/saint-petersburg/concert/places/ledovyi-dvorets': '*', #Ледовый дворец СКА
            #'https://afisha.yandex.ru/moscow/theatre/places/teatr-im-ermolovoi': '*', #ermolova theatre
            #'https://afisha.yandex.ru/moscow/concert/places/izvestiia-hall': '*', # izvestiya_hall
            #'https://afisha.yandex.ru/moscow/theatre/places/teatr-gogolia': '*', #gogolia theatre
            'https://afisha.yandex.ru/moscow/theatre/places/teatr-im-maiakovskogo': '*', # Маяковского театр
            'https://afisha.yandex.ru/moscow/theatre/places/mkht-im-chekhova': '*' , #МХАТ Чехова
            'https://afisha.yandex.ru/nizhny-novgorod/concert/places/dvorets-sporta-nagornyi': '*' , #Дворец спорта «Нагорный»
            'https://afisha.yandex.ru/moscow/theatre/places/teatr-im-stanislavskogo-i-nemirovicha-danchenko': '*' , #stanislavskogo
            'https://afisha.yandex.ru/ufa/sport/places/ufa-arena': '*', #ufa-arena
            'https://afisha.yandex.ru/togliatti/concert/places/lada-arena': '*', #lada-arena
            'https://afisha.yandex.ru/chelyabinsk/concert/places/ledovaia-arena-traktor': '*', #arena-traktor
            'https://afisha.yandex.ru/yekaterinburg/sport/places/arena-uralets': '*', #arena-uralets,
            #'https://afisha.yandex.ru/saint-petersburg/sport/places/ska-arena': '*',  # SKA arena
            'https://afisha.yandex.ru/moscow/concert/places/khram-khrista-spasitelia-zal-tserkovnykh-soborov': '*', # hram
            'https://afisha.yandex.ru/moscow/theatre/places/teatr-im-mossoveta': '*' #mossoveta
        }
        self.special_url = {
            #'https://afisha.yandex.ru/moscow/selections/standup': '*',  # Стендап
        }
        self.special_url_with_one_person = {
            #'https://afisha.yandex.ru/artist/pavel-volia?city=moscow': 'Павел Воля'  # Павел Воля
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
                if not event_info['session']: #возможно это абонемент
                    continue
                if not event_info.get('session').get('ticket'):
                    continue
                if event_info['session']['ticket']['saleStatus'] != 'available':
                    continue

                title = event_info['event']['title']

                year, month, day = event_info['session']['date'].split('-')
                month = month_list[int(month)]
                time = event_info['session'].get('datetime')
                if not time: # значит возможно это Абонемент и нет точного времени мероприятия
                    continue
                time = time.split('T')[-1]
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
        while True:
            r = self.selenium_smart_captha(url)
            if not ('captcha' in r.url and len(r.url) > 200):
                break
        return r

    def selenium_smart_captha(self, url: str):
        chrome_options = ChromeOptions()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument('--headless=new')
        chrome_options.add_argument("--no-sandbox")
        driver = ProxyWebDriver(proxy=self.proxy, chrome_options=chrome_options)

        try:
            driver.get(url=url)
            time.sleep(1)
            r = self.solve_smart_captcha_checkbox(driver)
            driver.get(url=r.url)
            r = self.solve_smart_captcha_image(driver)
        except TimeoutException as e:
            raise ProxyError(e)
        except Exception as e:
            raise Exception(str(e))
        finally:
            driver.quit()
        return r

    def solve_smart_captcha_checkbox(self, driver):
        body = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        ).get_attribute('innerHTML')

        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')

        data = {
            'rdata': r_data,
            'pdata': pdata
        }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
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
        img_captha = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.AdvancedCaptcha-View img"))
        )
        img_captha_href = img_captha.get_attribute('src')

        img_captha_order = driver.find_element(By.CSS_SELECTOR, value='div.AdvancedCaptcha-SilhouetteTask')
        img_captha_order.screenshot('afisha_catcha_order.png')

        textinstructions = driver.find_element(By.CSS_SELECTOR, value='span.Text').text

        r = self.session.get(img_captha_href, stream=True)
        if r.status_code == 200:
            with open('afisha_catcha.png', 'wb') as f:
                f.write(r.content)


        with Image.open('afisha_catcha.png') as img:
            image_with_elements = img.convert('RGB')
            image_with_elements.save('afisha_catcha.jpg')
        with open('afisha_catcha.jpg', 'rb') as img:
            image_with_elements = base64.b64encode(img.read())
        with Image.open('afisha_catcha_order.png') as img:
            w, h = img.size
            area = (0, 0, w-399, 0)
            image_with_order = ImageOps.crop(img, area)
            image_with_order = image_with_order.convert('RGB')
            image_with_order.save('afisha_catcha_order.jpg')
        with open('afisha_catcha_order.jpg', 'rb') as img:
            image_with_order = base64.b64encode(img.read())

        coordinates = yandex_afisha_coordinates_captha(image_with_elements,
                                                                           image_with_order,
                                                                           textinstructions)
        self.debug(coordinates)
       
        for coordinate in coordinates:
            actions = ActionChains(driver)
            img_captha = driver.find_element(By.CSS_SELECTOR, "div.AdvancedCaptcha-View img")
            x_offset = float(coordinate['x'])
            y_offset = float(coordinate['y'])
            # Получаем координаты верхнего левого угла элемента
            element_location = img_captha.location
            # Вычисляем смещение, чтобы переместиться в верхний левый угол
            xoffset = element_location['x']
            yoffset = element_location['y']
            actions.move_by_offset(xoffset, yoffset)
            actions.pause(1)
            actions.move_by_offset(x_offset, y_offset)
            actions.click().perform()
            actions.pause(1)
            actions.reset_actions()

        body = driver.find_element(By.CSS_SELECTOR, 'body').get_attribute('innerHTML')
        href = double_split(body, 'formAction:"', '"')
        r_data = driver.find_element(By.CSS_SELECTOR, 'input[name=rdata]').get_attribute('value')
        pdata = driver.find_element(By.CSS_SELECTOR, 'input[name=pdata]').get_attribute('value')
        rep = driver.find_element(By.CSS_SELECTOR, 'input[name=rep]').get_attribute('value')

        data = {
            'rep': rep,
            'rdata': r_data,
            'pdata': pdata
            }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
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
        url = f'https://afisha.yandex.ru{href}&rep={rep}'
        r = self.session.post(url, timeout=10, headers=headers, data=data)

        if not '<div class="CheckboxCaptcha' in r.text:
            self.debug(f'Yandex captcha success solved bro!')
        else:
            self.error(f'Yandex captcha DIDNT solved!!!')
            
        
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

    def _get_url_events_from_special_url__with_one_person(self, url: str) -> list[str]:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'afisha.yandex.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="112", "YaBrowser";v="23", "Not:A-Brand";v="99"',
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

        soup = BeautifulSoup(r.text, 'lxml')
        all_events_url = []
        all_events_card = soup.select('div.person-schedule-list div.person-schedule-item__tickets a')
        client_key = double_split(r.text, '{"key":"', '"')
        for event_data in all_events_card:
            event_id = event_data.get('data-event-id')
            region_id = event_data.get('data-region-id')
            href = f'https://widget.afisha.yandex.ru/w/events/{event_id}' \
                   f'?clientKey={client_key}&regionId={region_id}&widgetName=w2&lang=ru'
            all_events_url.append(href)
        return all_events_url

    def _get_events_from_special_url__with_one_person(self, all_events_url: list[str]) -> list[tuple]:
        output_data = []
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'content-type': 'application/json; charset=UTF-8',
            'host': 'widget.afisha.yandex.ru',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        for url in all_events_url:
            r = self.session.get(url, headers=headers)
            r = self.check_captcha(r, url, headers)

            requests_id = double_split(r.text, '"X-Request-Id":"', '"')
            csrf_token = double_split(r.text, '"X-CSRF-Token":"', '"')
            yanex_uid = double_split(r.text, '"X-Yandex-Uid":"', '"')
            client_key = double_split(url, 'clientKey=', '&')
            event_id = double_split(url, '/events/', '?')
            reg_id = double_split(url, 'regionId=', '&')
            event_params = {'client_key': client_key}
            headers = {
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'connection': 'keep-alive',
                'content-type': 'application/json; charset=UTF-8',
                'host': 'widget.afisha.yandex.ru',
                'referer': url,
                'pragma': 'no-cache',
                'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'timeout': '5000',
                'X-Csrf-Token': csrf_token,
                'X-Request-Id': requests_id,
                'X-Yandex-Uid': yanex_uid,
                'user-agent': self.user_agent
            }
            json_data = None
            count_requests = 1
            while json_data is None and count_requests != 50:
                url = f'https://widget.afisha.yandex.ru/api/tickets/v1/events/{event_id}' \
                      f'?clientKey={client_key}&region_id={reg_id}&req_number={count_requests}'
                r = self.session.get(url, headers=headers)
                r = self.check_captcha(r, url, headers)
                json_data = r.json().get('result')
                count_requests += 1

            presentation_sessions = json_data['event']['presentationSessions']
            data_sessions = [sessions['date'] for sessions in presentation_sessions]
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                          'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'connection': 'keep-alive',
                'content-type': 'application/json; charset=UTF-8',
                'host': 'widget.afisha.yandex.ru',
                'pragma': 'no-cache',
                'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'user-agent': self.user_agent
            }
            json_data = None
            count_requests = 1
            while json_data is None and count_requests != 50:
                url = f'https://widget.afisha.yandex.ru/api/tickets/v1/events/' \
                      f'{event_id}/venues/sessions?clientKey={client_key}&offset=0&limit=20' \
                      f'&dateFrom={data_sessions[0]}&dateTo={data_sessions[-1]}&regionId={reg_id}&req_number={count_requests}'
                r = self.session.get(url, headers=headers)
                r = self.check_captcha(r, url, headers)
                json_data = r.json().get('result', {}).get('venues', {}).get('items')
                count_requests += 1
                if count_requests == 25:
                    data_sessions = data_sessions[::-1]
            sessions = json_data[0]['sessions']
            for event in sessions:
                title = event['eventName']
                href = f'https://widget.afisha.yandex.ru/w/sessions/{event["key"]}?widgetName=w2&lang=ru'

                date = event['sessionDate'].split('T')
                date_date = date[0].split('-')
                date_date[1] = month_list[int(date_date[1])]
                date_time = date[1].split('+')[0]
                normal_date = date_date[-1] + ' ' + date_date[1] + ' ' + date_date[0] + ' ' + date_time

                scene = ''
                venue = event['name']
                event_params['session_id'] = event['key']

                output_data.append((title, href, normal_date, scene, event_params, venue))
        return output_data

    def body(self):
        # for url, venue in self.special_url_with_one_person.items():
        #     all_events_url = self._get_url_events_from_special_url__with_one_person(url)
        #     for event in  self._get_events_from_special_url__with_one_person(all_events_url):
        #         event_params = str(event[4]).replace("'", "\"")
        #         event_name = event[0].replace("'", '"')
        #         self.register_event(event_name, event[1], date=event[2], scene=event[3],
        #                             event_params=event_params, venue=venue)

        # places = self.get_places()
        for url in self.our_urls:
            self.debug(url, '<---yandex_events--->')
            client_key, request_id, dates =  self.place_request(url)
            venue = self.place['title']
            if url == 'https://afisha.yandex.ru/kazan/circus_show/places/tsirk-kazan':
                venue = 'Казанский цирк'
            elif url == 'https://afisha.yandex.ru/saint-petersburg/concert/places/ledovyi-dvorets':
                venue = 'Ледовый дворец (ХКСКА)'
            elif url == 'https://afisha.yandex.ru/moscow/concert/places/izvestiia-hall':
                venue = '(КЗ) Известия Холл'
            elif url == 'https://afisha.yandex.ru/moscow/theatre/places/teatr-im-maiakovskogo':
                venue = 'Театр Маяковского'
            elif url == 'https://afisha.yandex.ru/moscow/concert/places/khram-khrista-spasitelia-zal-tserkovnykh-soborov':
                venue = '(Христа Спасителя)'

            # date - 2023-01-02; period - 30
            for date, period in dates.items():
                date_items = self.schedule_events_request(request_id, date, period)
                a_events = self.get_place_events(date_items, client_key)
                for event in a_events:
                    #self.debug(event)
                    if 'VK Stadiaum' in venue:
                        if 'Абонемент' in event[0]:
                            continue
                    event_params = str(event[4]).replace("'", "\"")
                    event_name = event[0].replace("'", '"')
                    self.register_event(event_name, event[1], date=event[2], scene=event[3],
                                        event_params=event_params, venue=venue)

        # for url in self.special_url:
        #     total_events, request_id, client_key = self._get_total_events(url)
        #     final_event = self._get_card_with_event(total_events, request_id, client_key, url)
        #     for event in final_event:
        #         event_params = str(event[4]).replace("'", "\"")
        #         event_name = event[0].replace("'", '"')
        #         self.register_event(event_name, event[1], date=event[2], scene=event[3],
        #                             event_params=event_params, venue=event[5])
