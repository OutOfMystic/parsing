import asyncio
import threading
import time
import csv
from multiprocessing.pool import ThreadPool
from dataclasses import dataclass
from collections import namedtuple
from typing import Callable, Iterable

from sortedcontainers import SortedDict

from parse_module.console.base import print_cols
from parse_module.utils import provision, utils
from parse_module.utils.logger import logger
from parse_module.utils.provision import multi_try

Task = namedtuple('Task', ['to_proceed', 'from_thread', 'wait'])
Result = namedtuple('Result', ['scheduled_time', 'from_thread', 'apply_result'])


@dataclass
class Task:
    to_proceed: Callable
    from_thread: str
    wait: int = 0
    args: Iterable = None


class ScheduledExecutor(threading.Thread):
    def __init__(self, max_threads=40, stats='pooling_stats.csv'):
        super().__init__()
        self.max_threads = max_threads
        self.stats = stats
        self._tasks = SortedDict()
        self._pool = ThreadPool(processes=max_threads)
        self._results = []
        self._stats = []
        self._timers = {}
        self._starting_point = time.time()
        self._stats_counter = 0
        if self.stats:
            with open(stats, 'w+') as f:
                f.write('')
        self.start()

    def add_task(self, task: Task):
        timestamp = task.wait + time.time()
        self._tasks.setdefault(timestamp, [])
        self._tasks[timestamp].append(task)

    def _add_stats(self, scheduled_time):
        if not self.stats:
            return
        log_time = time.time()
        stat = (
            log_time - self._starting_point,
            log_time - scheduled_time,
            len(self._results),
            len(self._tasks)
        )

        self._stats_counter += 1
        self._stats.append(stat)
        if self._stats_counter % 20 == 0:
            with open(self.stats, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(stat)
                # writer.writerows(self._stats)
            self._stats.clear()

    def inspect_queue(self):
        log_time = time.time()
        stat = f'Log time: {log_time - self._starting_point:.1f}, ' \
               f'In process: {len(self._results)}/{self.max_threads}, ' \
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
            await asyncio.sleep(1)


    def _step(self):
        bisection = self._tasks.bisect_left(time.time())
        if not bisection:
            time.sleep(1)
        for _ in range(bisection):
            scheduled_time, tasks = self._tasks.popitem(0)
            for task in tasks:
                kwargs = {'args': task.args, 'name': task.from_thread, 'tries': 1, 'raise_exc': False}
                apply_result = self._pool.apply_async(provision.multi_try, [task.to_proceed], kwds=kwargs)
                result = Result(scheduled_time=scheduled_time,
                                from_thread=task.from_thread,
                                apply_result=apply_result)
                # logger.debug(task.to_proceed, name=task.from_thread)
                self._results.append(result)

        to_del = []
        for i, result_callback in enumerate(self._results):
            if i < self.max_threads:
                if result_callback not in self._timers:
                    self._timers[result_callback] = time.time()
            if not result_callback.apply_result.ready():
                continue
            result = result_callback.apply_result.get()
            to_del.append(i)
            # logger.debug('result', int(time.time() - result_callback.scheduled_time), 'sec',
            #              name=result_callback.from_thread)
            self._add_stats(result_callback.scheduled_time)
            if isinstance(result, Task):
                self.add_task(result)
        for i in to_del[::-1]:
            del self._results[i]

        to_del = []
        to_warn = []
        for timed, start_time in self._timers.items():
            if timed not in self._results:
                to_del.append(timed)
            else:
                block_time = 600 if 'EventParser (' in timed.from_thread else 300
                if time.time() - self._timers[timed] > block_time:
                    to_warn.append(timed.from_thread)
        for timed in to_del:
            del self._timers[timed]

        if len(to_warn) == self.max_threads:
            logger.critical('EXECUTION IS TOTALLY BLOCKED', name='Controller')
        else:
            for thread_name in to_warn:
                logger.error(f'Execution blocked. Check for input() or smth blocking the execution',
                             name=thread_name)

    def run(self):
        while True:
            provision.just_try(self._step, name='Controller')

