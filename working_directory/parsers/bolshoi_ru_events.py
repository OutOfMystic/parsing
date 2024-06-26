import json
from time import sleep
from datetime import datetime
from collections import namedtuple


from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from parse_module.drivers.chrome_selenium_driver import ChromeProxyWebDriver as ProxyWebDriver
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession

Events = namedtuple('Event', ['title', 'url', 'datetime', 'scheme'])
class BolshoiParser(EventParser):
    proxy_check_url = 'https://ticket.bolshoi.ru/'
    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url_for_tickets = 'https://ticket.bolshoi.ru/show/'
        self.url = 'https://ticket.bolshoi.ru/'

    def before_body(self):
        self.session = ProxySession(self)

    @staticmethod
    def make_date(date_str, time_str):
        '''
        "date_str": "2024-06-18",
        "time_str": "19:00:00",
        '''
        datetime_str = f"{date_str} {time_str}"
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        return dt

    def load_page_with_events(self) -> dict:
        with ProxyWebDriver(capability=True) as driver:
            driver.get("https://ticket.bolshoi.ru/")
            sleep(5)  # Убедитесь, что страница загружена полностью
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            # Сбор логов производительности
            logs = driver.get_capabilites_logs()
            body_dict = driver.find_data_in_responseReceived(logs,
                                                 find_patterns=('https://ticket.bolshoi.ru/api/v1/client/shows'))
            return body_dict

    def parsing_event(self, data):
        all_events = []
        for event in data:
            id = event.get('showId')
            url = f"{self.url_for_tickets}{id}"
            title = event.get('showName').strip()
            date_str = event.get('specDate')
            time_str = event.get('startTime')
            datetime_ = self.make_date(date_str, time_str)
            scene = event.get('hallName')

            event = Events(title, url, datetime_, scene)
            all_events.append(event)
        return all_events

    def body(self):
        events = self.load_page_with_events()
        final_events = self.parsing_event(events)

        for event in final_events:
            #print(event)
            self.register_event(
                event_name=event.title,
                url=event.url,
                date=event.datetime,
                scene=event.scheme,
                venue='Большой театр')