import multiprocessing
import threading
import time
from multiprocessing.connection import Connection

from ..models import scheme
from ..connection import db_manager
from ..utils.exceptions import InternalError
from ..utils.logger import logger


class SchemeRouterFrontend:

    def __init__(self, conn):
        self.conn = conn
        self.group_schemes = {}
        self.parser_schemes = {}
        self.task_lock = False

    def get_parser_scheme(self, event_id, scheme_id, name='Controller'):
        if event_id in self.parser_schemes:
            # logger.debug('found n sql', name=event_id)
            return self.parser_schemes[event_id]
        # logger.debug('gettng group scheme', name=event_id)
        group_scheme = self._get_group_scheme(scheme_id)
        operation = ['create_scheme', [event_id, scheme_id, name]]
        # logger.debug('sendng operaton', name=event_id)
        self.conn.send(operation)
        # logger.debug('operatn sent', name=event_id)
        new_scheme = SchemeProxy(group_scheme, self.conn, event_id)
        self.parser_schemes[event_id] = new_scheme
        return new_scheme

    def _get_group_scheme(self, scheme_id):
        if scheme_id not in self.group_schemes:
            new_scheme = scheme.Scheme(scheme_id)
            add_result = new_scheme.setup_sectors()
            if add_result is False:
                if not wait_until(lambda: scheme_id in self.group_schemes):
                    logger.error(f'Scheme distribution corrupted! Frontend. Scheme id {scheme_id}',
                                 name='Controller')
                    self.group_schemes[scheme_id] = new_scheme
            else:
                self.group_schemes[scheme_id] = new_scheme
        return self.group_schemes[scheme_id]

    def get_connections_task(self, subjects, indicators, parsing_types, parsed_events):
        if self.task_lock:
            raise InternalError('AI task placing error: task transport corrupted')
        operation = ['get_connections', [subjects, indicators, parsing_types, parsed_events]]
        self.conn.send(operation)
        self.task_lock = True

    def get_connections_result(self):
        if not self.task_lock:
            raise InternalError('AI solutions were lost: task transport corrupted')
        connections = self.conn.recv()
        self.task_lock = False
        return connections


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

    def unbind(self, priority, force=False):
        if force:
            if priority not in self._margins:
                return
        operation = ['unbind', [self.event_id, priority]]
        del self._margins[priority]
        self.conn.send(operation)

    def release_sectors(self, parsed_sectors, parsed_dancefloors,
                        cur_priority, from_thread):
        operation = ['release_sectors', [self.event_id, parsed_sectors, parsed_dancefloors,
                                         cur_priority, from_thread]]
        self.conn.send(operation)

    def restore_margin(self, priority):
        return self._margins[priority]


def wait_until(condition, timeout=300, step=0.1):
    start_time = time.time()
    while not condition():
        if (time.time() - start_time) > timeout:
            return False
        time.sleep(step)
    return True
