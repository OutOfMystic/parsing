import asyncio
import time
from abc import ABC, abstractmethod
from typing import Callable, Iterable

from ..manager.core import Bot
from ..utils import provision
from ..utils.logger import logger


class CoroutineBot(Bot, ABC):

    def __init__(self, proxy=None):
        Bot.__init__(self, proxy=proxy, skip_postinit=True)

    async def inthread_init(self):
        if self.driver_source:
            raise RuntimeError("Coroutine bot can't use selenium or hrenium")
        await self.before_body()
        self.fully_inited = True

    async def except_on_main(self):
        pass

    async def except_on_wait(self):
        pass

    async def on_many_exceptions(self):
        pass

    async def change_proxy(self, report=False):
        pass

    async def before_body(self):
        pass

    @abstractmethod
    async def body(self, *args, **kwargs):
        pass

    async def run_try(self):
        if not self._terminator.alive:
            return False
        await self.body()
        # logger.debug(f'Step ({self.name}) done')
        if not self._terminator.alive:
            return False

    async def run_except(self):
        async def on_exception():
            if (time.time() - self._error_timer) >= self.max_waste_time:
                mes = ('--max_waste_time elapsed '
                       f'({self.max_waste_time} сек)--')
                self.error(mes)
                self.error_timer = time.time()
                await self.change_proxy(report=True)
            await self.except_on_main()
        await provision.async_just_try(on_exception, name=self.name)
        await asyncio.sleep(1)

    async def proceed(self):
        if self.step % self.step_counter == 0 and self.step:
            self.bprint('Проход номер ' + str(self.step))
        result = await provision.async_try(self.run_try, handle_error=self.run_except,
                                           name=self.name, tries=self.max_tries, raise_exc=False)
        self.step += 1
        if result is provision.TryError and self._terminator.alive:
            await provision.async_try(self.on_many_exceptions, name=self.name, tries=1, raise_exc=False)

    def multi_try(self,
                  to_try: Callable,
                  handle_error: Callable = None,
                  tries=3,
                  raise_exc=True,
                  args: Iterable = None,
                  kwargs: dict = None,
                  print_errors=True):
        """
        Try to execute smth ``tries`` times sequentially.
        If all attempts are unsuccessful and ``raise_exc``
        is True, raise an exception. ``handle_error`` is called
        every time attempt was not succeeded.

        Args:
            to_try: main function
            handle_error: called if attempt was not succeeded
            tries: number of attempts to execute ``to_try``
            args: arguments sent to ``to_try``
            kwargs: keyword arguments sent to ``to_try``
            raise_exc: raise exception or not after all
            print_errors: log errors on each try

        Returns: value from a last successful attempt.
        If all attempts fail, exception is raised or
        provision.TryError is returned.
        """
        return provision.async_try(to_try,
                                   name=self.name,
                                   handle_error=handle_error,
                                   tries=tries,
                                   args=args,
                                   kwargs=kwargs,
                                   raise_exc=raise_exc,
                                   print_errors=print_errors)

