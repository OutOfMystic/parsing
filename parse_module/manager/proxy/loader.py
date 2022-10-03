import os.path
import time
import json
from urllib.parse import urlparse

from ...utils import provision
from .instances import UniProxy
from .. import backstage


class ProxyOnUrl:
    def __init__(self, domain):
        self.domain = domain
        self.proxies = []
        self.plen = 0
        self.last_tab = 0

    def update(self, proxies):
        self.proxies = proxies
        self.plen = len(proxies)

    def get(self):
        wait_counter = float('inf')
        sleep_time = 0.1
        while not self.plen:
            wait_counter += sleep_time
            if wait_counter > 10:
                wait_counter = 0
                print(f'Waiting for proxy for {self.domain}')
            time.sleep(sleep_time)

        self.last_tab += 1
        tab = self.last_tab % self.plen
        return self.proxies[tab]


class Proxies:
    def __init__(self):
        self.all_proxies = []
        self.last_tab = get_tab()
        self.proxies_on_url = {}

    def check_proxies(self, url='http://httpbin.org/'):
        domain = parse_domain(url)
        if domain not in self.proxies_on_url:
            self.proxies_on_url[domain] = ProxyOnUrl(domain)
        callback = self.proxies_on_url[domain]
        backstage.check_proxies(self.all_proxies, url, callback)

    def get(self, url='http://httpbin.org/'):
        domain = parse_domain(url)
        if domain not in self.proxies_on_url:
            domain = 'httpbin.org'
        proxies_on_url = self.proxies_on_url[domain]
        return proxies_on_url.get()


class ManualProxies(Proxies):
    def __init__(self, path):
        super().__init__()
        provision.multi_try(self._load_proxies, args=(path,), name='Proxy')

    def _load_proxies(self, path):
        with open(path, 'r') as fp:
            payload = json.load(fp)
        to_proxies = [UniProxy(row) for row in payload]
        self.all_proxies = to_proxies
        self.check_proxies()


def get_tab(increase=True):
    while True:
        payload = provision.try_open('tab', '1', json_=False)
        chrtab = int(payload)
        if increase:
            chrtab += 1
            provision.try_write('tab', str(chrtab), json_=False)
        return chrtab


def parse_domain(url):
    domain = urlparse(url).netloc
    domain_parts = domain.split('.')[-2:]
    return '.'.join(domain_parts)
