import asyncio
import time
from abc import ABC, abstractmethod

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
        try:
            if (time.time() - self.error_timer) >= self.max_waste_time:
                mes = ('--max_waste_time elapsed '
                       f'({self.max_waste_time} сек)--')
                self.error(mes)
                self.error_timer = time.time()
                await self.change_proxy(report=True)
                await self.before_body()
                self.slide_tab()
            await self.except_on_main()
        except Exception as error:
            self.error(f'Except on exception: {error}')
        await asyncio.sleep(1)

    async def proceed(self):
        if self.step % self.step_counter == 0 and self.step:
            self.bprint('Проход номер ' + str(self.step))
        result = await provision.async_try(self.run_try, handle_error=self.run_except,
                                           name=self.name, tries=self.max_tries, raise_exc=False)
        self.step += 1
        if result is provision.TryError and self._terminator.alive:
            await provision.async_try(self.on_many_exceptions, name=self.name, tries=1, raise_exc=False)
