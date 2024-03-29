from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.coroutines import AsyncEventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession


class TktGe(AsyncEventParser):
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://tkt.ge/event/355735/bruno-mars'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def body(self):
        all_events = (
            ('Бруно Марс', 'https://tkt.ge/api/v2/shows/get?itemId=355735', '01 Окт 2023 21:00'),
        )
        for event in all_events:
            self.register_event(event[0], event[1], date=event[2])
