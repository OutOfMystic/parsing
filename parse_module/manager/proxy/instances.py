import json
from typing import Any

import aiohttp as aiohttp
from aiohttp.client import _RequestContextManager
from aiohttp.typedefs import StrOrURL
from requests import Session


class Proxy:
    def __init__(self, ip, port, login=None, password=None, schema='http'):
        self.ip = ip
        self.port = port
        self.login = login
        self.password = password
        self.schema = schema
        self.args = self._format_args()
        self.requests = self._format_requests()
        self.async_proxy, self.async_proxy_auth = self._format_async()

    def __str__(self):
        if self.login:
            args = self.schema, self.ip, self.port, self.login, self.password
            return '%s://%s:%d@%s:%s' % args
        else:
            return f'{self.schema}://{self.login:}{self.password}'

    def _format_requests(self):
        proxies = {
            'http': '%s://%s:%s@%s:%d' % self.args,
            'https': '%s://%s:%s@%s:%d' % self.args
        }
        return proxies

    def _format_async(self):
        async_proxy = f"{self.schema}://{self.ip}:{self.port}"
        proxy_auth = None
        if self.login and self.password:
            proxy_auth = aiohttp.BasicAuth(self.login, self.password)
        return async_proxy, proxy_auth

    def _format_args(self):
        return self.schema, self.login, self.password, self.ip, self.port


class UniProxy(Proxy):
    def __init__(self, *args, login=None, password=None, schema='http'):
        if len(args) == 1:
            determinator = args[0]
            if isinstance(determinator, str):
                type_, ip, port, user, pwd = UniProxy.parse_str(determinator)
                super().__init__(ip, port, login=user, password=pwd, schema=type_)
            elif isinstance(determinator, (list, tuple)):
                type_, ip, port, user, pwd = UniProxy.parse_iter(determinator)
                super().__init__(ip, port, login=user, password=pwd, schema=type_)
            else:
                typeof = type(determinator).__name__
                raise AttributeError(f'the argument can\'t be a {typeof}')
        else:
            type_, ip, port, user, pwd = UniProxy.parse_iter(args)
            type_ = schema if schema != 'http' else type_
            user = login if login else user
            pwd = password if password else pwd
            super().__init__(ip, port, login=user, password=pwd, schema=type_)

    @staticmethod
    def parse_str(row):
        proxy_type, proxy_user, proxy_pass = 'http', None, None
        if r'://' in row:
            proxy_type, row = row.split(r'://')
        if '@' in row:
            row, logpass = row.split('@')
            proxy_user, proxy_pass = logpass.split(':')
        spl_proxy = row.split(':')
        proxy_host = spl_proxy[0]
        proxy_port = int(spl_proxy[1])
        return proxy_type, proxy_host, proxy_port, proxy_user, proxy_pass

    @staticmethod
    def parse_iter(iter_):
        proxy_type, proxy_user, proxy_pass = 'http', None, None
        if len(iter_) == 5:
            proxy_type, proxy_host, proxy_port, proxy_user, proxy_pass = iter_
        elif len(iter_) == 4:
            proxy_host, proxy_port, proxy_user, proxy_pass = iter_
        elif len(iter_) == 3:
            proxy_type, proxy_host, proxy_port = iter_
        elif len(iter_) == 2:
            proxy_host, proxy_port = iter_
        else:
            raise AttributeError(f'Error creating a proxy using {iter_}')
        return proxy_type, proxy_host, proxy_port, proxy_user, proxy_pass


class ProxySession(Session):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    def request(self, *args, **kwargs):
        kwargs['proxies'] = self.bot.proxy.requests
        kwargs['timeout'] = kwargs['timeout'] if 'timeout' in kwargs else 30
        return super().request(*args, **kwargs)


class AsyncProxySession(aiohttp.ClientSession):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def _request(self, *args, **kwargs):
        kwargs['proxy'] = self.bot.proxy.async_proxy
        kwargs['proxy_auth'] = self.bot.proxy.async_proxy_auth
        kwargs['timeout'] = kwargs['timeout'] if 'timeout' in kwargs else 30
        if 'verify' in kwargs:
            kwargs['ssl'] = kwargs.pop('verify')
        return await super()._request(*args, **kwargs)

    async def get_text(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any):
        async with self.get(url, allow_redirects=allow_redirects, ** kwargs) as response:
            return await response.text()

    async def get_json(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any):
        async with self.get(url, allow_redirects=allow_redirects, ** kwargs) as response:
            return await response.json()

    async def post_text(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any):
        async with self.post(url, allow_redirects=allow_redirects, ** kwargs) as response:
            return await response.text()

    async def post_json(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any):
        async with self.post(url, allow_redirects=allow_redirects, ** kwargs) as response:
            return await response.json()
