import json

from loguru import logger
from requests.exceptions import ProxyError
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from parse_module.coroutines import AsyncEventParser
from parse_module.drivers.proxelenium import ProxyWebDriver
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import EventParser
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class BolshoiParser(EventParser):
    proxy_check = SpecialConditions(url='https://ticket.bolshoi.ru/')

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://ticket.bolshoi.ru/api/v1/client/shows/'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, json_data):
        a_events = []

        for event in json_data:
            if event.get('minPrice') is None:
                continue
            href = 'https://ticket.bolshoi.ru/show/' + str(event.get('showId'))

            title = event.get('showName')

            date = event.get('specDate').split('-')[::-1]
            time_event = event.get('startTime').split(':')[:2]

            date = date[0] + ' ' + month_list[int(date[1])] + ' ' + date[2] + ' ' + ':'.join(time_event)

            scene = event.get('hallName')

            venue = 'Большой театр'

            a_events.append((title, href, date, venue, scene))

        return a_events

    def get_all_event_dates(self, event_url):
        pass

    def get_events(self):
        driver = ProxyWebDriver(proxy=self.proxy)
        json_loads = []

        try:
            driver.get(url=self.url)

            driver_json = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "pre"))
            ).text
            json_loads = json.loads(driver_json)

        except TimeoutException as e:
            logger.error(f"Возникла ошибка {e}")
            raise ProxyError(e)
        finally:
            driver.quit()

        return self.parse_events(json_loads)

    def body(self):
        a_events = self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], venue=event[3], scene=event[4])
