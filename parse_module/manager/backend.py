import multiprocessing
import sys
import threading
import time
from collections import defaultdict
from threading import Lock

from . import pooling
from .router import SchemeRouterFrontend, wait_until
from ..connection import db_manager
from ..manager.pooling import ScheduledExecutor
from ..models import scheme
from ..utils import provision
from ..utils.logger import logger
from ..utils.provision import multi_try


class Postponer(threading.Thread):

    def __init__(self, parser_schemes: dict, locked_queues: dict):
        super().__init__()
        self.schemes = parser_schemes
        self.locked_queues = locked_queues
        self.lock = Lock()
        self.start()

    def put_task(self, method, args):
        event_id = args[0]
        queue = self.locked_queues.get(event_id, None)
        if queue is None:
            self._process_task(method, args)
        else:
            # Scheme was not created
            try:
                self.lock.acquire()
                task = [method, args]
                queue.append(task)
            finally:
                self.lock.release()

    def _process_task(self, method, args, raise_exc=True):
        event_id = args[0]
        thread_name = self.schemes[event_id].name
        return multi_try(method, args=args, name=thread_name, tries=3, raise_exc=raise_exc)

    def _step(self):
        try:
            self.lock.acquire()
            event_ids_waiting_to_proceed = list(self.locked_queues.keys())
        finally:
            self.lock.release()

        processed = 0
        for event_id in event_ids_waiting_to_proceed:
            if event_id not in self.schemes:
                continue
            try:
                self.lock.acquire()
                queue = self.locked_queues.pop(event_id)
            finally:
                self.lock.release()
            for method, args in queue:
                self._process_task(method, args, raise_exc=False)
                processed += 1

        return processed

    def run(self):
        while True:
            processed = multi_try(self._step, tries=1, raise_exc=False, name='Controller')
            if processed is not provision.TryError and not processed:
                time.sleep(3)
            else:
                time.sleep(0.2)


class SchemeRouterBackend:

    def __init__(self, conn: multiprocessing.connection.Connection):
        self.parser_schemes = {}
        self.group_schemes = {}
        self.event_lockers = defaultdict(Lock)
        self.conn = conn
        self._pool = ScheduledExecutor(stats='scheme_router_stats.csv', max_threads=5)
        self._locked_queues = {}
        self._postponer = Postponer(self.parser_schemes, self._locked_queues)

    def _get_group_scheme(self, scheme_id):
        if scheme_id not in self.group_schemes:
            new_scheme = scheme.Scheme(scheme_id)
            add_result = new_scheme.setup_sectors(wait_mode=True)
            if add_result is False:
                if not wait_until(lambda: scheme_id in self.group_schemes):
                    logger.error(f'Scheme distribution corrupted! Backend. Scheme id {scheme_id}',
                                 name='Controller')
                    self.group_schemes[scheme_id] = new_scheme
            else:
                self.group_schemes[scheme_id] = new_scheme
        return self.group_schemes[scheme_id]

    def create_scheme(self, event_id, scheme_id, name):
        try:
            self._postponer.lock.acquire()
            self._locked_queues[event_id] = []
        finally:
            self._postponer.lock.release()
            task = pooling.Task(self._create_scheme, 'Controller', args=(event_id, scheme_id, name,))
            self._pool.add_task(task)

    def _create_scheme(self, event_id, scheme_id, name):
        lock = self.event_lockers[event_id]
        try:
            lock.acquire()
            if event_id not in self.parser_schemes:
                group_scheme = self._get_group_scheme(scheme_id)
                new_scheme = scheme.ParserScheme(group_scheme, event_id, name)
                self.parser_schemes[event_id] = new_scheme
        finally:
            lock.release()

    def bind(self, event_id, priority, margin_func):
        self._postponer.put_task(self._bind, (event_id, priority, margin_func,))

    def _bind(self, event_id, priority, margin_func):
        lock = self.event_lockers[event_id]
        try:
            lock.acquire()
            scheme = self.parser_schemes[event_id]
            scheme.bind(priority, margin_func,)
        finally:
            lock.release()

    def unbind(self, event_id, priority):
        self._postponer.put_task(self._unbind, (event_id, priority,))

    def _unbind(self, event_id, priority):
        lock = self.event_lockers[event_id]
        try:
            lock.acquire()
            scheme = self.parser_schemes[event_id]
            scheme.unbind(priority)
        finally:
            lock.release()

    def release_sectors(self, *args):
        self._postponer.put_task(self._release_sectors, args)

    def _release_sectors(self, event_id, *args):
        scheme = self.parser_schemes[event_id]
        scheme.release_sectors(*args)

    def run(self) -> None:
        logger.info('Backend started', name='Controller')
        while True:
            got_data = multi_try(self.conn.recv, tries=20, name='Controller',
                                 raise_exc=False)
            if got_data is provision.TryError:
                sys.exit()
            else:
                command, args = got_data
            method = getattr(self, command)
            provision.just_try(method, args=args, name='Controller')


def change_connection(login, password):
    while not db_manager.connection:
        time.sleep(0.1)
    db_manager.connection.close()
    db_manager.user = login
    db_manager.password = password
    db_manager.connect_db()


def process_function(inner_conn):
    change_connection('parsing_main', 'cnwhUCJMIIrF2g')
    backend_ = SchemeRouterBackend(inner_conn)
    backend_.run()


def get_router():
    outer_conn, inner_conn = multiprocessing.Pipe()
    process = multiprocessing.Process(target=process_function, args=(inner_conn,))
    process.start()
    return SchemeRouterFrontend(outer_conn), process
