import multiprocessing
import threading
import time
from collections import defaultdict
from multiprocessing import Lock

from . import scheme
from ..connection import db_manager
from ..manager.pooling import ScheduledExecutor, Task
from ..utils import provision
from ..utils.logger import logger
from ..utils.provision import multi_try


def wait_until(condition, timeout=60, step=0.1):
    start_time = time.time()
    while not condition():
        if (time.time() - start_time) > timeout:
            return False
        time.sleep(step)
    return True


class SchemeRouterFrontend:

    def __init__(self, conn: multiprocessing.connection.Connection):
        self.conn = conn
        self.group_schemes = {}
        self.parser_schemes = {}

    def get_parser_scheme(self, event_id, scheme_id, name='Controller'):
        if event_id in self.parser_schemes:
            return self.parser_schemes[event_id]
        group_scheme = self._get_group_scheme(scheme_id)
        operation = ['create_scheme', [event_id, scheme_id, name]]
        self.conn.send(operation)
        new_scheme = SchemeProxy(group_scheme, self.conn, event_id)
        self.parser_schemes[event_id] = new_scheme
        return new_scheme

    def _get_group_scheme(self, scheme_id):
        if scheme_id not in self.group_schemes:
            new_scheme = scheme.Scheme(scheme_id)
            add_result = new_scheme.get_scheme()
            if add_result is False:
                if not wait_until(lambda: scheme_id in self.group_schemes):
                    logger.critical(f'Scheme distribution corrupted! {scheme_id}', name='Controller')
                    self.group_schemes[scheme_id] = new_scheme
            else:
                self.group_schemes[scheme_id] = new_scheme
        return self.group_schemes[scheme_id]


class Postponer(threading.Thread):

    def __init__(self, parser_schemes, locked_queues):
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
            task = [method, args]
            queue.append(task)

    def _process_task(self, method, args):
        event_id = args[0]
        thread_name = self.schemes[event_id].name
        multi_try(method, args=args, name=thread_name, tries=3)

    def _step(self):
        try:
            self.lock.acquire()
            queues = self.locked_queues.copy()
        finally:
            self.lock.release()

        processed = 0
        for event_id in queues:
            if event_id not in self.schemes:
                continue
            queue = queues.popitem(event_id)
            for method, args in queue:
                self._process_task(method, args)
                processed += 1
        return processed

    def run(self):
        while True:
            processed = multi_try(self._step, tries=1, raise_exc=False, name='Controller')
            if processed is not provision.TryError and not processed:
                time.sleep(3)
            else:
                time.sleep(0.2)


class SchemeRouterBackend(multiprocessing.Process):

    def __init__(self, conn: multiprocessing.connection.Connection):
        super().__init__()
        self.parser_schemes = {}
        self.group_schemes = {}
        self.event_lockers = defaultdict(Lock)
        self.conn = conn
        self._pool = ScheduledExecutor()
        self._locked_queues = {}
        self._postponer = Postponer(self.parser_schemes, self._locked_queues)

    def create_scheme(self, event_id, scheme_id, name):
        try:
            self._postponer.lock.acquire()
            self._locked_queues[event_id] = []
        finally:
            self._postponer.lock.release()
            task = Task(self._create_scheme, 'Controller', args=(event_id, scheme_id, name,))
            self._pool.add(task)

    def _create_scheme(self, event_id, scheme_id, name):
        lock = self.event_lockers[event_id]
        try:
            lock.acquire()
            if event_id not in self.parser_schemes:
                group_scheme = self._get_group_scheme(scheme_id)
                new_scheme = scheme.ParserScheme(group_scheme, event_id, name)
                self.parser_schemes[event_id] = new_scheme
            got_scheme = self.parser_schemes[event_id]
            return got_scheme
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

    def unbind(self, event_id, priority, force):
        self._postponer.put_task(self._unbind, (event_id, priority, force,))

    def _unbind(self, event_id, priority):
        lock = self.event_lockers[event_id]
        try:
            lock.acquire()
            scheme = self.parser_schemes[event_id]
            scheme.unbind(priority)
        finally:
            lock.release()

    def release_sectors(self, event_id, *args):
        scheme = self.parser_schemes[event_id]
        scheme.release_sectors(*args)

    def _get_group_scheme(self, scheme_id):
        if scheme_id not in self.group_schemes:
            new_scheme = scheme.Scheme(scheme_id)
            add_result = new_scheme.get_scheme()
            if add_result is False:
                if not wait_until(lambda: scheme_id in self.group_schemes):
                    logger.critical(f'Scheme distribution corrupted! {scheme_id}', name='Controller')
                    self.group_schemes[scheme_id] = new_scheme
            else:
                self.group_schemes[scheme_id] = new_scheme
        return self.group_schemes[scheme_id]

    def run(self) -> None:
        while True:
            command, args = self.conn.recv()
            method = getattr(self, command)
            method(args)


class GroupRouter:

    def __init__(self, groups):
        self.groups = groups
        self._assignments = {}

    def route_group(self, url, event_id):
        scheme_id = db_manager.get_scheme_id(event_id)
        if scheme_id in self._assignments:
            return self._assignments[scheme_id]
        groups = [group for group in self.groups if group.url_filter(url)]
        self._assign(scheme_id, groups)
        return self._assignments[scheme_id]

    """def route_scheme(self, url, event_id, scheme_id):
        group = self.route_group(url, event_id)
        return group.router.get_parser_scheme(event_id, scheme_id)"""

    def _assign(self, scheme_id, groups):
        self._assignments[scheme_id] = groups[0]


class SchemeProxy:

    def __init__(self, scheme, conn, event_id):
        self.conn = conn
        self.event_id = event_id
        self.scheme_id = scheme.scheme_id
        self.name = scheme.name
        self.dancefloors = (sector.lower() for sector in scheme.dancefloors)
        self.sector_names = scheme.sector_names
        self.sector_data = scheme.sector_data
        self._margins = {}

    def bind(self, priority, margin_func):
        operation = ['bind', [self.event_id, priority, margin_func]]
        self._margins[priority] = margin_func
        self.conn.send(operation)

    def unbind(self, *args):
        if len(args) == 2:
            priority, force = args
            if force:
                if priority not in self._margins:
                    return
        else:
            priority = args[0]
        operation = ['unbind', [self.event_id, [priority]]]
        del self._margins[args[0]]
        self.conn.send(operation)

    def release_sectors(self, parsed_sectors, parsed_dancefloors,
                        cur_priority, from_thread):
        operation = ['release_sectors', [self.event_id, parsed_sectors, parsed_dancefloors,
                                         cur_priority, from_thread]]
        self.conn.send(operation)

    def restore_margin(self, priority):
        return self._margins[priority]


def get_router():
    outer_conn, inner_conn = multiprocessing.Pipe()
    process = SchemeRouterBackend(inner_conn)
    process.start()
    return SchemeRouterFrontend(outer_conn)
