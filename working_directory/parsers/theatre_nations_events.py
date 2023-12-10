from requests.exceptions import ProxyError

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import parse_utils


class Parser(EventParser):
    proxy_check_url = 'https://theatreofnations.ru/events/'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://theatreofnations.ru/events/'

    def before_body(self):
        self.session = ProxySession(self)

    def get_months(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'theatreofnations.ru',
            'pragma': 'no-cache',
            'referer': 'https://theatreofnations.ru/events',
            'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        if r.status_code != 200:
            raise ProxyError('Ne progruzilas, ip changed')
        url = 'https://theatreofnations.ru/events_ajax/?hall=&performance=&date_start=&date_end=&early_access=&only_active_events=&search_premiere=&search_child='
        r = self.session.get(url, headers=headers)
        months = []
        start_date = r.json()['calendar_dates'][0]
        for date in r.json()['calendar_dates']:
            new_month = date.split('-')[1]
            if new_month != start_date.split('-')[1]:
                range_date = f'{start_date},{past_date}'
                months.append(range_date)
                start_date = date
            past_date = date
        range_date = f'{start_date},{r.json()["calendar_dates"][-1]}'
        months.append(range_date)
        return months

    def get_events(self, months):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'theatreofnations.ru',
            'pragma': 'no-cache',
            'referer': 'https://theatreofnations.ru/events',
            'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        events = []
        for month in months:
            start_date, end_date = month.split(',')
            url = f'https://theatreofnations.ru/events_ajax/?hall=&performance=&date_start={start_date}&date_end={end_date}&early_access=&only_active_events=&search_premiere=&search_child='
            r = self.session.get(url, headers=headers)
            html = r.json()['html']
            events += html.split('<div class="events_groups_row"')[1:]

        a_events = []
        for event in events:
            if 'Купить билет' not in event:
                continue
            date = parse_utils.double_split(event, 'class="egr_date_date">', '</div>').strip()
            name = parse_utils.double_split(event, 'class="egr_content_performance_title">', '<').strip().replace('.',
                                                                                                                  '')
            scene = parse_utils.double_split(event, 'class="egr_content_hall">', '<')
            event_ids = parse_utils.lrsplit(event, '<a class="btn btn_js_sale" href="', '</a>')
            day, month = date.split()
            month = month.capitalize()
            if not event_ids:
                btns = parse_utils.lrsplit(event, '<a class="btn"', '</a>')
                for btn in btns:
                    if 'Купить билет' not in btn:
                        continue
                    event_id = parse_utils.double_split(btn, 'href="', '"')
                    time = parse_utils.double_split(event, 'class="egr_date_times_line">', '<').strip()
                    url = f'https://theatreofnations.ru{event_id}'
                    full_date = f"{day} {month} {time}"
                    a_events.append([name, url, full_date, scene])

            for event_info in event_ids:
                event_id = event_info[:event_info.find('"')]
                time = event_info[event_info.find(">") + 1:]
                url = f'https://theatreofnations.ru{event_id}'
                full_date = f"{day} {month} {time}"

                a_events.append([name, url, full_date, scene])

        return a_events

    def body(self):
        months = self.get_months()
        events = self.get_events(months)
        for event in events:
            self.register_event(event[0], event[1], date=event[2], scene=event[3])
