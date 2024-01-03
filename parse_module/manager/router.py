import time

from ..models import scheme
from ..connection import db_manager
from ..utils.logger import logger


class SchemeRouterFrontend:

    def __init__(self, conn):
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
            add_result = new_scheme.setup_sectors()
            if add_result is False:
                if not wait_until(lambda: scheme_id in self.group_schemes):
                    logger.error(f'Scheme distribution corrupted! Frontend. Scheme id {scheme_id}',
                                 name='Controller')
                    self.group_schemes[scheme_id] = new_scheme
            else:
                self.group_schemes[scheme_id] = new_scheme
        return self.group_schemes[scheme_id]


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
        priority, force = args if len(args) == 2 else args[0], False
        if force:
            if priority not in self._margins:
                return
        operation = ['unbind', [self.event_id, priority]]
        del self._margins[args[0]]
        self.conn.send(operation)

    def release_sectors(self, parsed_sectors, parsed_dancefloors,
                        cur_priority, from_thread):
        operation = ['release_sectors', [self.event_id, parsed_sectors, parsed_dancefloors,
                                         cur_priority, from_thread]]
        self.conn.send(operation)

    def restore_margin(self, priority):
        return self._margins[priority]


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


def wait_until(condition, timeout=300, step=0.1):
    start_time = time.time()
    while not condition():
        if (time.time() - start_time) > timeout:
            return False
        time.sleep(step)
    return True
