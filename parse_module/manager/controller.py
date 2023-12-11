import datetime
import itertools
import json
import os
import random
import threading
import time

from .proxy import loader
from .telecore import tele_core
from ..connection.database import TableDict
from ..models.ai_nlp.alias import EventAliases
from ..models.ai_nlp.collect import cross_subject_object
from ..models.ai_nlp.venue import VenueAliases
from ..models.margin import MarginRules
from parse_module.notify import from_parsing
from ..models.parser import db_manager
from ..models.parser import SeatsParser, EventParser
from ..models.group import SeatsParserGroup
from ..utils import provision, utils
from ..utils.date import Date
from ..utils.logger import logger
from ..utils.utils import differences

PREDEFINED = True


class Controller(threading.Thread):
    def __init__(self,
                 parsers_path,
                 config_path,
                 pending_delay=20,
                 debug_url=None,
                 debug_event_id=None,
                 release=False):
        super().__init__()
        self.parsed_events = None
        self.parser_modules = load_parsers(parsers_path)
        self.pending_delay = pending_delay
        self._debug_url = debug_url
        self._debug_event_id = debug_event_id
        self.debug = True if self._debug_event_id or self._debug_url else False
        self.release = release

        self._prepare_workdir()
        self.schemes_on_event = {}
        self.event_parsers = []
        self.seats_groups = []
        self.event_notifiers = []
        self.seats_notifiers = []
        self.margins = {}
        self._events_were_reset = []
        self._table_sites = TableDict(db_manager.get_site_names)
        self._already_warned_on_collect = set()

        self.proxy_hub = loader.ManualProxies('all_proxies.json') if parsers_path else None
        self.event_aliases = EventAliases(step=5)
        self.parsing_types = db_manager.get_parsing_types()
        self.venues = VenueAliases()
        self._load_parsers_with_config(config_path)
        self.fast_time = time.time()

    @staticmethod
    def bprint(mes, color=utils.Fore.LIGHTGREEN_EX):
        logger.bprint_compatible(mes, 'Controller', color)

    @staticmethod
    def _prepare_workdir():
        if not os.path.exists('screen'):
            os.mkdir('screen')
        if not os.path.exists('downloads'):
            os.mkdir('downloads')

    def _start_parser(self, parser_variable, parser_name):
        if parser_name.startswith('www.'):
            parser_name = parser_name.split('www.')[1]
        try:
            if parser_variable in (EventParser, SeatsParser):
                return
            elif issubclass(parser_variable, EventParser):
                self._start_event_parser(parser_variable, parser_name)
            elif issubclass(parser_variable, SeatsParser):
                self._init_seats_parsers(parser_variable, parser_name)
            else:
                return
        except TypeError:
            return
        self.proxy_hub.add_route(parser_variable.proxy_check_url)

    def _start_event_parser(self, parser_class, parser_name):
        if parser_name not in list(self.parsing_types.values()):
            db_manager.add_parsing_type(parser_name)
            self.parsing_types = db_manager.get_parsing_types()
            self.bprint(f'New type has been registered: {parser_name}')

        parser = parser_class(self, parser_name)
        parser.start()
        self.bprint(f'EVENT parser {parser_name} has started')
        self.event_parsers.append(parser)

    def _init_seats_parsers(self, parser_class, parser_name):
        group = SeatsParserGroup(self, parser_class, parser_name)
        self.bprint(f'{group.name} has started')
        self.seats_groups.append(group)

    def update_margins_from_database(self):
        got_margins = db_manager.get_margins()
        to_del, to_check, to_add = utils.differences(self.margins, got_margins)
        for margin_id in to_check:
            margin_func = self.margins[margin_id]
            new_margin_name, new_margin_rules = got_margins[margin_id]
            if new_margin_rules != margin_func.rules or new_margin_name != margin_func.name:
                margin_func.rules = new_margin_rules
                margin_func.name = new_margin_name
                logger.debug(f'Margin changed on {new_margin_name}')
                for group in self.seats_groups:
                    group.stop_by_margin(margin_id)
        for margin_id in to_add:
            margin_name, margin_rules = got_margins[margin_id]
            margin = MarginRules(margin_id, margin_name, margin_rules)
            self.margins[margin_id] = margin
        for margin_id in to_del:
            margin = self.margins[margin_id]
            logger.info(f'Deleting margin {margin.name}')
            for group in self.seats_groups:
                group.stop_by_margin(margin_id)
            del self.margins[margin_id]

    def _predefined_parsers(self, conn):
        for priority, parsing_settings in enumerate(conn['parsing']):
            subject_url, margin_name = parsing_settings
            margin_id = self.get_margin_id_by_name(margin_name)
            if not margin_id:
                continue
            connection = {
                'priority': priority,
                'event_id': conn['event_id'],
                'date': Date(conn['date'] + datetime.timedelta(hours=3)),
                'url': subject_url,
                'margin': margin_id,
                'scheme_id': conn['scheme_id']
            }
            signature = connection.copy()
            signature['date'] = str(connection['date'])
            connection['signature'] = signature
            indicator = signature.copy()
            del indicator['priority']
            connection['indicator'] = indicator
            yield connection

    def get_connections(self, subjects):
        indicators = []
        predefined_connections = []
        ai_connections = []

        for subject in subjects[::-1]:
            if not PREDEFINED:
                self.bprint('PREDEFINED PARSERS ARE SWITCHED OFF', color=utils.Fore.YELLOW)
                break
            for connection in self._predefined_parsers(subject):
                indicator = connection['indicator']
                indicators.append(indicator)
                predefined_connections.append(connection)

        labels = (self._table_sites, self.parsing_types, self._already_warned_on_collect,)
        for connection in cross_subject_object(subjects, self.parsed_events, self.venues, labels=labels):
            if connection['indicator'] in indicators:
                message = f"{connection['event_name']} {connection['date']} route conflict.\n" \
                          f"This parser is already assigned by AI. Leaving predefined state.\n" \
                          f"URL {connection['url']}"
                # self.bprint(message, color=utils.Fore.YELLOW)
                continue
            ai_connections.append(connection)
        return predefined_connections, ai_connections

    def database_interaction(self):
        self.update_margins_from_database()
        self.parsed_events = db_manager.get_parsed_events(types=self.parsing_types)
        self.event_aliases.step()
        return db_manager.get_events_for_parsing()

    def load_connections(self):
        start_time = time.time()
        subjects = self.database_interaction()
        logger.debug(f'Database interaction {time.time() - start_time}')

        all_connections = {group: [] for group in self.seats_groups}
        predefined_connections, ai_connections = self.get_connections(subjects)
        for connection in predefined_connections:
            for group in self.seats_groups:
                if group.url_filter(connection['url']):
                    all_connections[group].append(connection)
                    break
        for connection in ai_connections:
            for group in self.seats_groups:
                if group.url_filter(connection['url']):
                    all_connections[group].append(connection)
        # this_group = list(all_connections.values())[0]
        # print(len(this_group))
        # utils.pp_dict(all_connections)

        if not self.debug:
            for group, connections in all_connections.items():
                if not connections:
                    continue
                group.update(connections)
        elif self._debug_url:
            group, connections = self.get_debug_url_conn(all_connections)
            if connections:
                group.update(connections)
            else:
                self.bprint('Debug connection with specified url wasn\'t found',
                            color=utils.Fore.RED)
        elif self._debug_event_id:
            for group, connections in self.get_debug_ev_id_conns(all_connections):
                group.update(connections)

        # Do some database work at the end of step
        lock_time = time.time()
        self._reset_tickets()
        self._update_db_with_stored_urls(predefined_connections + ai_connections)

        # Waiting for seats lockers to be released
        lockers_states = [group.start_lock.locked() for group in self.seats_groups]
        first_pending = lockers_states.count(True)
        pending = first_pending
        while pending:
            if time.time() - lock_time > self.pending_delay:
                message = f'Seats groups\' lockers ({pending}/{first_pending}) are still being released...'
                self.bprint(message, color=utils.Fore.LIGHTGREEN_EX)
            time.sleep(5)
            lockers_states = [group.start_lock.locked() for group in self.seats_groups]
            pending = lockers_states.count(True)

    def _load_notifiers(self):
        events_to_load, seats_to_load = db_manager.get_parser_notifiers()

        events_to_load_names = {data['name']: data for data in events_to_load}
        loaded_events_names = {notifier.parser.name: notifier
                               for notifier in self.event_notifiers}
        to_del, to_review, to_add = utils.differences(loaded_events_names, events_to_load_names)

        # EVENTS PARSERS TO STOP
        for parsing_name in to_del:
            notifier = loaded_events_names[parsing_name]
            notifier.stop()
            self.event_notifiers.remove(notifier)

        # EVENTS PARSERS TO REVIEW
        for parsing_name in to_review:
            notifier = loaded_events_names[parsing_name]
            notifier_data = events_to_load_names[parsing_name]
            delay = notifier_data.get('delay', None)
            if delay is not None:
                notifier.parser.delay = delay
            for attribute, value in notifier_data.items():
                setattr(notifier, attribute, value)

        # EVENTS PARSERS TO LOAD
        event_parsers_to_add = {parser.name: parser for parser in self.event_parsers
                                if parser.name in to_add}
        for parsing_name, event_parser in event_parsers_to_add.items():
            notifier_data = events_to_load_names[parsing_name]
            notifier = from_parsing.EventNotifier(self, event_parser, **notifier_data)
            notifier.start()
            self.bprint(f'Event-Notifier for {event_parser.name}'
                        f' was attached to the parser')
            self.event_notifiers.append(notifier)

        seats_to_load_names = {notifier['event_id']: notifier for notifier in seats_to_load}
        loaded_seats_names = {notifier.event_id: notifier for notifier in self.seats_notifiers}
        all_seats_parsers = itertools.chain.from_iterable(group.parsers for group in self.seats_groups)
        all_seats_parsers = list(all_seats_parsers)
        to_del, to_review, to_add = utils.differences(loaded_seats_names, seats_to_load_names)

        # SEATS PARSERS TO STOP
        for event_id in to_del:
            notifier = loaded_seats_names[event_id]
            notifier.stop()
            self.seats_notifiers.remove(notifier)

        # SEATS PARSERS TO REVIEW
        for event_id in to_review:
            notifier = loaded_seats_names[event_id]
            notifier_data = seats_to_load_names[event_id]
            delay = notifier_data.get('delay', None)
            if delay is not None:
                notifier.parser.delay = delay
            for attribute, value in notifier_data.items():
                setattr(notifier, attribute, value)

        # SEATS PARSERS TO LOAD
        seats_parsers_to_add = {parser.event_id: parser for parser in all_seats_parsers
                                if parser.event_id in to_add}
        for event_id, seats_parser in seats_parsers_to_add.items():
            notifier_data = seats_to_load_names[event_id]
            notifier = from_parsing.SeatsNotifier(self, seats_parser, name=seats_parser.name,
                                                  **notifier_data)
            notifier.start()
            self.bprint(f'Seats-Notifier for {seats_parser.parent} ({seats_parser.name}) '
                        f'was attached to the parser')
            self.seats_notifiers.append(notifier)

    def _reset_tickets(self):
        if not self.release or self.debug:
            return
        event_ids = set()
        for group in self.seats_groups:
            for parser in group.parsers:
                event_ids.add(parser.event_id)
        _, _, new_to_reset = differences(self._events_were_reset, event_ids)
        db_manager.reset_tickets(new_to_reset)
        self._events_were_reset = list(event_ids)

    def _load_parsers_with_config(self, config_path):
        if config_path is None:
            print(utils.yellow('EMPTY CONFIGURATION'))
            return
        config = provision.try_open(config_path, {}, json_=True)
        turn_on_stats = {False: 0, True: 0}
        for parser_name in config:
            key = config[parser_name]
            turn_on_stats[key] += 1
            if not config[parser_name]:
                continue
            assert parser_name in self.parser_modules, \
                f'Loading: parser {parser_name} wasn\'t found'
            module = self.parser_modules[parser_name]
            for argument in dir(module):
                parser_variable = getattr(module, argument)
                self._start_parser(parser_variable, parser_name)

        self._seats_prop = turn_on_stats[True] / (turn_on_stats[False] + turn_on_stats[True] + 0.01)

    def get_margin_id_by_name(self, name):
        for margin in self.margins.values():
            if margin.name == name:
                return margin.id
        else:
            self.bprint(f'Can\'t find margin with name {name}', color=utils.Fore.RED)

    def get_debug_url_conn(self, all_connections):
        for group, connections in all_connections.items():
            for connection in connections:
                if connection['url'] == self._debug_url:
                    return group, [connection]
        else:
            return None, None

    def get_debug_ev_id_conns(self, all_connections):
        for group, connections in all_connections.items():
            for connection in connections:
                if connection['event_id'] == self._debug_event_id:
                    yield group, [connection]

    def _update_db_with_stored_urls(self, connections):
        if random.random() < 0.1 or not self.release:
            return
        self.database_interaction()
        parsers_on_event = {}
        for event_id, conns_on_event in utils.groupby(connections, lambda conn: conn['event_id']):
            parser_urls = {conn['url'] for conn in conns_on_event
                           if 'tickets-star.com' not in conn['url']}
            parsers_on_event[event_id] = parser_urls

        list_parsers = list(parsers_on_event.items())
        list_parsers.sort(key=lambda row: row[0])
        prepared_list = []
        for id_, urls in list_parsers:
            urls = list(urls)
            dumped = json.dumps(urls)
            row = [id_, dumped]
            prepared_list.append(row)
        db_manager.store_urls(prepared_list)

    def run(self):
        if self.parser_modules is None:
            raise RuntimeError('Controller cannot be started being non-configured')
        tele_core.add('notifications', '6002068146:AAHx8JmyW3QhhFK5hhdFIvTXs3XFlsWNraw')
        tele_core.add('bills', '5741231744:AAGHiVougv4uoRia5I_behO9r1oMj1NEMI8')
        self.fast_time = time.time()
        fast_delay = 5

        if self._debug_url:
            self.bprint(utils.red('DEBUG') + utils.green(' URL IS DEFINED!!!'))
        if self._debug_event_id:
            self.bprint(utils.red('DEBUG') + utils.green(' EVENT ID IS DEFINED!!!'))

        while True:
            provision.multi_try(self.load_connections, name='Controller',
                                tries=1, raise_exc=False)
            provision.multi_try(self._load_notifiers, name='Controller',
                                tries=1, raise_exc=False)
            delay = self.pending_delay if time.time() > self.fast_time else fast_delay
            time.sleep(delay)


def load_parsers(path):
    if path is None:
        print(utils.yellow('PARSERS PATH IS NONE. NONE OF PARSERS ARE LOADED'))
        return {}
    dirs = [module.split('.py')[0] for module in os.listdir(path) if is_package(module)]
    parser_modules = {}
    for dir_ in dirs:
        exec(f'from {path} import {dir_}')
        exec(f'parser_modules["{dir_}"] = {dir_}')
    return parser_modules


def is_package(pack):
    return not pack.startswith('__') and pack.endswith('.py')
