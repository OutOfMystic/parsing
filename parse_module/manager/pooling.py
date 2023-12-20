import threading
import time
import csv
from multiprocessing.pool import ThreadPool
from collections import namedtuple

from sortedcontainers import SortedDict

from parse_module.utils import provision
from parse_module.utils.logger import logger

Task = namedtuple('Task', ['to_proceed', 'parser', 'wait'])


class ScheduledExecutor(threading.Thread):
    def __init__(self, max_threads=20):
        super().__init__()
        self._tasks = SortedDict()
        self._pool = ThreadPool(processes=max_threads)
        self._results = []
        self._stats = []
        self._starting_point = time.time()
        self._stats_counter = 0
        self.start()

    def add(self, task: Task):
        timestamp = task.wait + time.time()
        self._tasks.setdefault(-timestamp, [])
        self._tasks[-timestamp].append(task)

    def _add_stats(self, commit_time):
        log_time = time.time()
        stat = (
            log_time - self._starting_point,
            log_time + commit_time,
            len(self._results),
        )

        self._stats_counter += 1
        self._stats.append(stat)
        if self._stats_counter % 200 == 0:
            with open('pooling_stats.csv', 'a') as f:
                writer = csv.writer(f)
                writer.writerows(self._stats)
            self._stats.clear()

    def _step(self):
        bisection = self._tasks.bisect_left(-time.time())
        sliced = len(self._tasks) - bisection
        if not sliced:
            time.sleep(0.2)
            return
        for _ in range(sliced):
            commit_time, tasks = self._tasks.popitem()
            for task in tasks:
                kwargs = {'name': task.parser, 'tries': 1, 'raise_exc': False}
                apply_result = self._pool.apply_async(provision.multi_try, [task.to_proceed], kwds=kwargs)
                self._add_stats(commit_time)
                self._results.append(apply_result)

        to_del = []
        for i, apply_result in enumerate(self._results):
            if not apply_result.ready():
                continue
            to_del.append(i)
            result = apply_result.get()
            if isinstance(result, Task):
                self.add(result)
        for i in to_del[::-1]:
            del self._results[i]

    def run(self):
        while True:
            self._step()

