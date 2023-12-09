import os.path
import time
import json
from urllib.parse import urlparse

from loguru import logger

from . import check
from ...utils import provision
from .instances import UniProxy
from .. import backstage


class ProxyOnDomain:
    def __init__(self, domain):
        self.domain = domain
        self.proxies = []
        self.plen = 0
        self.last_tab = 0

    def update(self, proxies):
        self.proxies = proxies
        self.plen = len(proxies)

    def _wait(self):
        wait_counter = float('inf')
        sleep_time = 0.1
        while not self.plen:
            wait_counter += sleep_time
            if wait_counter > 10:
                wait_counter = 0
                print(f'Waiting for proxy for {self.domain}')
            time.sleep(sleep_time)

    def get(self):
        self._wait()
        self.last_tab += 1
        tab = self.last_tab % self.plen
        return self.proxies[tab]

    def get_all(self):
        self._wait()
        return self.proxies


class Proxies:
    def __init__(self):
        self.all_proxies = []
        self.last_tab = get_tab()
        self.proxies_on_domain = {}

    def add_route(self, url='http://httpbin.org/'):
        domain = parse_domain(url)
        if domain not in self.proxies_on_domain:
            self.proxies_on_domain[domain] = ProxyOnDomain(domain)
        callback = self.proxies_on_domain[domain]
        backstage.tasker.put(check.check_proxies, self.all_proxies, url, callback)
        
    def _get_proxies_on_domain(self, url):
        domain = parse_domain(url)
        if domain not in self.proxies_on_domain:
            domain = 'httpbin.org'
        proxies_on_domain = self.proxies_on_domain[domain]
        return proxies_on_domain
        
    def get(self, url='http://httpbin.org/'):
        proxies_on_domain = self._get_proxies_on_domain(url)
        proxy = proxies_on_domain.get()
        return proxy
    
    def get_all(self, url='http://httpbin.org/'):
        proxies_on_domain = self._get_proxies_on_domain(url)
        return proxies_on_domain.get_all()


class ManualProxies(Proxies):
    def __init__(self, path):
        super().__init__()
        provision.multi_try(self._load_proxies, args=(path,), name='Controller')
        self.add_route()

    def _load_proxies(self, path):
        with open(path, 'r') as fp:
            payload = json.load(fp)
        to_proxies = [UniProxy(row) for row in payload]
        self.all_proxies = to_proxies


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
    domain_parts = domain.split('.')   ##############
    return '.'.join(domain_parts)
