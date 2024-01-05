from bs4 import BeautifulSoup
from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from parse_module.utils.parse_utils import double_split


class Parser(EventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://mxat.ru/timetable/'

    def before_body(self):
        self.session = ProxySession(self)

    def get_request(self, month_params=''):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'mxat.ru',
            'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url + month_params, headers=headers, verify=False)
        return r.text

    def get_months_params(self, months_container):
        months_params = [month_a['href'].split('/')[-2] for month_a in months_container.find_all('a')]

        return months_params

    def get_events(self, events_container, month, year):
        a_events = []
        try:
            prof_events_info = double_split(str(events_container),
                                            '<script type="text/javascript">(function() { var init = function()',
                                            '</script>')
        except IndexError:
            return a_events

        day = '0'
        for event in events_container.find_all('div', class_='event'):
            if 'first' in event['class']:
                day = event.find('div', class_='dt').text.split(',')[0].strip()

            time = event.find('span', class_='tm').text.strip()
            title = event.find('div', class_='ttl').find('a').text.strip()
            scene = event.find('span', class_='pl').text.strip()

            date = f'{day} {month} {year} {time}'

            btn_container = event.find('div', class_='tbtn')

            if not btn_container:
                continue

            if btn_container.text == 'Оставить заявку':
                continue

            event_prof_id = btn_container.find('div')['id']
            event_prof_info = double_split(prof_events_info, event_prof_id, '}')
            company_id = int(double_split(event_prof_info, '"companyId":', ','))
            event_id = double_split(event_prof_info, '"eventId":', ',')
            show_id = double_split(event_prof_info, '"showId":', '}')
            href = f'https://spa.profticket.ru/customer/{company_id}/shows/{show_id}/#{event_id}'

            a_events.append([title, href, date, scene, company_id, event_id, show_id])

        return a_events

    def parse_month_events(self, month_params=''):
        resp = self.get_request(month_params)
        soup = BeautifulSoup(resp, 'lxml')
        month = soup.find('div', class_='submenu').find('td', class_='active').find('a').text[:3].capitalize()
        year = soup.find('td', class_='month')['style'].split('/')[-1].split('-')[0]
        events = self.get_events(soup, month, year)

        if month_params:
            return events
        else:
            months = self.get_months_params(soup.find('div', class_='submenu'))
            return events, months

    def body(self):
        events, months_params = self.parse_month_events()
        a_events = events

        for month_params in months_params:
            a_events += self.parse_month_events(month_params)

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2], scene=event[3],
                                company_id=event[4], event_id=event[5], show_id=event[6], venue='МХТ имени Чехова')

