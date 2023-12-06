import itertools
import threading
import time

from loguru import logger

from . import collect
from .solve import solver
from ...connection import db_manager
from ...utils import provision, utils


class VenueAliases:
    """
    Нужно сопоставить object_['venue'] и event['scheme']['name']
    Главная функция get возвращает алиас из event['scheme']['name']
    Заносятся новые схемы
    Заносятся новые объекты для парсинга

    Названия схем берутся из списка scheme_names, он обновляется
    внутри controller.
    Когда выполняется get, делается проход через assigned.
    Если же в assigned alias не обнаружен, то решается alias для схем
    Если появился новый scheme
    """

    def __init__(self):
        self.aliases = {}
        self.schemes = {}
        self._lock = threading.Lock()

    def update_names(self, venues: set):
        schemes = db_manager.get_scheme_names()
        new_venues = venues.difference(self.aliases)
        if not new_venues and (schemes == self.schemes):
            return
        self.schemes = schemes

        all_aliases = venues.union(self.aliases.keys())
        all_aliases = list(all_aliases)
        all_aliases_fixed = [fix_alias(alias) for alias in all_aliases]
        schemes = self.schemes.values()
        schemes_fixed = {fix_scheme(scheme): scheme for scheme in schemes}
        pairs = itertools.product(all_aliases_fixed, schemes_fixed)
        pairs = list(pairs)
        solved = solver.solve_pack(pairs)

        names_len = len(schemes_fixed) if len(solved) else 1
        new_aliases = {}
        for start in range(0, len(solved), names_len):
            solutions = solved[start: start + names_len]
            accepted_indexes = [start + solutions.index(sol) for sol in solutions if sol > 0.9999]
            venue = all_aliases[start // names_len]
            accepted_schemes = [pairs[index][1] for index in accepted_indexes]
            new_aliases_on_venue = [schemes_fixed[scheme] for scheme in accepted_schemes]
            new_aliases[venue] = list(set(new_aliases_on_venue))
        self.aliases.update(new_aliases)

    def get(self, alias):
        return self.aliases[alias]


def fix_alias(alias):
    return alias.lower() \
        .replace('театр', '') \
        .replace('дворец', '') \
        .replace('арена', '') \
        .replace('цирк', '') \
        .replace('им.', '') \
        .replace('им', '')


def fix_scheme(scheme):
    return scheme.lower() \
        .replace('театр', '') \
        .replace('дворец', '') \
        .replace('сцена', '') \
        .replace('арена', '') \
        .replace('цирк', '') \
        .replace('им.', '') \
        .replace('им', '')
