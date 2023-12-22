import threading
import time
import csv
from multiprocessing.pool import ThreadPool
from collections import namedtuple, defaultdict

from sortedcontainers import SortedDict

from parse_module.utils import provision
from parse_module.utils.logger import logger
from parse_module.utils.provision import multi_try

Task = namedtuple('Task', ['to_proceed', 'parser', 'wait'])
Result = namedtuple('Result', ['scheduled_time', 'task', 'apply_result'])


class ScheduledExecutor(threading.Thread):
    def __init__(self, max_threads=20):
        super().__init__()
        self.max_threads = max_threads
        self._tasks = SortedDict()
        self._pool = ThreadPool(processes=max_threads)
        self._results = []
        self._stats = []
        self._timers = {}
        self._starting_point = time.time()
        self._stats_counter = 0
        with open('pooling_stats.csv', 'w+') as f:
            f.write('')
        self.start()

    def add(self, task: Task):
        timestamp = task.wait + time.time()
        self._tasks.setdefault(timestamp, [])
        self._tasks[timestamp].append(task)

    def _add_stats(self, scheduled_time):
        log_time = time.time()
        stat = (
            log_time - self._starting_point,
            log_time - scheduled_time,
            len(self._results),
            len(self._tasks)
        )

        self._stats_counter += 1
        self._stats.append(stat)
        if self._stats_counter % 1 == 0:
            with open('pooling_stats.csv', 'a') as f:
                writer = csv.writer(f)
                writer.writerow(stat)
                # writer.writerows(self._stats)
            self._stats.clear()

    @staticmethod
    def get_key(key):
        key = str(key)
        ppos = key.split('.')[0][-5:]
        return int(ppos)

    def _step(self):
        bisection = self._tasks.bisect_left(time.time())
        logger.debug(len(self._tasks), len(self._results), bisection, self.get_key(time.time()),
                     list(self.get_key(key) for key in self._tasks.keys())[:30])
        if not bisection:
            time.sleep(1)
        for _ in range(bisection):
            scheduled_time, tasks = self._tasks.popitem(0)
            for task in tasks:
                kwargs = {'name': task.parser, 'tries': 1, 'raise_exc': False}
                apply_result = self._pool.apply_async(provision.multi_try, [task.to_proceed], kwds=kwargs)
                result = Result(scheduled_time=scheduled_time, task=task, apply_result=apply_result)
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
            # logger.debug(-int(-time.time() - result_callback.scheduled_time))
            self._add_stats(result_callback.scheduled_time)
            if isinstance(result, Task):
                self.add(result)
        for i in to_del[::-1]:
            del self._results[i]

        to_del = []
        to_warn = []
        for timed, start_time in self._timers.items():
            if timed not in self._tasks:
                to_del.append(timed)
            else:
                block_time = 600 if 'EventParser (' in timed.task.parser else 300
                if time.time() - self._timers[timed] > block_time:
                    to_warn.append(timed.task.parser)
        for timed in to_del:
            del self._timers[timed]

        if len(to_warn) == self.max_threads:
            logger.critical('EXECUTION TOTALLY BLOCKED')
        else:
            for timed in to_warn:
                logger.warning(f'Execution blocked. Check for input() or smth blocking the execution',
                               name=timed.task.parser)

    def run(self):
        while True:
            multi_try(self._step, tries=1, raise_exc=False, name='Controller')

