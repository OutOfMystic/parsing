import time
from threading import Lock

from . import scheme
from ..connection import db_manager
from ..utils import provision
from ..utils.logger import logger


def wait_until(condition, timeout=60, step=0.1):
    start_time = time.time()
    while not condition():
        if (time.time() - start_time) > timeout:
            return False
        time.sleep(step)
    return True


class SchemeRouter:
    parser_schemes = {}
    group_schemes = {}
    event_lockers = {}

    def get_parser_scheme(self, event_id, scheme_id, name='Controller'):
        lock = self._get_lock(event_id)
        try:
            lock.acquire()
            group_scheme = self.get_group_scheme(scheme_id)
            if event_id not in self.parser_schemes:
                new_scheme = scheme.ParserScheme(group_scheme, event_id, name)
                self.parser_schemes[event_id] = new_scheme
            got_scheme = self.parser_schemes[event_id]
            return got_scheme
        finally:
            lock.release()

    def get_group_scheme(self, scheme_id):
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

    def _get_lock(self, event_id):
        if event_id not in self.event_lockers:
            self.event_lockers[event_id] = Lock()
        return self.event_lockers[event_id]


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

    def route_scheme(self, url, event_id, scheme_id):
        group = self.route_group(url, event_id)
        return group.router.get_parser_scheme(event_id, scheme_id)

    def _assign(self, scheme_id, groups):
        self._assignments[scheme_id] = groups[0]


