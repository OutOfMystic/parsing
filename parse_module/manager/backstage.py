import threading
from datetime import datetime
from queue import Queue
from typing import Callable
from threading import Lock

from ..console.base import print_cols
from ..utils import provision
from .controller import logger


class Task:
    def __init__(self,
                 function,
                 args,
                 kwargs,
                 throttling=False,
                 from_thread='Main'):
        self.timestamp = datetime.now().isoformat()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.throttling = throttling
        self.from_thread = from_thread


class BackTasker(threading.Thread):
    def __init__(self):
        super().__init__()
        self._lock = Lock()
        self.tasks = Queue()

    def put(self, func_: Callable, *args, from_thread='Main', **kwargs):
        if args is None:
            args = tuple()
        task = Task(func_, args, kwargs, from_thread=from_thread)
        self.tasks.put(task)

    def put_throttle(self, func_: Callable, first_arg, *args,
                     from_iterable=True, from_thread='Main', **kwargs):
        """
        If from_iterable is True, you can put ``dict`` or ``list``.
        Otherwise, you can put an only item

        Only first_arg is stacked for throttling!
        """
        args = list(args)
        if from_iterable:
            assert hasattr(first_arg, '__iter__'), '``first_arg`` should be iterable'
        if not from_iterable:
            first_arg = [first_arg]
        args.insert(0, first_arg)
        task = Task(func_, args, kwargs, throttling=True, from_thread=from_thread)
        try:
            self._lock.acquire()
            self.tasks.put(task)
        finally:
            self._lock.release()

    def _get(self):
        try:
            task = self.tasks.get()
            args = task.args
            if task.throttling:
                args = self._get_same_tasks(task.function, task.args, task.timestamp)
            provision.multi_try(task.function, name=task.from_thread, args=args,
                                kwargs=task.kwargs, tries=1, raise_exc=False)
        except Exception as err:
            logger.error(f'Error getting task from the backstage: {err}', name='Controller')

    def _get_same_tasks(self, function_to_find, args_original, timestamp_original):
        first_arg = args_original[0]
        dict_ = isinstance(first_arg, dict)
        to_put_back = []
        args_collected = [(first_arg, timestamp_original,)]

        try:
            self._lock.acquire()
            while not self.tasks.empty():
                task = self.tasks.get()
                if task.throttling and task.function == function_to_find:
                    first_arg_and_timestamp = (task.args[0], task.timestamp,)
                    args_collected.append(first_arg_and_timestamp)
                else:
                    to_put_back.append(task)

            to_put_back.sort(key=lambda item: item.timestamp)
            for task in to_put_back:
                self.tasks.put(task)
        finally:
            self._lock.release()

        args_collected.sort(key=lambda item: item[1])
        if dict_:
            ordered_args = {}
            for args, timestamp in args_collected:
                ordered_args.update(args)
        else:
            ordered_args = []
            for args, timestamp in args_collected:
                ordered_args.extend(args)

        return ordered_args, *args_original[1:]

    def inspect_queue(self):
        to_print = []
        to_put_back = []

        try:
            self._lock.acquire()
            while not self.tasks.empty():
                task = self.tasks.get()
                row = [str(task.timestamp), len(task.args), str(task.kwargs), str(task.throttling)]
                to_print.append(row)
                to_put_back.append(task)

            to_put_back.sort(key=lambda item: item.timestamp)
            for task in to_put_back:
                self.tasks.put(task)
        finally:
            self._lock.release()
        print_cols(to_print)

    def run(self):
        while True:
            self._get()


tasker = BackTasker()
tasker.start()
