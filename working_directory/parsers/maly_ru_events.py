from bs4 import BeautifulSoup
from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class Parser(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.maly.ru/tickets'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def get_request(self, month_params=''):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'www.maly.ru',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }

        r = await self.session.get(self.url + month_params, headers=headers)

        return r.text

    def get_next_month_params(self, months_container):
        month_params = ''

        next_year_href = months_container.find_all('a')[-1]['href']
        months_href = months_container.find_all('a', class_='poster-dates__link')
        for i, month_href in enumerate(months_href):
            if '_active' in month_href['class']:
                month_params = next_year_href if i == len(months_href) - 1 else months_href[i + 1]['href']
                break

        return '?' + month_params.split('?')[-1]

    def get_events(self, events_container, year):
        a_events = []

        for date_events_block in events_container.find_all('div', class_='poster-tables__item'):
            day_month = date_events_block.find('div', class_='dayname').text.strip()
            day, month, year = day_month.split() 
            day_month_f = f"{day} {month[:3].capitalize()}" #"03 Сен" 

            for event_tr in date_events_block.find('table', class_='poster-details').find_all('tr'):
                buy_btn = event_tr.find('a', class_='poster-details__buy')
                if 'disabled' in buy_btn['class']:
                    continue

                href = 'http://www.maly.ru' + buy_btn['href']
                title = event_tr.find('a', class_='l_title').text.strip()
                scene_time = event_tr.find('td', class_='poster-details__scene').text.strip()
                scene_time = scene_time.split()
                scene = ' '.join([text.strip() for text in scene_time if ':' not in text])
                time = scene_time[-1]
                date = f'{day_month_f} {year} {time}'

                a_events.append([title, href, date, scene])

        return a_events
    
    async def body(self):
        not_events_to_skip = 0
        a_events = []
        month_params = ''
        while True:
            soup = BeautifulSoup(await self.get_request(month_params), 'lxml')
            month_params = self.get_next_month_params(soup.find('div', class_='poster-dates'))
            year = soup.find('h2', class_='page__title').text.strip().split()[0]
            events = self.get_events(soup.find('div', class_='poster-tables'), year)

            if events:
                a_events += events
            elif not_events_to_skip == 4:
                break
            else:
                not_events_to_skip += 1

        for event in a_events:
            self.register_event(event[0], event[1], date=event[2],
                                scene=event[3], venue='Малый театр')
