import json
import time
from bs4 import BeautifulSoup

from parse_module.models.parser import EventParser
from parse_module.utils.parse_utils import double_split
from parse_module.utils.date import month_list
from parse_module.manager.proxy.instances import ProxySession


class KassirParser(EventParser):
    proxy_check_url = 'https://msk.kassir.ru/'

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 3600
        self.driver_source = None
        self.our_urls = {
            # 'https://msk.kassir.ru/bilety-v-teatr': '*',
            # 'https://msk.kassir.ru/bilety-na-sportivnye-meropriyatiya': '*',
            'https://msk.kassir.ru/sportivnye-kompleksy/dvorets-sporta-megasport': '*',
            'https://msk.kassir.ru/sportivnye-kompleksy/vtb-arena-tsentralnyiy-stadion-dinamo': '*',
            'https://msk.kassir.ru/kluby/adrenaline-stadium': '*',
            'https://msk.kassir.ru/sportivnye-kompleksy/cska-arena': '*',
            'https://msk.kassir.ru/sportivnye-kompleksy/ok-lujniki': '*',
            # 'https://msk.kassir.ru/teatry/vahtangova': '*',
            # 'https://msk.kassir.ru/teatry/mht-chehova': '*',
            # 'https://msk.kassir.ru/teatry/teatr-satiryi': '*',
            # 'https://msk.kassir.ru/teatry/operetty': '*',
            'https://spb.kassir.ru/sportivnye-kompleksy/sk-yubileynyiy-2': '*',
            'https://spb.kassir.ru/koncertnye-zaly/ledovyiy-dvorets-2': '*',
            'https://msk.kassir.ru/koncertnye-zaly/gosudarstvennyj-kremlevskij-dvorec': '*',
            'https://sochi.kassir.ru/teatry/zimniy-teatr': '*',
            'https://msk.kassir.ru/koncertnye-zaly/zelenyiy-teatr-vdnh': '*',
        }

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup):
        a_events = []
        all_events_container = soup.find_all('div', class_='js-pager-container')

        if all_events_container:
            events_containers = all_events_container.find_all('div', class_='tiles-container')
        else:
            events_containers = soup.find_all('div', class_='tiles-container')

        for container in events_containers:
            events = container.find_all('div', class_='action-tile') + container.find_all('div', class_='event-tile')
            events += container.find_all('div', class_=['event', 'js-ec-tile'])
            for event in events:
                if 'Нет свободных мест' in event.text:
                    continue

                event_info = event.find('a', class_='image').get('data-ec-item')
                title = event.find('div', class_='title').find('a').get('title')
                href = event.find('a', class_='btn').get('href').replace('---', '-')

                try:
                    venue = double_split(event_info, '"venueName":"', '","').strip()
                except IndexError:
                    continue
                venue = venue.split(' - ')[0]
                if 'МХТ' in venue:
                    venue = 'Театр Чехова'

                dates = []
                event_date = ''
                if 'date' in event_info:
                    if '"date":{' in event_info:
                        event_info_date_str = double_split(event_info, '"date":', '},') + '}'
                    else:
                        event_info_date_str = double_split(event_info, '"date":', '",') + '"'

                    event_info_date = json.loads(event_info_date_str)
                    if 'start_min' in event_info_date:
                        event_date = self.format_date(event_info_date['start_min'])
                    else:
                        event_date = self.format_date(event_info_date)

                afisha_event_info = {
                    'title': title,
                    'href': href,
                    'date': event_date,
                    'venue': venue,
                }

                all_event_dates = self.get_all_event_dates(afisha_event_info)
                if not all_event_dates:  # request to the event probably returned 404 doesn't exist
                    self.lprint(f'[kassir_warning]: events_parser couldnt parse event from event response - '
                                f'{afisha_event_info}', console_print=False)
                    continue
                else:
                    dates += all_event_dates

                for date in dates:
                    a_events.append((date['title'], date['href'], date['date'], date['venue']))

        return a_events

    def get_all_event_dates(self, afisha_event_info):
        url = afisha_event_info['href']
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "YaBrowser";v="23"',
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

        if 'Страница не найдена' in r.text:
            return []

        soup = BeautifulSoup(r.text, 'lxml')
        events_table = soup.find('div', class_='events-table')
        date_dropdown = soup.find('div', class_='date-dropdown')
        card_data = soup.find_all('li', class_='event-date-selector-tab')

        if events_table:
            return self.get_table_event_dates(events_table)
        elif date_dropdown:
            return self.get_dropdown_event_dates(date_dropdown, afisha_event_info)
        elif len(card_data) > 0:
            output_data = []
            for card in card_data:
                data_in_span = card.find_all('span', class_='inline-flex')
                event_date = data_in_span[0].text.split()
                event_date[1] = event_date[1][:3].title()
                time = data_in_span[-1].text
                normal_date = ' '.join(event_date) + ' ' + time

                href = afisha_event_info['href'].split('.ru/')[0]
                link = card.find('a').get('href')
                href = href + '.ru' + link
                output_data.append(
                    {
                        'title': afisha_event_info['title'],
                        'href': href,
                        'date': normal_date,
                        'venue': afisha_event_info['venue']
                    }
                )
            return output_data
        else:
            if '"dateFrom":"' in r.text:
                event_date = double_split(r.text, '"dateFrom":"', '"')
                afisha_event_info['date'] = self.format_date(event_date)

            return [afisha_event_info]

    def get_table_event_dates(self, events_table):
        event_rows = events_table.find_all('tr')

        date_events = []
        for row in event_rows:
            title = row.find('td', class_='col-title').text
            href = row.find('a', class_='btn').get('href').replace('---', '-')
            year = href.split('_')[-1].split('-')[0]
            date = row.find('td', class_='col-date').text
            date = self.format_str_date(date.replace('\n', ' ').replace('  ', ''), year)

            venue = row.find('td', class_='col-place').text.strip()
            venue = venue.split(' - ')[0]
            if 'МХТ' in venue:
                venue = 'Театр Чехова'

            date_events.append({
                'title': title,
                'href': href,
                'date': date,
                'venue': venue,
            })

        return date_events

    def get_dropdown_event_dates(self, date_dropdown, afisha_event_info):
        if afisha_event_info['date']:
            year = afisha_event_info['date'].split()[-2]
        else:
            year = None

        dropdown_dates = [
            {
                'id': option['value'].strip(),
                'date': self.format_str_date(option.text.strip(), year)
            } for option in date_dropdown.find_all('option')
        ]

        date_events = []
        for dr_date in dropdown_dates:
            date_events.append({
                'title': afisha_event_info['title'],
                'date': dr_date['date'],
                'href': f'{afisha_event_info["href"]}#{dr_date["id"]}',
                'venue': afisha_event_info['venue'],
            })

        return date_events

    def format_date(self, date):
        y_m_d, time = date.split()
        y, m, d = y_m_d.split('-')
        month = month_list[int(m)]
        time = time[:-3]
        date = f'{d} {month} {y} {time}'
        return date

    def format_str_date(self, str_date, y=None):
        str_date_spl = str_date.split()

        if len(str_date_spl) == 4:
            d, m, wd, t = str_date_spl
        else:
            d, m, t = str_date_spl

        m = m[:3].capitalize()

        if not y:
            y = calculate_year(m)

        date = f'{d} {m} {y} {t}'

        return date

    def get_events(self, url):
        a_events = []

        c = 90
        p = 1
        while True:
            page_url = f'{url}?c={c}&p={p}'
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': self.user_agent,
                'x-requested-with': 'XMLHttpRequest'
            }
            if p:
                headers.update({'referer': url})
            r = self.session.get(page_url, headers=headers)

            if '{"html":"' in r.text:
                to_soup = r.json()['html']
            else:
                to_soup = r.text

            soup = BeautifulSoup(to_soup, 'lxml')
            a_events += self.parse_events(soup)

            if 'Загрузить ещё' not in r.text and '"more_results":"' not in r.text:
                break
            else:
                p += 1

        return a_events

    def body(self):
        a_events = []
        for url in self.our_urls:
            a_events += self.get_events(url)

        a_events = list(set(a_events))
        for event in a_events:
            if event[2] == '':
                continue
            self.register_event(event[0], event[1], date=event[2], venue=event[3])
