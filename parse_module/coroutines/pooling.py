import asyncio
import threading
import time
from dataclasses import dataclass
from collections import namedtuple
from typing import Callable, Iterable

from sortedcontainers import SortedDict

from parse_module.console.base import print_cols
from parse_module.utils import provision, utils
from parse_module.utils.logger import logger

Task = namedtuple('Task', ['to_proceed', 'from_thread', 'wait'])
Result = namedtuple('Result', ['scheduled_time', 'from_thread', 'apply_result'])


@dataclass
class Task:
    to_proceed: Callable
    from_thread: str
    wait: int = 0
    args: Iterable = None


class ScheduledExecutor(threading.Thread):
    def __init__(self):
        super().__init__()
        self._tasks = SortedDict()
        self._results = []
        self._stats = []
        self._timers = {}
        self._starting_point = time.time()
        self._stats_counter = 0
        self.start()

    def add_task(self, task: Task):
        timestamp = task.wait + time.time()
        self._tasks.setdefault(timestamp, [task])

    def inspect_queue(self):
        log_time = time.time()
        stat = f'Log time: {log_time - self._starting_point:.1f}, ' \
               f'In process: {len(self._results)}, ' \
               f'Scheduled: {len(self._tasks)}'
        tasks = self._tasks.copy()
        to_print = []
        for task_time, tasks in tasks.items():
            time_to_task = task_time - time.time()
            formed_time = int(time_to_task * 10) / 10
            tasks_ = tasks.copy()
            for task in tasks_:
                row = [utils.green(formed_time), utils.colorize(task.from_thread, utils.Fore.LIGHTCYAN_EX)]
                to_print.append(row)
        print_cols(to_print[::-1])
        utils.blueprint(stat)

    @staticmethod
    def get_key(key):
        key = str(key)
        ppos = key.split('.')[0][-5:]
        return int(ppos)

    async def _step(self):
        bisection = self._tasks.bisect_left(time.time())
        if not bisection:
            await asyncio.sleep(0.2)
        for _ in range(bisection):
            scheduled_time, tasks = self._tasks.popitem(0)
            for task in tasks:
                coroutine = provision.async_try(task.to_proceed,
                                                name=task.from_thread,
                                                args=task.args,
                                                tries=1,
                                                raise_exc=False)
                apply_result = asyncio.create_task(coroutine)
                result_callback = Result(scheduled_time=scheduled_time,
                                         from_thread=task.from_thread,
                                         apply_result=apply_result)
                # logger.debug(task.to_proceed, name=task.from_thread)
                self._results.append(result_callback)

        to_del = []
        for i, result_callback in enumerate(self._results):
            if result_callback not in self._timers:
                self._timers[result_callback] = time.time()
            if result_callback.apply_result.done():
                provision.just_try(result_callback.apply_result.result,
                                   name=result_callback.from_thread)
                to_del.append(i)
                # logger.debug('result', int(time.time() - result_callback.scheduled_time), 'sec',
                #              name=result_callback.from_thread)
        for i in to_del[::-1]:
            del self._results[i]

        to_del = []
        to_warn = []
        for timed, start_time in self._timers.items():
            # if coroutjne already proceeded
            if timed not in self._results:
                to_del.append(timed)
            else:
                block_time = 1200
                if time.time() - self._timers[timed] > block_time:
                    to_warn.append(timed.from_thread)
        for timed in to_del:
            del self._timers[timed]

        for thread_name in to_warn:
            logger.warning(f'Too long execution. Check for input(), '
                           f'time.sleeps or smth blocking the execution',
                           name=thread_name)

    async def run_async(self):
        while True:
            await provision.async_just_try(self._step, name='Controller')

    def run(self):
        # Инициализируем и запускаем новый event loop в этом потоке
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.run_async())
        loop.close()
