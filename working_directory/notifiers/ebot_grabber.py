import json
import os
import threading
from multiprocessing.pool import ThreadPool
from threading import Lock

from loguru import logger

from parse_module.manager.core import BotCore
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.manager.proxy.loader import ManualProxies
from parse_module.utils.parse_utils import double_split, lrsplit
from parse_module.utils.provision import try_open, multi_try, TryError

events_path = os.path.join('notifiers', 'events.json')


class DomainGrabber(BotCore):
    events = try_open(events_path, {}, json_=True)

    def __init__(self, domain, proxy, tickets=True):
        super().__init__(proxy=proxy)
        self.tech_code = None
        self.domain = domain
        self.name = domain
        self.tickets = tickets
        self.saves_path = os.path.join('notifiers', 'all_tickets', f'{self.domain}.json')
        self.saves = try_open(self.saves_path, {}, json_=True)
        self.session = AsyncProxySession(self)
        self.lock = Lock()

    def get_events(self):
        url = f'https://{self.domain}/events'
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/we'
                      'bp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-MY,en;q=0.9,ru-RU;q=0.8,ru;q=0.7,en-US;q=0.6,vi;q=0.5,ar;q=0.4',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
        }
        r = self.session.get(url, headers=headers)
        self.tech_code = double_split(r.text, '{"tech_name":"', '"')

        next_jses = lrsplit(r.text, 'src="/_next/static/', " defer")
        next_script = [js for js in next_jses if '_buildManifest.js' in js][0]
        next_code = next_script.split('/')[0]
        acquiring_id = self.get_acquiring(next_code)

        url = f'https://landing-api.pbilet.net/api/v1/landing/{self.tech_code}' \
              f'/event/expanded?limit=25&page=1'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru',
            'cache-control': 'no-cache',
            'origin': f'https://{self.domain}',
            'pragma': 'no-cache',
            'referer': f'https://{self.domain}/',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.user_agent,
        }
        r = self.session.get(url, headers=headers)
        events = extract_events(r.json(), self.domain, self.tech_code)
        for event in events:
            event['acquiring_id'] = acquiring_id

        last_page = r.json()['last_page']
        for page in range(2, last_page + 1):
            url = f'https://landing-api.pbilet.net/api/v1/landing/{self.tech_code}' \
                  f'/event/expanded?limit=25&page={page}'
            r = self.session.get(url, headers=headers)
            if not r.text:
                continue
            new_events = extract_events(r.json(), self.domain, self.tech_code)
            for event in new_events:
                event['acquiring_id'] = acquiring_id
            events.extend(new_events)
        return events

    def get_acquiring(self, next_code):
        url = f'https://{self.domain}/_next/data/{next_code}/default/cart.json'
        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru',
            'cache-control': 'no-cache',
            'origin': f'https://{self.domain}',
            'pragma': 'no-cache',
            'referer': f'https://widget-frame.{self.domain}/',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent,
            'X-Nextjs-Data': '1'
        }
        r = self.session.get(url, headers=headers)
        acquirings = r.json()['pageProps']['theme']['acquiring_configs']
        for acquiring in acquirings:
            if 'stripe' in acquiring['name'].lower():
                continue
            else:
                return acquiring['id']
        else:
            raise RuntimeError(f'Acquiring wasnt found: {acquirings}')

    def get_tickets(self, event):
        logger.debug(f'getting tickets {self.domain} {event}')
        url = f'https://widget-api.{self.domain}/api/widget/{event["widget"]}/' \
              f'ticket?lang=ru&currency=RUB&event={event["current_id"]}&is_landing=true'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru',
            'cache-control': 'no-cache',
            'origin': f'https://{self.domain}',
            'pragma': 'no-cache',
            'referer': f'https://widget-frame.{self.domain}/',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.user_agent,
        }
        r = self.session.get(url, headers=headers)
        if 'sectors' not in r.text:
            return {}
        sectors = {}
        for sector in r.json()['sectors']:
            rows = {}
            if 'r' not in sector:
                continue
            for row in sector['r']:
                tickets = []
                row_num = row['i']
                for seat in row['s']:
                    if 'c' not in seat:
                        continue
                    if 'cr' not in seat:
                        continue
                    if 'p' not in seat:
                        continue
                    if 'tt' not in seat:
                        continue
                    ticket = {
                        'id': f"{event['current_id']}_{seat['d']}",
                        'x': seat['x'],
                        'y': seat['y'],
                        'price': seat['p'],
                        'our': seat['our'],
                        'k': seat['k'],
                        'seat': seat['i'],
                        'extra': {'uss': False},
                        'at': seat['at'],
                        'tt': seat['tt'],
                        'sector': sector['i'],
                        'row': row_num,
                        'selectedEvent': event['current_id'],
                        'selectedDate': event['date'],
                        'event_id': event['id'],
                        'count': seat['c']
                    }
                    tickets.append(ticket)
                if len(tickets) < 4:
                    continue
                tickets.sort(key=lambda t: t['seat'])
                rows[row_num] = tickets
            if not rows:
                continue
            sectors[sector['i']] = rows
        return sectors

    def get_everything(self):
        logger.debug(f'getting_events {self.domain}')
        events = self.get_events()
        events_with_tickets = []
        for i, event in enumerate(events):
            tickets = multi_try(self.get_tickets, name=f'{self.domain} tickets',
                                args=(event,), raise_exc=False)
            if tickets == TryError:
                continue
            event_copy = event.copy()
            event_copy['seats'] = tickets
            events_with_tickets.append(event_copy)
        return events, events_with_tickets

    def save_events(self, events, save_to, path):
        try:
            self.lock.acquire()
            json.dumps(events)
            save_to[self.domain] = {}
            save_to[self.domain]['events'] = events
            if not events:
                logger.info('Empty events')
                return
            save_to[self.domain]['landing'] = self.tech_code
            with open(path, 'w') as f:
                json.dump(save_to, f, separators=(',', ':'))
        except Exception as err:
            print('Saving data error:', self.domain, str(err))
            for event in events:
                try:
                    json.dumps(event)
                except Exception as err:
                    print(self.domain, event['name'], event['date'], err, str(err))
                    logger.error(event)
        finally:
            self.lock.release()

    def on_many_exceptions(self):
        self.stop()

    async def body(self):
        if self.tickets:
            events, events_with_tickets = self.get_everything()
            self.save_events(events, self.events, events_path)
            self.save_events(events_with_tickets, self.saves, self.saves_path)
        else:
            logger.debug(f'getting_events {self.domain}')
            events = self.get_events()
            self.save_events(events, self.events, events_path)
        self.stop()
        logger.success(f'Saving complete {self.domain}')


def extract_events(json_, domain, landing):
    events = []
    for result in json_['results']:
        event = {
            'name': result['event']['title'],
            'date': f"{result['event']['date_start']} {result['event']['time_start']}",
            'id': result['id'],
            'current_id': result['event']['id'],
            'widget': result['widget'],
            'domain': domain,
            'landing': landing
        }
        events.append(event)
    return events


def get_data(domain, tickets=True):
    grabber = DomainGrabber(domain, proxy_hub.get('http://landing-api.pbilet.net'), tickets=tickets)
    grabber.start()
    grabber.join()
    logger.success(f'Thread stopped {domain}')
    return domain


def get_event_data(domain):
    return get_data(domain, tickets=False)


if __name__ == '__main__':
    proxy_hub = ManualProxies('all_proxies.json')
    proxy_hub.add_route('http://landing-api.pbilet.net')
    with open(os.path.join('notifiers', 'domains.txt')) as f:
        domains = [domain for domain in f.read().split('\n') if domain]
    with ThreadPool(45) as pool:
        for domain in pool.map(get_event_data, domains):
            continue
