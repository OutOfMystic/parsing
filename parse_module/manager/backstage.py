import threading
import time
from queue import Queue

from ..utils import provision, utils
from .proxy import check


class BackTasker(threading.Thread):
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.locker = threading.Lock()

    def put(self, *task):
        self.locker.acquire()
        try:
            self.tasks.append(task)
        except Exception as err:
            raise err
        finally:
            self.locker.release()

    def get(self):
        self.locker.acquire()
        try:
            if not self.tasks:
                time.sleep(0.25)
                return True
            function, args = self.tasks.pop(0)
        except Exception as err:
            print(utils.red(f'Error getting task from backstage: {err}'))
        else:
            provision.multi_try(function, name='Backstage', args=args)
        finally:
            self.locker.release()

    def run(self):
        while True:
            self.get()


def check_proxies(proxies, url, callback, method='get'):
    check.check_proxies(proxies, url, callback, method=method)


tasker = BackTasker()
tasker.start()
quests = Queue()