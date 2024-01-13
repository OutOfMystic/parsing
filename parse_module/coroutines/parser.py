import time
from abc import ABC, abstractmethod

from . import core, pooling
from ..connection import db_manager
from ..manager.backstage import tasker
from ..manager.proxy import check
from ..manager.proxy.sessions import AsyncProxySession
from ..models import parser
from ..utils import provision
from ..utils.exceptions import ProxyHubError
from ..utils.logger import logger


class AsyncParserBase(core.CoroutineBot, ABC):
    proxy_check = check.NormalConditions()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.session = None
        self.last_state = None
        self.spreading = 0.2
        self._notifier = None

    async def _get_proxy(self):
        self.proxy = await self.controller.proxy_hub.get_async(self.proxy_check)
        if not self.proxy:
            raise ProxyHubError(f'Out of proxies!')

    async def change_proxy(self, report=False):
        if report:
            self.controller.proxy_hub.report(self.proxy_check, self.proxy)
        # logger.debug('change_proxy start')
        await self._get_proxy()
        if isinstance(self.session, AsyncProxySession):
            await self.session.close()
        await self.before_body()
        # logger.debug('change_proxy finish')

    def set_notifier(self, notifier):
        if self._notifier:
            self.error(f'Notifier for parser {self.name} has already been set. Refused.')
        else:
            self._notifier = notifier

    def detach_notifier(self):
        self._notifier = None

    def trigger_notifier(self):
        notifier = self._notifier
        if notifier:
            notifier.proceed()

    def _debug_only(self, mes, *args):
        if self.controller.debug:
            self.debug(mes, *args)

    async def proceed(self):
        start_time = time.time()
        next_step_delay = min(self.get_delay() / 15, 120)
        if self.proxy is None:
            self._debug_only('changing proxy', int((time.time() - start_time) * 10) / 10)
            await provision.async_just_try(self._get_proxy, name=self.name)
            self._debug_only('changed proxy', int((time.time() - start_time) * 10) / 10)

        if self.proxy is not None:
            next_step_delay = self.get_delay()
            if not self.fully_inited:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                await self.inthread_init()
                self._debug_only('inited', int((time.time() - start_time) * 10) / 10)
            if self.fully_inited and self._terminator.alive:
                self._debug_only('Proceeding', int((time.time() - start_time) * 10) / 10)
                await super().proceed()
                self._debug_only('Proceeded', int((time.time() - start_time) * 10) / 10)
            else:
                next_step_delay = max(self.get_delay() / 7, 300)

        if self._terminator.alive:
            task = pooling.Task(self.proceed, self.name, next_step_delay)
            await self.controller.pool_async.add_task_async(task)
            self._debug_only('Pooled', int((time.time() - start_time) * 10) / 10)

    def start(self, start_delay=0):
        task = pooling.Task(self.proceed, self.name, 0)
        # logger.debug('sent task from parser', task)
        self.controller.pool_async.add_task(task)

    @abstractmethod
    async def body(self):
        pass


class AsyncEventParser(AsyncParserBase, parser.EventParser, ABC):

    def __init__(self, controller, name):
        AsyncParserBase.__init__(self, controller)
        parser.EventParser.__init__(self, controller, name)

    def _add_events(self, events_to_send):
        listed_events = []
        for event_name, url, date, hash_ in events_to_send:
            columns = self._new_condition[event_name, url, date, hash_]
            columns = columns.copy()
            if date is None:
                date = "null"
            date = str(date)
            venue = columns.pop('venue')
            if venue is None:
                venue = "null"
            listed_event = [
                self._db_name, event_name,
                url, venue, columns, date
            ]
            listed_events.append(listed_event)
        if listed_events:
            tasker.put(db_manager.add_parsed_events, listed_events, from_thread=self.name)

    async def run_try(self):
        await AsyncParserBase.run_try(self)

        if self.step == 0:
            tasker.put(db_manager.delete_parsed_events, self._db_name, from_thread=self.name)
        self._change_events_state()
        self.last_state = self._new_condition.copy()
        self._new_condition.clear()
        self.trigger_notifier()


class AsyncSeatsParser(AsyncParserBase, parser.SeatsParser, ABC):

    def __init__(self, controller, event_id, event_name,
                 url, date, venue, signature, scheme,
                 priority, parent, **extra):
        AsyncParserBase.__init__(self, controller)
        parser.SeatsParser.__init__(self, controller, event_id, event_name,
                                    url, date, venue, signature, scheme,
                                    priority, parent, **extra)

    async def run_try(self):
        if not self.stop.alive:
            return False

        self._debug_only('body started')
        await self.body()
        self._debug_only('body finished')

        if self.stop.alive:
            self.trigger_notifier()
            self.last_state = (self.parsed_sectors.copy(), self.parsed_dancefloors.copy(),)
            self._debug_only('releasing sectors')
            self.scheme.release_sectors(self.parsed_sectors, self.parsed_dancefloors,
                                        self.priority, self.name)
            self._debug_only('released sectors')
            self.parsed_sectors.clear()
            self.parsed_dancefloors.clear()

    async def run_except(self):
        self.parsed_sectors.clear()
        await AsyncParserBase.run_except(self)
