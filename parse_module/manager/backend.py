import json
import multiprocessing
import sys
import threading
import time
from collections import defaultdict
from multiprocessing.connection import Connection
from queue import Queue
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
from ..utils import provision, utils
from ..utils.logger import logger
from ..utils.provision import multi_try

send_lock = threading.Lock()


def send_threadsafe(self, data):
    send_lock.acquire()
    try:
        Connection.send(self, data)
    finally:
        send_lock.release()


class AISolver:

    def __init__(self):
        self._table_sites = TableDict(db_manager.get_site_names)
        self._already_warned = set()
        self.solver, self._cache_dict = solve.get_model_and_cache()
        self.venues = venue.VenueAliases(self.solver)

    def get_connections(self, subjects: list, indicators: set, parsing_types: dict, parsed_events: list):
        connections = []

        labels = (self._table_sites, parsing_types, self._already_warned,)
        types_on_site = db_manager.get_site_parsers()
        for connection in cross_subject_object(subjects, parsed_events, self.venues,
                                               self.solver, self._cache_dict,
                                               types_on_site, labels=labels):
            if connection['indicator'] in indicators:
                continue
            connections.append(connection)

        self._warn_already_loaded(connections)
        return connections

    def _warn_already_loaded(self, connections):
        already_ran_conns = dict()
        for connection in connections:
            indicator_data = {
                'event_id': connection['event_id'],
                'scheme_id': connection['scheme_id'],
                'date': str(connection['date']),
                'url': connection['url']
            }
            indicator_without_margin = json.dumps(indicator_data, sort_keys=True)
            if indicator_without_margin in already_ran_conns:
                already_ran_parent = already_ran_conns[indicator_without_margin]
                parents_part = f'{utils.Fore.RED}{connection["parent"]}\\{already_ran_parent}{utils.Fore.YELLOW}'
                message = (f'SEATS parser #{connection["event_id"]}'
                           f' {connection["event_name"]}'
                           f' {connection["date"]} ({parents_part})'
                           f' is absolutely similar'
                           f' to another loaded')
                if message not in self._already_warned:
                    self._already_warned.add(message)
                    logger.warning(message, name='Controller (Backend)')
            else:
                already_ran_conns[indicator_without_margin] = connection['parent']


class ThreadBuffer(threading.Thread):

    def __init__(self, process_func):
        super().__init__()
        self.buffer = []
        self.process_func = process_func
        self.start()

    def put(self, item):
        self.buffer.append(item)

    def run(self):
        while True:
            buffer = self.buffer
            self.buffer = []
            for item in buffer:
                self.process_func(item)
            if not buffer:
                time.sleep(0.05)


class TasksOnScheme(Queue):

    def __init__(self, event_id, scheme_id, name, group_schemes, pool):
        super().__init__()
        self.event_id = event_id
        self._group_schemes = group_schemes
        self.scheme = None
        self.queue_processed = False
        task = pooling.Task(self._create_scheme, 'Controller (Backend)', args=(event_id, scheme_id, name,))
        pool.add_task(task)

    def _get_group_scheme(self, scheme_id):
        if scheme_id not in self._group_schemes:
            new_scheme = scheme.Scheme(scheme_id)
            add_result = new_scheme.setup_sectors(wait_mode=True)
            if add_result is False:
                if not wait_until(lambda: scheme_id in self._group_schemes):
                    logger.error(f'Scheme distribution corrupted! Backend. Scheme id {scheme_id}',
                                 name='Controller (Backend)')
                    self._group_schemes[scheme_id] = new_scheme
            else:
                self._group_schemes[scheme_id] = new_scheme
        return self._group_schemes[scheme_id]

    def _create_scheme(self, event_id, scheme_id, name):
        group_scheme = self._get_group_scheme(scheme_id)
        new_scheme = scheme.ParserScheme(group_scheme, event_id, name)
        self.scheme = new_scheme
        self._empty_tasks_buffer()

    def _empty_tasks_buffer(self):
        while not self.empty():
            method_name, args = self.get()
            method = self._get_method(method_name)
            provision.just_try(method, args=args, name='Controller (Backend)')
        self.queue_processed = True

    def process(self, method_name, args):
        if self.queue_processed:
            method = self._get_method(method_name)
            provision.just_try(method, args=args, name='Controller (Backend)')
        else:
            self.put([method_name, args])
        # logger.debug(method_name, args, name='Backend')

    def _get_method(self, name):
        return getattr(self.scheme, name)


class SchemeRouterBackend:

    def __init__(self, conn: multiprocessing.connection.Connection):
        self.parser_schemes = {}
        self.group_schemes = {}
        self.conn = conn
        self._pool = ScheduledExecutor(stats='scheme_router_stats.csv', max_threads=5)
        self.buffer = ThreadBuffer(self.process_buffer)
        self.ai_workspace = AISolver()

    def create_scheme(self, event_id, scheme_id, name):
        if event_id not in self.parser_schemes:
            self.parser_schemes[event_id] = TasksOnScheme(event_id, scheme_id, name,
                                                          self.group_schemes, self._pool)

    def get_connections(self, *args):
        provision.threading_try(self._get_connections,
                                args=args,
                                name='Controller (Backend)',
                                tries=1)

    def _get_connections(self, subjects, indicators, parsing_types, parsed_events):
        solutions = self.ai_workspace.get_connections(subjects, indicators, parsing_types, parsed_events)
        self.conn.send(solutions)

    def process_buffer(self, got_data):
        method_name, args = got_data
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            provision.just_try(method, args=args, name='Controller (Backend)')
        else:
            if not args:
                logger.error('Buffer corrupted', name='Controller (Backend)')
                return
            event_id = args[0]
            args = args[1:]
            if event_id not in self.parser_schemes:
                logger.error('Scheme distribution corrupted', name='Controller (Backend)')
                return
            event_scheme = self.parser_schemes[event_id]
            event_scheme.process(method_name, args)

    def run(self) -> None:
        self.conn.send('Started')
        logger.info('Backend started', name='Controller (Backend)')
        while True:
            got_data = multi_try(self.conn.recv, tries=20, name='Controller (Backend)',
                                 raise_exc=False)
            if got_data is provision.TryError:
                sys.exit()
            else:
                self.buffer.put(got_data)


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
