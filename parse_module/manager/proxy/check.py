import asyncio
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import requests
import time

from requests.exceptions import ProxyError

from ...utils import provision
from ...utils.logger import logger
from ...models import user_agent

CHECK_DELAY = 2 * 60 * 60


class SpecialConditions:
    semaphores_on_condition = {}
    async_semaphores_on_condition = {}

    def __init__(self,
                 url='http://httpbin.org/',
                 method=requests.get,
                 handler=None,
                 lifetime=3600,
                 max_parsers_on_ip=None):
        self.url = url
        self.method = method
        self.handler = handler if handler else self.default_handler
        assert lifetime >= 120, 'Proxy lifetime should be more or equal to 2 minutes'
        self.lifetime = lifetime
        self.max_parsers_on_ip = max_parsers_on_ip
        self.signature = (self.url, self.method.__name__, self.default_handler.__name__,)
        self.semaphores_on_condition[self.signature] = defaultdict(threading.Semaphore)
        self.async_semaphores_on_condition[self.signature] = defaultdict(asyncio.Semaphore)

    def get_proxy_semaphore(self, proxy) -> Optional[threading.Semaphore]:
        if self.max_parsers_on_ip:
            return self.semaphores_on_condition[self.signature][proxy.args]

    def get_async_proxy_semaphore(self, proxy) -> Optional[asyncio.Semaphore]:
        if self.max_parsers_on_ip:
            return self.async_semaphores_on_condition[self.signature][proxy.args]

    @staticmethod
    def default_handler(proxy, url, method):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp'
                      ',image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': user_agent.random()
        }
        r = method(url, proxies=proxy.requests, headers=headers, timeout=10)
        if not r.ok:
            raise ProxyError


class NormalConditions(SpecialConditions):
    def __init__(self):
        super().__init__()


def check_task(check_args):
    handler, proxy, url, method = check_args
    try:
        handler(proxy, url, method)
    except Exception as err:
        # logger.info(f'Skipping proxy: {err}', name='Controller')
        return None
    else:
        return proxy


def check_proxies(proxies, proxies_on_condition):
    # CHECK TASKS POOLING
    start_time = time.time()
    tasks = []
    condition: SpecialConditions
    condition = proxies_on_condition.condition

    for proxy in proxies:
        task = [condition.handler, proxy, condition.url, condition.method]
        tasks.append(task)
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_task, tasks)

    good_proxies = [value for value in results if value]
    proxies_on_condition.put(good_proxies)

    # FORMATTING
    exec_time = time.time() - start_time
    good_count = len(good_proxies)
    if good_count == 0:
        logger_func = logger.error
    elif good_count > 0.3 * len(proxies):
        logger_func = logger.info
    else:
        logger_func = logger.warning
    logger_func(f'{good_count} proxies for {condition.url} '
                f'were obtained in {exec_time:.1f} seconds', name='Controller')

