import aiohttp as aiohttp


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

