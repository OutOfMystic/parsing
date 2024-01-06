from typing import Any, Optional, Coroutine

import aiohttp as aiohttp
from aiohttp import hdrs, ContentTypeError
from aiohttp.client_reqrep import _is_expected_content_type, ClientResponse
from aiohttp.typedefs import StrOrURL, JSONDecoder, DEFAULT_JSON_DECODER
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
    def parse_str(row: str):
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


class AwaitedResponse:
    def __init__(self,
                 request_info,
                 history,
                 content,
                 headers,
                 encoding,
                 status_code):
        self.request_info = request_info
        self.history = history
        self.encoding = encoding
        self.content = content
        self.headers = headers
        self.status_code = status_code
        self.text = self.content.decode(encoding)  # type: ignore[no-any-return,union-attr]

    def json(self, *,
             encoding: Optional[str] = None,
             loads: JSONDecoder = DEFAULT_JSON_DECODER,
             content_type: Optional[str] = "application/json") -> Any:
        if content_type:
            ctype = self.headers.get(hdrs.CONTENT_TYPE, "").lower()
            if not _is_expected_content_type(ctype, content_type):
                raise ContentTypeError(
                    self.request_info,
                    self.history,
                    message=(
                        "Attempt to decode JSON with " "unexpected mimetype: %s" % ctype
                    ),
                    headers=self.headers,
                )
        stripped = self._body.strip()  # type: ignore[union-attr]
        if not stripped:
            return None

        if encoding is None:
            encoding = self.encoding

        return loads(stripped.decode(encoding))


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

    @staticmethod
    async def _static_response(method, *args, **kwargs):
        response: ClientResponse
        async with method(*args, **kwargs) as response:
            return AwaitedResponse(response.request_info,
                                   response.history,
                                   await response.read(),
                                   response.headers,
                                   response.get_encoding(),
                                   response.status)

    async def get(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any) -> AwaitedResponse:
        """Perform HTTP GET request."""
        return await self._static_response(super().get, url, allow_redirects=allow_redirects, **kwargs)

    async def options(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any) -> AwaitedResponse:
        """Perform HTTP OPTIONS request."""
        return await self._static_response(super().options, url, allow_redirects=allow_redirects, **kwargs)

    async def head(self, url: StrOrURL, *, allow_redirects: bool = False, **kwargs: Any) -> AwaitedResponse:
        """Perform HTTP HEAD request."""
        return await self._static_response(super().head, url, allow_redirects=allow_redirects, **kwargs)

    async def post(self, url: StrOrURL, *, data: Any = None, **kwargs: Any) -> AwaitedResponse:
        """Perform HTTP POST request."""
        return await self._static_response(super().post, url, data, **kwargs)

    async def put(self, url: StrOrURL, *, data: Any = None, **kwargs: Any) -> AwaitedResponse:
        """Perform HTTP PUT request."""
        return await self._static_response(super().put, url, data, **kwargs)

    async def patch(self, url: StrOrURL, *, data: Any = None, **kwargs: Any) -> AwaitedResponse:
        """Perform HTTP PATCH request."""
        return await self._static_response(super().patch, url, data, **kwargs)

    async def delete(self, url: StrOrURL, **kwargs: Any) -> AwaitedResponse:
        """Perform HTTP DELETE request."""
        return await self._static_response(super().delete, url, **kwargs)

    def get_with(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any):
        """Perform HTTP GET request with ``with`` constructor."""
        return super().get(url, allow_redirects=allow_redirects, **kwargs)

    def options_with(self, url: StrOrURL, *, allow_redirects: bool = True, **kwargs: Any):
        """Perform HTTP OPTIONS request with ``with`` constructor."""
        return super().options(url, allow_redirects=allow_redirects, **kwargs)

    def head_with(self, url: StrOrURL, *, allow_redirects: bool = False, **kwargs: Any):
        """Perform HTTP HEAD request with ``with`` constructor."""
        return super().head(url, allow_redirects=allow_redirects, **kwargs)

    def post_with(self, url: StrOrURL, *, data: Any = None, **kwargs: Any):
        """Perform HTTP POST request with ``with`` constructor."""
        return super().post(url, data=data, **kwargs)

    def put_with(self, url: StrOrURL, *, data: Any = None, **kwargs: Any):
        """Perform HTTP PUT request with ``with`` constructor."""
        return super().put(url, data=data, **kwargs)

    def patch_with(self, url: StrOrURL, *, data: Any = None, **kwargs: Any):
        """Perform HTTP PATCH request with ``with`` constructor."""
        return super().patch(url, data=data, **kwargs)

    def delete_with(self, url: StrOrURL, **kwargs: Any):
        """Perform HTTP DELETE request with ``with`` constructor."""
        return super().delete(url, **kwargs)
