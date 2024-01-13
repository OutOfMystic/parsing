import asyncio
import json
import time
import json as json_
from typing import overload
from urllib.parse import urlparse

from . import check
from .check import SpecialConditions, NormalConditions
from ...utils import provision
from .instances import UniProxy
from ...utils.logger import logger, track_coroutine
from ...utils.provision import threading_try


class ProxyOnCondition:
    def __init__(self, proxy_hub, condition, from_data=None):
        self.proxy_hub = proxy_hub
        self.condition = condition
        self.proxies = []
        self.last_update = 0
        self.plen = 0
        self.last_tab = 0
        self.in_check = False
        if from_data is not None:
            if len(from_data["proxies"]) / len(self.proxy_hub.all_proxies) > 0.3:
                self.proxies = [UniProxy(proxy) for proxy in from_data['proxies']]
                self.plen = len(self.proxies)
                self.last_update = from_data['timestamp']
                logger.info(f'Restored proxies for {self.condition.url} '
                            f'({len(from_data["proxies"])})', name='Controller')
            else:
                logger.warning(f'Refused loading proxies for {self.condition.url}. '
                               f'Poor availability ({len(from_data["proxies"])})', name='Controller')
        self.update()

    def json(self):
        str_proxies = [str(proxy) for proxy in self.proxies]
        return {
            "timestamp": self.last_update,
            "proxies": str_proxies
        }

    def update(self):
        if self.in_check:
            return
        lifetime = self.condition.lifetime if self.proxies else 180
        if self.last_update < time.time() - lifetime:
            self.in_check = True
            threading_try(check.check_proxies, args=(self.proxy_hub.all_proxies, self,))
            self.in_check = False

    def report(self, proxy):
        if proxy in self.proxies:
            self.proxies.remove(proxy)

    def put(self, proxies):
        self.last_update = time.time()
        self.proxies = proxies
        self.plen = len(proxies)
        self.proxy_hub.save_states()

    def _wait(self):
        sleep_time = 0.1
        while not self.last_update:
            sleep_time += 0.1
            time.sleep(0.1)

    @track_coroutine
    async def _wait_async(self):
        sleep_time = 0.1
        while not self.last_update:
            sleep_time += 0.1
            await asyncio.sleep(0.1)

    def get(self):
        if not self.last_update:
            self._wait()
        if self.proxies:
            self.last_tab += 1
            tab = self.last_tab % self.plen
            return self.proxies[tab]
        else:
            return None

    @track_coroutine
    async def get_async(self):
        if not self.last_update:
            await self._wait_async()
        if self.proxies:
            self.last_tab += 1
            tab = self.last_tab % self.plen
            return self.proxies[tab]
        else:
            return None

    def get_all(self):
        if not self.last_update:
            self._wait()
        return self.proxies

    async def get_all_async(self):
        if not self.last_update:
            await self._wait_async()
        return self.proxies

    async def amount(self):
        if not self.last_update:
            await self._wait_async()
        return len(self.proxies)


class ProxyHub:
    def __init__(self):
        self.all_proxies = []
        self.last_tab = 0

        self.stored_data = self._load_stored_data()
        self.proxies_on_condition = {}

    @overload
    def add_route(self, check_conditions: SpecialConditions):
        ...

    @overload
    def add_route(self, url: str):
        ...

    @overload
    def get_all(self, check_conditions: SpecialConditions):
        ...

    @overload
    def get_all(self, url: str):
        ...

    @overload
    def get(self, check_conditions: SpecialConditions):
        ...

    @overload
    def get(self, url: str):
        ...

    @overload
    async def get_async(self, url: str):
        ...

    @overload
    async def get_async(self, check_conditions: SpecialConditions):
        ...

    @overload
    async def get_all_async(self, url: str):
        ...

    @overload
    async def get_all_async(self, check_conditions: SpecialConditions):
        ...

    @overload
    async def get_amount(self, url: str):
        ...

    @overload
    async def get_amount(self, check_conditions: SpecialConditions):
        ...

    @staticmethod
    def _check_argument(check_conditions):
        if isinstance(check_conditions, SpecialConditions):
            pass
        elif isinstance(check_conditions, str):
            check_conditions = SpecialConditions(url=check_conditions)
        else:
            return TypeError(f'Argument should be ``Conditions`` or ``str``')
        return check_conditions

    @staticmethod
    def _load_stored_data():
        stored = provision.try_open('proxies.json', {})
        return {tuple(json.loads(key)): proxies for key, proxies in stored.items()}

    def save_states(self):
        data_to_store = {}
        for proxy_group in self.proxies_on_condition.values():
            signature = json.dumps(proxy_group.condition.signature)
            data_to_store[signature] = proxy_group.json()
        provision.try_write('proxies.json', data_to_store)

    def add_route(self, check_conditions):
        check_conditions = self._check_argument(check_conditions)
        if check_conditions.signature not in self.proxies_on_condition:
            stored_data = self.stored_data.get(check_conditions.signature, None)
            new_pool = ProxyOnCondition(self, check_conditions, from_data=stored_data)
            self.proxies_on_condition[check_conditions.signature] = new_pool

    def get(self, check_conditions):
        check_conditions = self._check_argument(check_conditions)
        proxies = self.proxies_on_condition[check_conditions.signature]
        return proxies.get()
    
    def get_all(self, check_conditions):
        check_conditions = self._check_argument(check_conditions)
        proxies = self.proxies_on_condition[check_conditions.signature]
        return proxies.get_all()

    async def get_async(self, check_conditions):
        check_conditions = self._check_argument(check_conditions)
        proxies = self.proxies_on_condition[check_conditions.signature]
        return await proxies.get_async()

    async def get_all_async(self, check_conditions):
        check_conditions = self._check_argument(check_conditions)
        proxies = self.proxies_on_condition[check_conditions.signature]
        return await proxies.get_all_async()

    async def get_amount(self, check_conditions):
        check_conditions = self._check_argument(check_conditions)
        proxies = self.proxies_on_condition[check_conditions.signature]
        return await proxies.amount()

    def report(self, check_conditions, proxy):
        check_conditions = self._check_argument(check_conditions)
        proxies = self.proxies_on_condition[check_conditions.signature]
        proxies.report(proxy)

    def update(self):
        for proxy_group in self.proxies_on_condition.values():
            proxy_group.update()


class ManualProxies(ProxyHub):
    def __init__(self, path):
        super().__init__()
        provision.multi_try(self._load_proxies, args=(path,), name='Controller')
        self.add_route(NormalConditions())

    def _load_proxies(self, path):
        with open(path, 'r') as fp:
            payload = json_.load(fp)
        to_proxies = [UniProxy(row) for row in payload]
        self.all_proxies = to_proxies
