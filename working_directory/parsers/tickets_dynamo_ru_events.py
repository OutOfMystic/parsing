from bs4 import BeautifulSoup
import datetime

from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession


class DynamoParser(EventParser):
    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 1800
        self.driver_source = None
        self.url = 'https://tickets.dynamo.ru/?_ga=2.193174821.947964618.1675930069-641847379.1675930069'

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []

        list_events = soup.find_all('div', class_='ticket_item')
        first_parameter_for_href = soup.find('body').find('script').text.split('; ')[2]
        first_parameter_for_href = first_parameter_for_href.split(', ')[1]
        first_parameter_for_href = first_parameter_for_href[1:-3]

        season = soup.find('div', class_='title_block_link').text
        prev_year_in_season, next_year_in_season = season.split()[-1].split('/')

        for event in list_events:
            title_teams = event.find_all('div', class_='games_ticket_team')
            title = title_teams[0].text.strip() + ' - ' + title_teams[1].text.strip()

            second_parameter_for_href = event.get('onclick').split('\'')
            for string in second_parameter_for_href:
                if '@' in string:
                    second_parameter_for_href = string.replace('@', '%40')
            href = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{second_parameter_for_href}?clientKey={first_parameter_for_href}'

            day_and_month = event.find('div', class_='games_ticket_item_data').text.split()
            day = day_and_month[0]
            month = day_and_month[1][:3]

            time = event.find('div', class_='games_ticket_item_vs').text

            normal_date = self.get_date_for_parse(day, month, prev_year_in_season, next_year_in_season, time)

            # venue = event.find('div', class_='games_ticket_tournament').text

            # a_events.append([title, href, normal_date, venue])
            a_events.append([title, href, normal_date])

        return a_events

    def get_date_for_parse(self, day, month, prev_year_in_season, next_year_in_season, time):
        month_num_by_str = {
            "Янв": 1, "Фев": 2, "Мар": 3, "Апр": 4,
            "Май": 5, "Июн": 6, "Июл": 7, "Авг": 8,
            "Сен": 9, "Окт": 10, "Ноя": 11, "Дек": 12,
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
            "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
            "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        date_now = datetime.date.today()
        if len(day) == 1:
            day = f'0{day}'

        if date_now.year == int(next_year_in_season):
            normal_date = day + ' ' + month + ' ' + next_year_in_season + ' ' + time
        else:
            month_int = month_num_by_str.get(month)
            if month_int >= date_now.month:
                normal_date = day + ' ' + month + ' ' + prev_year_in_season + ' ' + time
            else:
                normal_date = day + ' ' + month + ' ' + next_year_in_season + ' ' + time
        return normal_date

    def get_events(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'tickets.dynamo.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = self.parse_events(soup)

        return a_events

    def body(self):
        a_events = self.get_events()

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2])
