import asyncio
import datetime
import inspect
import itertools
import json
import os
import random
import time
from asyncio import AbstractEventLoop

from . import pooling
from .inspect import run_inspection
from .proxy import loader
from .telecore import TeleCore
from .. import coroutines
from ..connection import db_manager
from ..coroutines import AsyncEventParser, AsyncSeatsParser
from ..models.ai_nlp import alias
from ..models.margin import MarginRules
from parse_module.notify import from_parsing
from ..models.parser import SeatsParser, EventParser
from parse_module.manager.group import SeatsParserGroup
from ..utils import provision, utils
from ..utils.date import Date
from ..utils.logger import start_async_logger, logger
from ..utils.utils import differences

PREDEFINED = True


class Controller:
    def __init__(self,
                 parsers_path,
                 config_path,
                 router,
                 async_loop: AbstractEventLoop,
                 pending_delay=60,
                 debug_url=None,
                 debug_event_id=None,
                 release=False):
        super().__init__()
        self.async_loop = async_loop
        self.parsed_events = None
        self.parser_modules = load_parsers(parsers_path)
        self.pending_delay = pending_delay
        self._debug_url = debug_url
        self._debug_event_id = debug_event_id
        self.debug = self._debug_event_id or self._debug_url
        self.release = release

        self._async_logger_started = False
        self.fast_time = time.time()
        self.schemes_on_event = {}
        self.event_parsers = []
        self.seats_groups = []
        self.event_notifiers = []
        self.seats_notifiers = []
        self.margins = {}
        self._events_were_reset = []

        # Controller threaded resources
        self.router = router
        self._prepare_workdir()
        self.tele_core = get_telecore()
        self._console = run_inspection(self, release=True)
        self.proxy_hub = loader.ManualProxies('all_proxies.json') if parsers_path else None
        self.event_aliases = alias.EventAliases(step=5)
        self.parsing_types = db_manager.get_parsing_types()
        self.pool = pooling.ScheduledExecutor(max_threads=30)

        # Controller async resources
        start_async_logger()
        self.request_semaphore = asyncio.Semaphore(60)
        self.pool_async = coroutines.ScheduledExecutor(async_loop, debug=self.debug)

        self._load_parsers_with_config(config_path)

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
        if not inspect.isclass(parser_variable):
            return
        elif parser_variable in (EventParser, SeatsParser, AsyncEventParser, AsyncSeatsParser):
            return
        elif issubclass(parser_variable, EventParser):
            self._start_event_parser(parser_variable, parser_name)
        elif issubclass(parser_variable, SeatsParser):
            self._init_seats_parsers(parser_variable, parser_name)
        else:
            return

    def _start_event_parser(self, parser_class, parser_name):
        if parser_name not in list(self.parsing_types.values()):
            db_manager.add_parsing_type(parser_name)
            self.parsing_types = db_manager.get_parsing_types()
            self.bprint(f'New type has been registered: {parser_name}')

        if self.debug:
            return
        self.proxy_hub.add_route(parser_class.proxy_check)
        parser = parser_class(self, parser_name)
        parser.start()
        self.bprint(f'{parser.name} has started')
        self.event_parsers.append(parser)

    def _init_seats_parsers(self, parser_class, parser_name):
        self.proxy_hub.add_route(parser_class.proxy_check)
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
                logger.debug(f'Margin changed on {new_margin_name}', name='Controller')
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
        margins_by_name = {margin.name: margin.id for margin in self.margins.values()}
        for priority, parsing_settings in enumerate(conn['parsing']):
            subject_url, margin_name = parsing_settings
            margin_id = margins_by_name.get(margin_name, None)
            if margin_id is None:
                logger.error(f'Can\'t find margin with name {margin_name}', name='Controller')

            connection = {
                'priority': priority,
                'event_id': conn['event_id'],
                'scheme_id': conn['scheme_id'],
                'date': Date(conn['date']) ,#+ datetime.timedelta(hours=3)),
                'url': subject_url,
                'margin': margin_id
            }

            signature = connection.copy()
            signature['date'] = str(connection['date'])
            connection['signature'] = signature
            indicator = signature.copy()
            del indicator['priority']
            connection['indicator'] = str(indicator)

            yield connection

    def get_connections(self, subjects):
        indicators = set()

        # Predefined connections
        predefined_connections = []
        for subject in subjects[::-1]:
            if not PREDEFINED:
                self.bprint('PREDEFINED PARSERS ARE SWITCHED OFF', color=utils.Fore.YELLOW)
                break
            for connection in self._predefined_parsers(subject):
                indicator = connection['indicator']
                indicators.add(indicator)
                predefined_connections.append(connection)

        self.router.get_connections_task(subjects, indicators, self.parsing_types,
                                         self.parsed_events)
        ai_connections = self.router.get_connections_result()
        return predefined_connections, ai_connections

    def database_interaction(self):
        start_time = time.time()
        self.update_margins_from_database()
        self.parsed_events = db_manager.get_parsed_events(types=self.parsing_types)
        self.event_aliases.step()
        events_for_parsing = db_manager.get_events_for_parsing()
        logger.debug(f'Database interaction {time.time() - start_time}', name='Controller')
        return events_for_parsing

    def load_connections(self, subjects):
        # MAKE CONNECTIONS AND DISTRIBUTE THEM TO SEATS GROUPS
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

        # UPDATE SEATS GROUPS WITH GAINED CONNECTIONS
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

        """ # Start async logger
        if not self._async_logger_started:
            #start_async_logger(self.async_loop)
            self._async_logger_started = True"""

        # Waiting for seats lockers to be released
        start_time = time.time()
        while any(group.start_lock.locked() for group in self.seats_groups):
            if time.time() - start_time > self.pending_delay:
                connected = sum(group.going_to_start for group in self.seats_groups)
                groups_locked = [group.name for group in self.seats_groups if group.start_lock.locked()]
                groups_in_a_row = ', '.join(groups_locked) if len(groups_locked) <= 3 else len(groups_locked)
                message = f'Seats groups\' ({groups_in_a_row}) lockers are still being released... ' \
                          f'Going to start {connected}'
                self.bprint(message, color=utils.Fore.YELLOW)
            time.sleep(2)

        return subjects, all_connections, predefined_connections + ai_connections

    def _load_notifiers(self):
        # EVENT NOTIFIERS
        events_to_load, seats_to_load = db_manager.get_parser_notifiers()

        events_to_load_names = {f"EventParser ({data['name']})": data for data in events_to_load}
        loaded_events_names = {notifier.parser.name: notifier
                               for notifier in self.event_notifiers}
        to_del, to_review, to_add = utils.differences(loaded_events_names, events_to_load_names)

        # EVENT NOTIFIERS TO STOP
        for parsing_name in to_del:
            notifier = loaded_events_names[parsing_name]
            notifier.stop()
            self.event_notifiers.remove(notifier)

        # EVENT NOTIFIERS TO REVIEW
        for parsing_name in to_review:
            notifier = loaded_events_names[parsing_name]
            notifier_data = events_to_load_names[parsing_name]
            delay = notifier_data.get('delay', None)
            if delay is not None:
                notifier.parser.delay = delay
            for attribute, value in notifier_data.items():
                setattr(notifier, attribute, value)

        # EVENT NOTIFIERS TO LOAD
        event_parsers_to_add = {parser.name: parser for parser in self.event_parsers
                                if parser.name in to_add}
        for parsing_name, event_parser in event_parsers_to_add.items():
            notifier_data = events_to_load_names[parsing_name]
            notifier = from_parsing.EventNotifier(self, event_parser, **notifier_data)
            self.bprint(f'Event-Notifier for {event_parser.name}'
                        f' was attached to the parser')
            self.event_notifiers.append(notifier)

        # SEATS NOTIFIERS
        seats_to_load_names = {load_data['event_id']: load_data for load_data in seats_to_load}
        loaded_seats_names = {notifier.event_id: notifier for notifier in self.seats_notifiers}
        all_seats_parsers = itertools.chain.from_iterable(group.parsers for group in self.seats_groups)
        all_seats_parsers = list(all_seats_parsers)
        to_del, to_review, to_add = utils.differences(loaded_seats_names, seats_to_load_names)

        # PREPARING DATA FOR LOADED WITH AUTORUN SETTINGS
        events_to_autorun = {data['name']: data for data in events_to_load if data['autorun_seats']}
        seats_to_run = {}
        for parser in all_seats_parsers:
            if parser.parent in events_to_autorun:
                real_parser_event_id = parser.signature['event_id']
                seats_to_run[real_parser_event_id] = parser
                if real_parser_event_id in seats_to_load_names:
                    continue
                seats_to_load_names[real_parser_event_id] = events_to_autorun[parser.parent]

        # SEATS NOTIFIERS TO STOP
        for event_id in to_del:
            notifier = loaded_seats_names[event_id]
            notifier.stop()
            self.seats_notifiers.remove(notifier)

        # SEATS NOTIFIERS TO REVIEW
        for event_id in to_review:
            notifier = loaded_seats_names[event_id]
            notifier_data = seats_to_load_names[event_id]
            delay = notifier_data.get('delay', None)
            if delay is not None:
                notifier.parser.delay = delay
            for attribute, value in notifier_data.items():
                setattr(notifier, attribute, value)

        # SEATS NOTIFIERS TO LOAD
        seats_parsers_to_add = {parser.signature['event_id']: parser for parser in all_seats_parsers
                                if parser.signature['event_id'] in to_add}
        seats_to_run.update(seats_parsers_to_add)
        for event_id, seats_parser in seats_to_run.items():
            notifier_data = seats_to_load_names[event_id]
            notifier = from_parsing.SeatsNotifier(self, seats_parser, name=seats_parser.name,
                                                  **notifier_data)
            self.bprint(f'Seats-Notifier for {seats_parser.parent} ({seats_parser.name}) '
                        f'was attached to the parser')
            self.seats_notifiers.append(notifier)

    def _database_cleanwork(self, subjects, all_conns, all_conns_plain):
        # Do some database work at the end of step
        if self.release and not self.debug:
            db_manager.delete_old_tickets()
            self._reset_tickets(subjects, all_conns)
        self._update_db_with_stored_urls(all_conns_plain)

    def _reset_tickets(self, subjects, all_connections):
        event_ids = set(connection['event_id'] for connection in plain_dict_values(all_connections))
        all_event_ids = set(subject['event_id'] for subject in subjects)
        events_to_reset = all_event_ids - event_ids

        _, _, new_to_reset = differences(self._events_were_reset, events_to_reset)
        logger.debug(f'{len(new_to_reset)} were reset', name='Controller')
        db_manager.reset_tickets(new_to_reset)
        self._events_were_reset = list(events_to_reset)

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
        # self.database_interaction()
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
        self.fast_time = time.time()
        fast_delay = 5

        if self._debug_url:
            self.bprint(utils.red('DEBUG') + utils.green(' URL IS DEFINED!!!'))
        if self._debug_event_id:
            self.bprint(utils.red('DEBUG') + utils.green(' EVENT ID IS DEFINED!!!'))

        while True:
            subjects = provision.just_try(self.database_interaction, name='Controller')
            if subjects is provision.TryError:
                logger.error('DATABASE INTERACTION FAILED', name='Controller')
                continue
            conn_data = provision.just_try(self.load_connections, args=(subjects,), name='Controller')
            provision.just_try(self._load_notifiers, name='Controller')
            if conn_data is provision.TryError:
                logger.error('MAKING CONNECTIONS FAILED', name='Controller')
                continue
            provision.just_try(self._database_cleanwork, args=conn_data, name='Controller')
            delay = self.pending_delay if time.time() > self.fast_time else fast_delay
            time.sleep(delay)


def get_telecore():
    admins = [454746771, 772343631]
    tele_profiles = os.path.join('config', 'tele_profiles.json')
    tele_accordance = os.path.join('config', 'tele_accordance.json')
    tele_core = TeleCore(profiles_config=tele_profiles,
                         accordance_config=tele_accordance,
                         admins=admins)
    tele_core.add('notifications', '6002068146:AAHx8JmyW3QhhFK5hhdFIvTXs3XFlsWNraw')
    tele_core.add('bills', '5741231744:AAGHiVougv4uoRia5I_behO9r1oMj1NEMI8')
    return tele_core


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


def plain_dict_values(dict_):
    chain = itertools.chain.from_iterable(dict_.values())
    return list(chain)

