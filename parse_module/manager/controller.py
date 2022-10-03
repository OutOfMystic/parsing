import os
import inspect
import threading
import time

from .proxy import loader
from ..models.parser import db_manager
from ..utils import provision, utils
from ..models.parser import SeatsParser, EventParser
from ..models.group import SeatsParserGroup


class Controller(threading.Thread):
    def __init__(self, parsers_path, config_path, pending_delay=30, check_porxies_delay=7200):
        super().__init__()
        self.parser_modules = load_parsers(parsers_path)
        self.pending_delay = pending_delay
        self._prepare_workspace()
        self.event_parsers = []
        self.seats_groups = []
        self.proxy_hub = loader.ManualProxies('all_proxies.json')
        self.load_config(config_path)
        self.fast_time = time.time()

    @staticmethod
    def bprint(mes, color=utils.Fore.GREEN):
        mes = f'Controller| {utils.colorize(mes, color)}\n'
        print(mes, end='')

    @staticmethod
    def _prepare_workspace():
        if not os.path.exists('screen'):
            os.mkdir('screen')
        if not os.path.exists('downloads'):
            os.mkdir('downloads')

    def _start_parser(self, parser_class, parser_name):
        if get_parents(parser_class) == EventParser:
            self._start_event_parser(parser_class, parser_name)
        elif get_parents(parser_class) == SeatsParser:
            self._init_seats_parsers(parser_class, parser_name)

    def _start_event_parser(self, parser_class, parser_name):
        parser = parser_class(self)
        parser.name = parser_name
        parser.start()
        self.bprint(f'EVENT parser {parser_name} has started')
        self.event_parsers.append(parser)

    def _init_seats_parsers(self, parser_class, parser_name):
        group = SeatsParserGroup(self, parser_class)
        self.bprint(f'seats group {parser_name}.{parser_class.__name__} has started')
        self.seats_groups.append(group)

    def load_connections(self):
        connections = db_manager.get_events_for_parsing()

        all_connections = {group: [] for group in self.seats_groups}
        for subject_id, parsing_data in connections[::-1]:
            for priority, parsing_settings in enumerate(parsing_data):
                parsing_settings = [priority, subject_id] + parsing_settings
                subject_url = parsing_settings[2]
                for group in self.seats_groups:
                    if group.url_filter(subject_url):
                        all_connections[group].append(parsing_settings)
                        break

        for group, connections in all_connections.items():
            if not connections:
                continue
            group.update(connections)

    def load_config(self, config_path):
        config = provision.load_data(config_path)
        for parser_name in config:
            if not config[parser_name]:
                continue
            assert parser_name in self.parser_modules, \
                f'Loading: parser {parser_name} wasn\'t found'
            module = self.parser_modules[parser_name]
            for argument in dir(module):
                parser_class = getattr(module, argument)
                self._start_parser(parser_class, parser_name)

    def run(self):
        self.fast_time = time.time() + 120
        fast_delay = 5
        while True:
            provision.multi_try(self.load_connections, name='Controller',
                                tries=1, raise_exc=False)
            delay = self.pending_delay if time.time() > self.fast_time else fast_delay
            time.sleep(delay)


def load_parsers(path):
    dirs = [module.split('.py')[0] for module in os.listdir(path) if is_package(module)]
    parser_modules = {}
    for dir_ in dirs:
        exec(f'from {path} import {dir_}')
        exec(f'parser_modules["{dir_}"] = {dir_}')
    return parser_modules


def is_package(pack):
    return not pack.startswith('__') and pack.endswith('.py')


def get_parents(class_):
    if not inspect.isclass(class_):
        return
    if class_.__name__.startswith('__'):
        return
    for _ in range(5):
        class_ = class_.__base__
        if class_ == EventParser:
            return EventParser
        elif class_ == SeatsParser:
            return SeatsParser
        elif class_ == object:
            return
        elif not class_:
            return
