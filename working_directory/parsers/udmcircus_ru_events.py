from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.utils.date import make_date_if_year_is_unknown

class CircusIzevsk(AsyncEventParser):
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://quicktickets.ru/izhevsk-cirk'
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "no-cache",
            "dnt": "1",
            "pragma": "no-cache",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent
        }
        self.a_events = []

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def load_events(self):
        body = await self.session.get(self.url, headers=self.headers)
        soup = BeautifulSoup(body.text, 'lxml')

        all_performances = soup.find(id='elems-list')
        box_with_all_performances = all_performances.find_all(class_='elem')

        for one_performance in box_with_all_performances:
            try:
                title_of_performance = one_performance.find('h3').find(class_='underline').text
                sessions = one_performance.find(class_='sessions')
                all_events = sessions.find_all(class_='session-column')

                for one_event in all_events:
                    href_relative = one_event.find('a').get('href')
                    href_absolute = f"https://quicktickets.ru{href_relative}"
                    date = one_event.find(class_='underline').text
                    date_to_write = make_date_if_year_is_unknown(*date.split(), need_datetime=True)

                    self.a_events.append((title_of_performance, href_absolute, date_to_write))
            except Exception as ex:
                self.error(f'{ex} {one_performance}')

    async def body(self):
        await self.load_events()
        for event in self.a_events:
            #self.info(event)
            self.register_event(event[0], event[1], date=event[2], venue='Удмуртский цирк Ижевск')