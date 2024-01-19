import asyncio
import platform
import time
from asyncio import AbstractEventLoop
from dataclasses import dataclass
from collections import namedtuple
from typing import Callable, Iterable

from sortedcontainers import SortedDict

from ..console.base import print_cols
from ..utils import provision, utils
from ..utils.logger import logger

Task = namedtuple('Task', ['to_proceed', 'from_thread', 'wait'])
Result = namedtuple('Result', ['scheduled_time', 'from_thread', 'apply_result'])


@dataclass
class Task:
    to_proceed: Callable
    from_thread: str
    wait: int = 0
    args: Iterable = None


class ScheduledExecutor:
    def __init__(self, loop: AbstractEventLoop, max_connects=100, debug=False):
        super().__init__()
        self.frst = set()
        self.debug = debug
        self._loop = loop
        self._tasks = SortedDict()
        self._results = []
        self._stats = []
        self._timers = {}
        self._starting_point = time.time()
        self._stats_counter = 0
        self._last_demand_check = time.time()
        self._semaphore = asyncio.Semaphore(max_connects)
        self._is_win32 = platform.system() == 'Windows'
        self.in_process = 0
        asyncio.run_coroutine_threadsafe(self.run_async(), loop)

    def add_task(self, task: Task):
        # coroutine = self.add_task_async(task)
        # asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        timestamp = task.wait + time.time()
        self._tasks.setdefault(timestamp, [task])
        logger.debug('got task to pooling', task.from_thread)

    async def add_task_async(self, task: Task):
        # logger.debug('got async task to pooling', task.from_thread)
        timestamp = task.wait + time.time()
        self._tasks.setdefault(timestamp, [task])

    def high_demand_check(self):
        awaiting_lower_limit = 1 if self.debug else 50
        if time.time() - self._last_demand_check > 5 or self.debug:
            self._last_demand_check = time.time()
            if self.in_process >= awaiting_lower_limit:
                stat = f'High demand. Tasks in process: {self.in_process}, ' \
                       f'Scheduled: {len(self._tasks)}'
                logger.info(stat, name='Controller (Backend)')

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

    @staticmethod
    def handle_result(result, from_thread):
        if isinstance(result, BaseException):
            str_exception = str(result).split('\n')[0]
            error = f'({type(result).__name__}) {str_exception}'
            logger.error(error, name=from_thread)

    async def _step(self):
        raise RuntimeError()
        bisection = self._tasks.bisect_left(time.time())
        if not bisection:
            await asyncio.sleep(0.2)
        tasks_to_run = []
        for _ in range(bisection):
            time_and_tasks = self._tasks.popitem(0)
            tasks_to_run.append(time_and_tasks)
            self.in_process += len(time_and_tasks[1])

        for scheduled_time, tasks in tasks_to_run:
            for task in tasks:
                coroutine = self.create_coroutine_from_task(task)
                """args = task.args if task.args else []
                coroutine = task.to_proceed(*args)"""

                await self._semaphore.acquire()
                apply_result = asyncio.create_task(coroutine)
                # name = task.to_proceed.__name__ if hasattr(task.to_proceed, '__name__') else str(task.to_proceed)
                apply_result.set_name(task.from_thread)
                result_callback = Result(scheduled_time=scheduled_time,
                                         from_thread=task.from_thread,
                                         apply_result=apply_result)
                self.high_demand_check()
                # logger.debug(task.to_proceed, name=task.from_thread)
                self._results.append(result_callback)
                
                frst = 'NEW' if task.from_thread not in self.frst else 'OLD'
                amount = len(self.frst) if task.from_thread not in self.frst else len(self._results)
                self.frst.add(task.from_thread)
                logger.debug('proceeding', frst, amount, task.from_thread)

        to_del = []
        for i, result_callback in enumerate(self._results):
            if result_callback not in self._timers:
                self._timers[result_callback] = time.time()
            if result_callback.apply_result.done():
                self.handle_result(result_callback.apply_result.result, result_callback.from_thread)
                to_del.append(i)
                # logger.debug('result', int(time.time() - result_callback.scheduled_time), 'sec',
                #              name=result_callback.from_thread)
        for i in to_del[::-1]:
            del self._results[i]
            self.in_process -= 1

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
        await asyncio.sleep(0.1)

    async def run_async(self):
        while True:
            await provision.async_just_try(self._step, name='Controller')

    def create_coroutine_from_task(self, task):
        return provision.async_just_try(task.to_proceed,
                                        name=task.from_thread,
                                        args=task.args,
                                        semaphore=self._semaphore)


