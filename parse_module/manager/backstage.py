import threading
import time
from queue import Queue
from typing import Callable

from ..utils import provision, utils


class BackTasker(threading.Thread):
    def __init__(self):
        super().__init__()
        self.tasks = Queue()

    def put(self, func_: Callable, args=None):
        if args is None:
            args = tuple()
        task = (func_, args, False)
        self.tasks.put(task)

    def throttle(self, func_: Callable, arg, from_iterable=False):
        if not from_iterable:
            arg = [arg]
        task = (func_, arg, True)
        self.tasks.put(task)

    def _get(self):
        try:
            function, args, throttling = self.tasks.get()
            if throttling:
                args = self._get_same_tasks(function)
            provision.multi_try(function, name='Backstage', args=args, tries=1,
                                raise_exc=False)
        except Exception as err:
            print(utils.red(f'Error getting task from backstage: {err}'))

    def _get_same_tasks(self, function_to_find):
        args = []
        to_return = []
        while not self.tasks.empty():
            function, args, throttling = self.tasks.get()
            if throttling and function == function_to_find:
                args.extend(args)
            else:
                wrong_choice = (function, args, throttling)
                to_return.append(wrong_choice)
        for task in to_return:
            self.tasks.put(task)
        return args

    def run(self):
        while True:
            self._get()


class ThrottlingTasker(threading.Thread):

    def


tasker = BackTasker()
tasker.start()
