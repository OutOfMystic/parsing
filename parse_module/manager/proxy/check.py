import requests
import time

from loguru import logger
from requests.exceptions import ProxyError

from ...utils import provision, utils
from .instances import UniProxy
from . import loader

CHECK_DELAY = 2 * 60 * 60


def check_task(proxy, url, method):
    method = getattr(requests, method)
    try:
        r = method(url, proxies=proxy.requests, timeout=10)
        if r.status_code == 407:
            raise ProxyError('407 Proxy Authentication Failed')
        if r.status_code == 403:
            raise ProxyError('403 Ban')
    except Exception as err:
        print(f'Error checking proxy: {err}')
        return None
    else:
        return proxy


def check_tasks(proxies, url, method):
    tasks = []
    for proxy in proxies:
        task = [[proxy, url, method]]
        tasks.append(task)
    results = provision.pool(check_task, tasks, len(proxies) // 10 + 1)
    good_proxies = [proxy for proxy in results.values() if proxy]

    domain = loader.parse_domain(url)
    good_str_proxies = [str(proxy) for proxy in good_proxies]
    proxy_data[domain] = [time.time()] + good_str_proxies
    provision.try_write('proxies.json', proxy_data)
    return good_proxies


def check_proxies(proxies, url, callback, method='get'):
    start_time = time.time()
    domain = loader.parse_domain(url)
    if domain not in proxy_data:
        proxy_data[domain] = [time.time()]
        good_proxies = check_tasks(proxies, url, method)
    elif (time.time() - proxy_data[domain][0]) < CHECK_DELAY:
        good_proxies = []
        all_proxies = proxy_data[domain][1:]
        for proxy in all_proxies:
            formatted_proxy = UniProxy(proxy)
            good_proxies.append(formatted_proxy)
    else:
        good_proxies = check_tasks(proxies, url, method)
    callback.update(good_proxies)

    exec_time = time.time() - start_time
    good_count = len(good_proxies)
    if good_count == 0:
        color_func = utils.red
    elif good_count > 0.3 * len(proxies):
        color_func = utils.green
    else:
        color_func = utils.yellow
    good_count = color_func(str(good_count))
    if exec_time < 0.1:
        return
    print('Controller| ' + good_count +
          utils.green(f' proxies for {url} were obtained in {exec_time:.1f} seconds'))


proxy_data = provision.try_open('proxies.json', {})
