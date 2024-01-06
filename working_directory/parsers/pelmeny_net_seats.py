from typing import NamedTuple

from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class PelmenyNet(AsyncSeatsParser):
    event = 'pelmeny.net'
    url_filter = lambda url: False

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def body(self):
        return None
