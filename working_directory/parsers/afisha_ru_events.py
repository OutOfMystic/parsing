from asyncio import sleep as asyncio_sleep
import re
import locale
from datetime import datetime
import ssl

from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.manager.proxy.sessions import AsyncProxySession
from parse_module.utils.parse_utils import double_split


class AfishaEvents(AsyncEventParser):
    proxy_check = SpecialConditions(url='https://www.afisha.ru/')

    def __init__(self, *args):
        super().__init__(*args)
        self.delay = 3600
        self.driver_source = None
        self.domain = 'https://www.afisha.ru'
        self.headers = {
            'Accept': 'application/json',
            'host': 'www.afisha.ru',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'User-Agent': self.user_agent
        }
        self.our_urls = {
            'https://www.afisha.ru/msk/concerthall/mdm-4740/': '*', #mdm
            #'https://www.afisha.ru/msk/theatre/gelikon-opera-15879450/performance/': '*', #gelikon ##
            'https://www.afisha.ru/msk/theatre/moskovskiy-teatr-operetty-15877729/': '*', #operetta
            #'https://www.afisha.ru/msk/theatre/teatr-gogolya-15926286/': '*', #gogolia theatr ##
            #'https://www.afisha.ru/msk/concerthall/crocus-city-hall-5222/': '*', # крокус сити холл ##
            'https://www.afisha.ru/msk/theatre/teatr-rossiyskoy-armii-15877731/': '*', #armii
            #'https://www.afisha.ru/msk/theatre/gubernskiy-teatr-15883628/': '*', #gubernskiy
        }
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def reformat_date(date):
        date = datetime.fromisoformat(date)
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        date_to_write = date.strftime("%d ") + \
            date.strftime("%b ").capitalize() + \
            date.strftime("%Y %H:%M")
        return date_to_write

    async def get_x_token(self, x_ath_url, count=0):
        headers = {
            'Accept': 'text/html; charset=utf-8',
            'host': 'www.afisha.ru',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'User-Agent': self.user_agent
        } 
        response = await self.session.get(x_ath_url, headers=headers, ssl=self.ssl_context)
        soup = BeautifulSoup(response.text, 'lxml')
        re_find_js = re.compile(r'^/js/.*\.js')
        scripts = soup.find_all('script', {'src': re_find_js})
        scripts = [self.domain + i.get('src') for i in scripts]
        
        headers = {
            'Accept': '*/*',
            'host': 'www.afisha.ru',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Cache-Control': 'no-cache',
            'refer': x_ath_url,
            'Connection': 'keep-alive',
            'User-Agent': self.user_agent
        }

        find_in_js = [
            'InternalDesktop',
            'InternalMobile'
            ]
        js_to_parsing = None
        for script in scripts:
            js_response = await self.session.get(script, headers=headers, ssl=self.ssl_context)
            js_text = js_response.text
            search = [i in js_text for i in find_in_js]
            if any(search):
                js_to_parsing = js_text
                break  
        
        if not js_to_parsing and count < 8:
            count += 1
            self.warning(f' try to find XApplication token + {count}')
            await self.change_proxy()
            return await self.get_x_token(x_ath_url, count)
        
        reformat = {}
        try:
            x_auth_all_txt = double_split(js_to_parsing, 'InternalDesktopInPage', '}')
            reformat =  [i.split(':') for i in x_auth_all_txt.split(',')]
            reformat = {key[0]: key[1].strip('"') for key in reformat if len(key) == 2}
        except Exception as ex:
            self.warning(f'cannot find XApplication token!, set default '
                        f'"ec16316b-67e3-4a32-9f05-6a00d1dc0a8b" {ex}')
       
        XApplication = reformat.get('InternalDesktop', 'ec16316b-67e3-4a32-9f05-6a00d1dc0a8b')

        return XApplication

    async def get_events_from_one_page(self, response, X_AUTH_TOKEN, url_page):
        a_events = [] 
        response_json = response.json()
        perfomances = response_json.get('Schedule', {})
        if not perfomances:
            response_json, perfomances = await self.if_not_perfomances(url_page)
        for category_name, category_data in perfomances.items():
            if not category_data:
                continue
            events = category_data["Items"]
            
            venue = response_json.get("PlaceInfo").get("Name")
            if venue in self.venue_reformat:
                venue = self.venue_reformat[venue]

            for event in events:
                # with open('TEST2.json', 'w', encoding='utf-8') as file:
                #     json.dump(event, file, indent=4, ensure_ascii=False)
                try:
                    name_of_title = [name for name, box in event.items() if box and 'Name' in box][0]
                    title = event.get(name_of_title).get("Name")
                    
                    all_dates = event["PlaceSchedules"]
                    all_sessions = [j for i in all_dates for j in i.get("Sessions")]

                    for session in all_sessions:
                        if session.get("SourceSessionID"):
                            sourcesessionID = session.get("SourceSessionID")
                            date = self.reformat_date(session.get("DateTime"))
                            url = f'https://mapi.afisha.ru/api/v21/hall/{sourcesessionID}?withSubstrate=true'
                            a_events.append((title, url, date, venue, sourcesessionID, X_AUTH_TOKEN ))
                except Exception as ex:
                    self.warning(f'Cannot save this event {event} {ex}')

        return a_events
    
    
    async def if_not_perfomances(self, url_page):
        self.warning(f"incorrect data in {url_page}, cannot find 'Schedule' in response.json() ")
        await self.make_new_session()
        await asyncio_sleep(1)
        response = await self.session.get(url_page, headers=self.headers, ssl=self.ssl_context)
        perfomances = response.json().get('Schedule', {})
        if not perfomances:
            self.error(f"2(request) incorrect data in {url_page}, cannot find 'Schedule' in response.json() ")
        return response.json(), perfomances
    

    async def make_new_session(self):
        await self.change_proxy()
        # self.proxy = await self.controller.proxy_hub.get_async(self.proxy_check)
        # self.session = AsyncProxySession(self)
        
    
    async def get_pages(self, url, count=0):
        response = await self.session.get(url, headers=self.headers, ssl=self.ssl_context)
        try:
            resp = response.json()
        except Exception as ex:
            resp = False
        if (response.status_code != 200 or not resp) and count < 8:
            count += 1
            self.warning(f' cannot load {url} try +={count}')
            await self.make_new_session()
            return await self.get_pages(url, count)
        
        links = set()
        # with open('TEST1.json', 'w', encoding='utf-8') as file:
        #     json.dump(response.json(), file, indent=4, ensure_ascii=False)
        perfomances = resp.get("Schedule",{}) 
        if not perfomances:
            resp, perfomances = await self.if_not_perfomances(url)
        for category_name, category_data in perfomances.items():
            if not category_data:
                continue
            try:
                how_many_pagination = category_data.get('Pager')
                
                currentPage = how_many_pagination.get('CurrentPage')
                pagesAll = how_many_pagination.get('PagesCount')
                if currentPage <= pagesAll:
                    box_links = how_many_pagination.get('PageLinks')
                    links.update([self.domain + i.get('Url') for i in box_links])
                else:
                    links.update([url])
            except Exception as ex:
                self.error(f'exception {ex}')
        return links
            
    async def fill_a_events(self, links, X_AUTH_TOKEN):
        for url in links:
            #self.info(url, '->>> for url in links')
            try:
                response = await self.session.get(url, headers=self.headers, ssl=self.ssl_context)
                if response.status_code == 200:
                    self.a_events.extend(await self.get_events_from_one_page(response, X_AUTH_TOKEN, url))
            except Exception as ex:
                self.warning(f'Exception {ex}')
                continue
            await asyncio_sleep(1)

    async def body(self):
        self.venue_reformat = {
            'МДМ': 'Московский Дворец Молодежи',
            'Московский театр оперетты': 'Театр Оперетты'
        }

        self.a_events = []
        
        for url, venue in self.our_urls.items():
            #self.info(url, '<- for url in self.our_urls')

            X_AUTH_TOKEN = await self.get_x_token('https://www.afisha.ru/')

            all_pages = await self.get_pages(url)
            #self.info(all_pages, '<-> all_pages')

            await self.fill_a_events(all_pages, X_AUTH_TOKEN)
            await asyncio_sleep(1)
    
        for event in self.a_events:
            #self.info(event)
            try:
                self.register_event(event[0], event[1], date=event[2],
                                     venue=event[3], sessionID=event[4], XApplication=event[5])
            except ValueError:
                continue
            





