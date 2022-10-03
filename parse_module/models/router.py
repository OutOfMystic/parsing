from . import scheme
from ..connection import db_manager


class SchemeRouter:

    def __init__(self):
        self.group_schemes = {}
        self.parser_schemes = {}
        
    def get_group_scheme(self, event_id):
        scheme_id = db_manager.get_scheme_id(event_id)
        if scheme_id not in self.group_schemes:
            new_scheme = scheme.Scheme(scheme_id)
            new_scheme.get_scheme()
            self.group_schemes[scheme_id] = new_scheme
        return self.group_schemes[scheme_id]

    def get_scheme(self, event_id):
        group_scheme = self.get_group_scheme(event_id)
        if event_id not in self.parser_schemes:
            new_scheme = scheme.ParserScheme(group_scheme, event_id)
            self.parser_schemes[event_id] = new_scheme
        return self.parser_schemes[event_id]


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

    def route_scheme(self, url, event_id):
        group = self.route_group(url, event_id)
        return group.router.get_scheme(event_id)

    def _assign(self, scheme_id, groups):
        self._assignments[scheme_id] = groups[0]
