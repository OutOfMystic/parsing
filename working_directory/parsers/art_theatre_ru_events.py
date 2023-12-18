from datetime import datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.manager.proxy.instances import ProxySession


class Gorkovo(EventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://art-theatre.ru/afisha'

    def before_body(self):
        self.session = ProxySession(self)

    def get_day_and_month(self, all_data_in_day):
        date = all_data_in_day.find('div', class_='data')
        date = double_split(str(date), '>', '<').strip()
        return date

    def ajax_request_for_data(self, month_to_url, year_to_url, origin_month_for_request, all_event_in_month, page=2):
        timestamp_for_request = datetime(day=1, month=int(month_to_url), year=year_to_url)
        timestamp_for_request = datetime.timestamp(timestamp_for_request)
        timestamp_for_request = int(timestamp_for_request * 1000)

        url = f'https://art-theatre.ru/ajax/poster.php?date={timestamp_for_request}&page={page}'
        data_json = self.get_ajax(url)
        text_for_soup = data_json.get('content')
        if text_for_soup:
            soup_from_request = BeautifulSoup(text_for_soup, 'lxml')
            all_event_in_soup_from_request = soup_from_request.find_all('div', class_='day-items')
            all_event_in_month.extend(all_event_in_soup_from_request)
            if data_json.get('next') != 'false':
                try:
                    month_first_date_in_ajax = self.get_day_and_month(all_event_in_soup_from_request[0]).split()[1]
                except IndexError:
                    return all_event_in_month
                month_last_date_in_ajax = self.get_day_and_month(all_event_in_soup_from_request[-1]).split()[1]
                if month_first_date_in_ajax == origin_month_for_request and month_last_date_in_ajax == origin_month_for_request:
                    page += 1
                    all_event_in_month = self.ajax_request_for_data(month_to_url, year_to_url,
                                                                    origin_month_for_request, all_event_in_month)

        return all_event_in_month

    def parse_events(self):
        a_events = []
        datetime_now = datetime.now()

        while True:
            month_to_url = str(datetime_now.month)
            if len(month_to_url) == 1:
                month_to_url = '0' + month_to_url
            year_to_url = datetime_now.year
            datetime_now = datetime_now + relativedelta(months=1)
            href_to_data = f'/{year_to_url}/{month_to_url}'

            url = self.url + href_to_data
            soup = self.get_events(url, href_to_data)

            all_event_in_month = soup.find_all('div', class_='day-items')
            if len(all_event_in_month) == 0:
                break

            origin_month_for_request = self.get_day_and_month(all_event_in_month[0]).split()[1]

            all_event_in_month = self.ajax_request_for_data(month_to_url, year_to_url, origin_month_for_request, all_event_in_month)

            for all_data_in_day in all_event_in_month:
                date = self.get_day_and_month(all_data_in_day)
                if date.split()[1] != origin_month_for_request:
                    break

                events = all_data_in_day.find_all('div', class_='item')
                for event in events:
                    if 'is-no-button' in event.get('class'):
                        continue
                    title = event.find('a')
                    title = double_split(str(title), '>', '<').strip()

                    time = event.find('div', class_='time').text

                    if len(date.split()[1]) > 3:
                        date = date.split()[0] + ' ' + date.split()[1][:3].title()
                    else:
                        date = date.split()[0] + ' ' + date.split()[1].title()
                    normal_date = date + ' ' + str(year_to_url) + ' ' + time

                    check_button_with_href = event.find('div', class_='btn')
                    if check_button_with_href:
                        continue
                    href = event.find('a', class_='btn').get('href')

                    a_events.append([title, href, normal_date])

        return a_events

    def get_ajax(self, url):
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'content-type': 'application/json',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)
        return r.json()

    def get_events(self, url, href_to_data):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'referer': f'https://art-theatre.ru/afisha{href_to_data}',
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

        return soup

    def body(self):
        events_is_complite = []
        a_events = self.parse_events()

        for event in a_events:
            if event not in events_is_complite:
                self.register_event(event[0], event[1], date=event[2])
                events_is_complite.append(event)