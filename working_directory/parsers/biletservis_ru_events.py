import more_itertools
from bs4 import BeautifulSoup
import datetime

from requests import TooManyRedirects

from parse_module.models.parser import EventParser
from parse_module.utils import provision
from parse_module.utils.parse_utils import double_split, lrsplit
from parse_module.manager.proxy.instances import ProxySession


class BuletServis(EventParser):
    def __init__(self, controller):
        super().__init__(controller)
        self.a_events = None
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://biletservis.ru/bolshoi-teatr.html'
        self.needed_venues = [
            {
                'venue_id': 1, # используется при поиске
                'venue': 'Большой театр',
                'place_id': '24' # place_id это параметр в запросе seats парсера
            }
        ]

    def before_body(self):
        self.session = ProxySession(self)

    def parse_events(self, soup, venue_id, venue):
        a_events = {}

        all_month = soup.find('ul', class_='monthmenu')
        all_month = all_month.find_all('li')

        good_date = []
        for li in all_month:
            span = li.find('span')
            if span.get('style') is None:
                date = str(li)[str(li).index("('"):str(li).index("')")+2]
                good_date.append(eval(date))

        for date_for_url in good_date[:-1]:
            date_start = int(datetime.datetime.strptime(date_for_url[0], "%d.%m.%Y").timestamp())
            date_end = int(datetime.datetime.strptime(date_for_url[1], "%d.%m.%Y").timestamp())
            url = f'https://biletservis.ru/fevents.php?pID={venue_id}&date=curdate' \
                  f'&date1={date_start}&date2={date_end}&ajax=1'
            soup = self.get_data(url=url)

            all_tr = soup.find_all('tr', class_='category_icon2')
            for tr in all_tr:

                date = tr.find('td', class_="a_date")
                date_day = date.find('b').text
                date_month = date.find('span').text[:3]

                title = tr.find('td', class_='a_meta')
                href_and_title = title.find('a')

                time = title.find('small').text
                title = href_and_title.text
                href = 'https://biletservis.ru' + href_and_title.get('href')

                onclick = href_and_title.get('onclick')
                evdate_id = double_split(onclick, '?date=', "'")

                place = tr.find('td', class_='a_place')
                scene = place.find('span').text

                year = date_for_url[0].split('.')[-1]
                date = date_day + ' ' + date_month + ' ' + year + ' ' + time

                a_events[evdate_id] = [title, href, date, venue, scene]
        return a_events

    def get_data(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,imag'
                      'e/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'host': 'biletservis.ru',
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
        r = self.session.post(url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        return soup

    def get_events(self):
        url = self.url
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/'
                      'apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'biletservis.ru',
            'referer': 'https://biletservis.ru/teatr/',
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
        r = self.session.post(url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')

        a_events = {}
        for data in self.needed_venues:
            a_event_pack = self.parse_events(soup, data['venue_id'], data['venue'])
            a_events.update(a_event_pack)
        return a_events

    def get_extra_data(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,i'
                      'mage/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'biletservis.ru',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }

        try:
            r = self.session.get(url, headers=headers)
        except TooManyRedirects:
            return {}
        if r.url == 'https://biletservis.ru/':
            return {}

        needed_place_ids = [place['place_id'] for place in self.needed_venues]
        all_data = double_split(r.text, 'widgetHallsIdsArr = new Array();', '\n')
        all_data = all_data.replace('; ', ';')
        data_cells = lrsplit(all_data, ".push('", "');")
        data_rows = more_itertools.grouper(data_cells, 7, incomplete='strict')

        li_loaders = lrsplit(r.text, '<li onclick="$(\'#loader\').l', '});">')
        li_list = [[double_split(li, "$('#eventdate').val('", "'"),
                   double_split(li, '?date=', "'")] for li in li_loaders]
        cur_datesec = double_split(r.text, "id=eventdate value='", "'>")
        cur_eventdate = double_split(r.text, "dateid value='", "'>")
        li_row = [cur_datesec, cur_eventdate]
        li_list.append(li_row)

        extra_data = {}
        for row in data_rows:
            datesec = row[0]
            for li_datesec, li_eventdate in li_list:
                if li_datesec == datesec:
                    eventdate = li_eventdate
                    break
            else:
                raise RuntimeError('Wrond eventdate and datesec pair on the webpage')
            formatted = {
                'sec_date': row[0],
                'event_bs_id': row[1],
                'event_id_cfg': row[2],
                'ev_name_cfg': row[3],
                'place_id': row[4],
                'scene_name_cfg': row[5],
                'hall_id': row[6]
            }
            if formatted['place_id'] not in needed_place_ids:
                continue
            extra_data[eventdate] = formatted
        return extra_data

    def body(self):
        self.a_events = self.get_events()
        urls = set(event[1] for event in self.a_events.values())

        extra_data = {}
        for url in urls:
            new_data = self.multi_try(self.get_extra_data, tries=1,
                                      raise_exc=False, args=(url,))
            if new_data == provision.TryError:
                continue
            extra_data.update(new_data)

        for eventdate, event in self.a_events.items():
            if eventdate not in extra_data:
                continue
            kwargs = extra_data[eventdate]
            self.register_event(event[0], event[1], date=event[2],
                                venue=event[3], scene=event[4], **kwargs)
