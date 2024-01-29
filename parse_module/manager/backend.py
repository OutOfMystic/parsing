import multiprocessing
import sys
import threading
import time
from collections import defaultdict
from multiprocessing.connection import Connection
from threading import Lock

from . import pooling
from .router import SchemeRouterFrontend, wait_until
from .. import connection
from ..connection import db_manager
from ..connection.database import TableDict
from ..manager.pooling import ScheduledExecutor
from ..models import scheme
from ..models.ai_nlp import venue, solve
from ..models.ai_nlp.collect import cross_subject_object
from ..utils import provision
from ..utils.logger import logger
from ..utils.provision import multi_try

send_lock = threading.Lock()


def send_threadsafe(self, data):
    send_lock.acquire()
    try:
        Connection.send(self, data)
    finally:
        send_lock.release()


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
            processed = multi_try(self._step, tries=1, raise_exc=False, name='Controller (Backend)')
            if processed is not provision.TryError and not processed:
                time.sleep(3)
            else:
                time.sleep(0.2)


class AISolver:
    def __init__(self):
        self._table_sites = TableDict(db_manager.get_site_names)
        self._already_warned_on_collect = set()
        self.solver, self._cache_dict = solve.get_model_and_cache()
        self.venues = venue.VenueAliases(self.solver)

    def get_connections(self, subjects: list, indicators: set, parsing_types: dict, parsed_events: list):
        connections = []

        labels = (self._table_sites, parsing_types, self._already_warned_on_collect,)
        types_on_site = db_manager.get_site_parsers()
        for connection in cross_subject_object(subjects, parsed_events, self.venues,
                                               self.solver, self._cache_dict,
                                               types_on_site, labels=labels):
            if connection['indicator'] in indicators:
                continue
            connections.append(connection)
        return connections


class SchemeRouterBackend:

    def __init__(self, conn: multiprocessing.connection.Connection):
        self.parser_schemes = {}
        self.group_schemes = {}
        self.event_lockers = defaultdict(Lock)
        self.conn = conn
        self._pool = ScheduledExecutor(stats='scheme_router_stats.csv', max_threads=5)
        self._locked_queues = {}
        self.ai_workspace = AISolver()
        self._postponer = Postponer(self.parser_schemes, self._locked_queues)

    def _get_group_scheme(self, scheme_id):
        if scheme_id not in self.group_schemes:
            new_scheme = scheme.Scheme(scheme_id)
            add_result = new_scheme.setup_sectors(wait_mode=True)
            if add_result is False:
                if not wait_until(lambda: scheme_id in self.group_schemes):
                    logger.error(f'Scheme distribution corrupted! Backend. Scheme id {scheme_id}',
                                 name='Controller (Backend)')
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
            task = pooling.Task(self._create_scheme, 'Controller (Backend)', args=(event_id, scheme_id, name,))
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

    def get_connections(self, *args):
        provision.threading_try(self._get_connections,
                                args=args,
                                name='Controller (Backend)',
                                tries=1)

    def _get_connections(self, subjects, indicators, parsing_types, parsed_events):
        solutions = self.ai_workspace.get_connections(subjects, indicators, parsing_types, parsed_events)
        self.conn.send(solutions)

    def run(self) -> None:
        self.conn.send('Started')
        logger.info('Backend started', name='Controller (Backend)')
        while True:
            got_data = multi_try(self.conn.recv, tries=20, name='Controller (Backend)',
                                 raise_exc=False)
            if got_data is provision.TryError:
                sys.exit()
            else:
                command, args = got_data
            method = getattr(self, command)
            # logger.debug(method, args, name='Backend')
            provision.just_try(method, args=args, name='Controller (Backend)')


def change_connection(ip, port, login):
    while not db_manager.connection:
        time.sleep(0.1)
    db_manager.connection.close()
    db_manager.user = login
    db_manager.host = ip
    db_manager.port = port
    threading.Thread(target=db_manager.connect_db).start()


def process_starting(inner_conn, ip, port, login):
    change_connection(ip, port, login)
    backend_ = SchemeRouterBackend(inner_conn)
    backend_.run()


def get_router(local_db=False):
    outer_conn, inner_conn = multiprocessing.Pipe()
    outer_conn.send = send_threadsafe.__get__(outer_conn)
    logger.info('Backend initing...', name='Controller (Backend)')
    if local_db:
        args = (inner_conn, '127.0.0.1', '5432', 'django_project',)
    else:
        args = (inner_conn, '193.178.170.180', '5432', 'django_project',)
    process = multiprocessing.Process(target=process_starting,
                                      args=args)
    process.start()
    router = SchemeRouterFrontend(outer_conn)
    router.conn.recv()
    return router, process
