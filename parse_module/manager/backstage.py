import threading
import time
from queue import Queue
from typing import Callable

from loguru import logger

from ..utils import provision, utils


class BackTasker(threading.Thread):
    def __init__(self):
        super().__init__()
        self.tasks = Queue()

    def put(self, func_: Callable, *args, **kwargs):
        if args is None:
            args = tuple()
        task = (func_, args, kwargs, False)
        self.tasks.put(task)

    def put_throttle(self, func_: Callable, first_arg, *args, from_iterable=True, **kwargs):
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
        task = (func_, args, kwargs, True)
        self.tasks.put(task)

    def _get(self):
        try:
            function, args, kwargs, throttling = self.tasks.get()
            if throttling:
                args = self._get_same_tasks(function, args)
            provision.multi_try(function, name='Backstage', args=args,
                                kwargs=kwargs, tries=1, raise_exc=False)
        except Exception as err:
            print(utils.red(f'Error getting task from the backstage: {err}'))

    def _get_same_tasks(self, function_to_find, args_original):
        first_arg = args_original[0]
        dict_ = isinstance(first_arg, dict)
        to_put_back = []
        args_collected = first_arg

        while not self.tasks.empty():
            function, args, kwargs, throttling = self.tasks.get()
            if throttling and function == function_to_find:
                first_arg = args[0]
                if dict_:
                    args_collected.update(first_arg)
                else:
                    args_collected.extend(first_arg)
            else:
                wrong_choice = (function, args, kwargs, throttling)
                to_put_back.append(wrong_choice)

        for task in to_put_back:
            self.tasks.put(task)

        return args_collected, *args_original[1:]

    def run(self):
        while True:
            self._get()


tasker = BackTasker()
tasker.start()
