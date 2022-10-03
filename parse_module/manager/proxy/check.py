import requests
import time

from ...utils import provision
from .instances import UniProxy
from . import loader

CHECK_DELAY = 2 * 60 * 60


def check_task(proxy, url, method):
    method = requests.get if method == 'get' else 'post'
    try:
        method(url, proxies=proxy.requests)
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
    results = provision.pool(check_task, tasks, 10)
    good_proxies = [proxy for proxy in results.values() if proxy]

    domain = loader.parse_domain(url)
    good_str_proxies = [str(proxy) for proxy in good_proxies]
    proxy_data[domain] = [time.time()] + good_str_proxies
    provision.try_write('proxies.json', proxy_data)
    return good_proxies


def check_proxies(proxies, url, callback, method='get'):
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


proxy_data = provision.try_open('proxies.json', {})
