import os
import pickle
import json
import time
from collections import defaultdict
from threading import Lock

import psycopg2

from ..utils.logger import logger
from ..utils.provision import multi_try
from ..utils import utils, provision, date
from ..manager.backstage import tasker

locked_counter = 0


def locker(func):

    def wrapper(*args, **kwargs):
        global locked_counter

        try:
            locked_counter += 1
            lock.acquire()
            return func(*args, **kwargs)
        except psycopg2.ProgrammingError as err:
            mes = f'Retrying {func.__name__}: {err}'
            logger.warning(mes, name='Controller')
            return wrapper(*args, **kwargs)
        except IndexError:
            print('Didn\'t get a full response!')
        finally:
            locked_counter -= 1
            lock.release()
    return wrapper


class DBConnection:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = str(port)
        self.user = user
        self.password = password
        self.database = database
        self._save_mode = False
        self._saved_selects = {}
        self.connection = None
        self.cursor = None
        tasker.put(self.connect_db, from_thread='Controller')

    def save_mode_on(self):
        logger.warning('DATABASE SAVE MODE TURNED ON', name='Controller')
        self._save_mode = True
        if os.path.exists('selects.pkl'):
            with open('selects.pkl', 'rb') as fp:
                saved_selects = pickle.load(fp)
            if date.Day(saved_selects['date']) != date.Day(date.now()):
                logger.info('Pickled selects are outdated, skipping', name='Controller')
                return
            self._saved_selects = saved_selects

    def _update_saves(self, request, response):
        self._saved_selects[request] = response
        self._saved_selects['date'] = str(date.now())
        with open('selects.pkl', 'wb+') as fp:
            pickle.dump(self._saved_selects, fp)

    def connect_db(self):
        multi_try(self._connect_db, name='Controller', tries=5)

    def _connect_db(self):
        self.connection = None
        self.cursor = None
        self.connection = psycopg2.connect(user=self.user,
                                           password=self.password,
                                           host=self.host,
                                           port=self.port,
                                           database=self.database)
        self.cursor = self.connection.cursor()

    def cursor_wrapper(self, func_name, *args):
        while self.cursor is None:
            time.sleep(0.1)

        try:
            function = getattr(self.cursor, func_name)
            return function(*args)
        except psycopg2.ProgrammingError as error:
            if str(error) == 'no results to fetch':
                raise error
            logger.error(f'Unable to process command: {error}', name='Controller')
        except Exception as error:
            raise error

    def connection_wrapper(self, func_name, *args):
        while self.connection is None:
            time.sleep(0.1)
        try:
            function = getattr(self.connection, func_name)
            return function(*args)
        except psycopg2.ProgrammingError as error:
            logger.error(f'Unable to process command: {error}', name='Controller')
        except Exception as error:
            raise error

    def execute(self, request):
        return provision.multi_try(self.cursor_wrapper, args=('execute', request,),
                                   handle_error=self._connect_db, name='Controller',
                                   tries=5)

    def select(self, request):
        if request in self._saved_selects:
            fetched = self._saved_selects[request]
            logger.info(f'LOADED request with len {len(str(fetched))} {request}')
        else:
            self.execute(request)
            fetched = self.fetchall()
            if self._save_mode and fetched is not None:
                self._update_saves(request, fetched)
        return fetched

    def fetchall(self):
        return provision.multi_try(self.cursor_wrapper, args=('fetchall',),
                                   handle_error=self._connect_db,
                                   tries=5, name='Controller')

    def commit(self):
        return provision.multi_try(self.connection_wrapper, args=('commit',),
                                   handle_error=self._connect_db,
                                   tries=5, name='Controller')


class ParsingDB(DBConnection):
    def __init__(self):
        super().__init__(host="193.178.170.180",
                         port="5432",
                         user="django_project",
                         password="Q8kPzqBPk4fb6I",
                         database="crmdb")
        
    # def __init__(self):
    #     super().__init__(host="195.2.81.173",
    #                     port="5432",
    #                     user="tenerunayo",
    #                     password="umauwuNg24@A",
    #                     database="crmdb")

    @locker
    def get_scheme(self, tasks, saved_schemes, **kwargs):
        dicted_tasks = defaultdict(list)
        event_lockers = []
        for scheme_id, callback, event_locker in tasks:
            dicted_tasks[scheme_id].append(callback)
            event_lockers.append(event_locker)

        scheme_ids = ', '.join(str(scheme_id) for scheme_id in dicted_tasks)
        try:
            self.execute("SELECT name, json, id FROM public.tables_constructor "
                         f"WHERE id IN ({scheme_ids})")

            for name, json_, scheme_id in self.fetchall():
                callbacks = dicted_tasks[scheme_id]
                callbacks[0].append(name)
                callbacks[0].append(json_)
                for callback in callbacks[1:]:
                    callback.append(None)
                    callback.append(None)
            for scheme_id, callbacks in dicted_tasks.items():
                if callbacks:
                    if callbacks[0][0] is not None:
                        saved_schemes[scheme_id] = callbacks[0]
                else:
                    logger.error(f'PARSER STARTED INCORRECTLY. SCHEME {scheme_id} DATA WAS LOST', name='Controller')
        finally:
            for event_locker in event_lockers:
                event_locker.set()

    @locker
    def get_scheme_names(self):
        self.execute("SELECT id, name, venue FROM public.tables_constructor")
        records = self.fetchall()
        for id_, name, venue in records:
            if not venue:
                logger.error(utils.red(f'Empty venue name for scheme {name} ({id_})!!!'),
                             name='Controller')
                continue
        return {id_: venue for id_, _, venue in records}

    @locker
    def get_all_tickets(self, tasks, **kwargs):
        dicted_tasks = {}
        event_lockers = []
        for event_id, callback, event_locker in tasks:
            dicted_tasks[event_id] = callback
            event_lockers.append(event_locker)

        event_ids = ', '.join(str(event_id) for event_id in dicted_tasks)
        self.execute("SELECT id, status, original_price, event_id_id FROM public.tables_tickets "
                     f"WHERE event_id_id IN ({event_ids})")

        for id_, status, price, event_id in self.fetchall():
            dicted_tasks[event_id][id_] = price if status == 'available-pars' else False
        for event_locker in event_lockers:
            event_locker.set()

    @locker
    def get_event_parsers(self):
        self.execute("SELECT parent FROM public.tables_parsedevents")
        records = self.fetchall()
        return records

    @locker
    def get_events_for_parsing(self):
        self.execute("SELECT id, name, date, scheme_id, parsed_url, site_id "
                     "FROM public.tables_event "
                     "WHERE site_id <> 3 AND scheme_id IS NOT NULL")
        records = self.fetchall()
        connections = [{'event_id': id_, 'event_name': name, 'date': date,
                        'parsing': parsing, 'site_id': site_id, 'scheme_id': scheme_id}
                       for id_, name, date, scheme_id, parsing, site_id in records]
        for connection in connections:
            if connection['parsing'] is None:
                connection['parsing'] = []
            connection['event_id'] = int(connection['event_id'])
        connections.sort(key=lambda key: key['event_id'])
        return connections

    @locker
    def reset_tickets(self, event_ids):
        if not event_ids:
            return
        event_ids = ', '.join(str(event_id) for event_id in event_ids)
        self.execute(f"UPDATE public.tables_tickets "
                     f"SET status='not' "
                     f"WHERE status='available-pars' AND "
                     f"event_id_id IN ({event_ids})")
        self.commit()

    @locker
    def update_dancefloors(self, change_dict, margin_func, **kwargs):
        scripts = []
        for dancefloor, price_amount in change_dict.items():
            if price_amount is None:
                ticket_id = dancefloor.ticket_id
                script = f"UPDATE public.tables_tickets " \
                         f"SET status='not', no_schema_available=0 " \
                         f"WHERE id={ticket_id};"
            else:
                origin_price, amount = price_amount
                sell_price = margin_func(origin_price)
                ticket_id = dancefloor.ticket_id
                status = 'available-pars' if amount else 'not'
                script = f"UPDATE public.tables_tickets " \
                         f"SET status='{status}', original_price={origin_price}, " \
                         f"sell_price={sell_price}, no_schema_available={amount} " \
                         f"WHERE id={ticket_id};"
            scripts.append(script)
        if scripts:
            self.execute('\n'.join(scripts))
        self.commit()

    @locker
    def update_tickets(self, tasks, **kwargs):
        tickets = {}
        for task, margin_func in tasks:
            for ticket_id, value in task.items():
                if value is True:
                    tickets[ticket_id] = True
                elif value is False:
                    tickets[ticket_id] = False
                else:
                    tickets[ticket_id] = (value, margin_func(value),)
        set_to_false, set_to_true, true_with_price = divide_tickets(tickets)
        # logger.debug(f'To False {len(set_to_false)}')
        # logger.debug(f'To True {len(set_to_true)}')
        # for price_and_sell_price, ticket_ids in true_with_price.items():
        #    logger.debug(f'To True wth price {len(ticket_ids)} ({price_and_sell_price[1]})')
        set_to_false_str = map(str, set_to_false)
        set_to_true_str = map(str, set_to_true)
        false_string = ", ".join(set_to_false_str)
        true_string = ", ".join(set_to_true_str)

        scripts = []
        if false_string:
            scripts.append("UPDATE public.tables_tickets "
                           "SET status='not' WHERE "
                           f"id IN ({false_string}) AND "
                           f"status='available-pars';")
        if true_string:
            scripts.append("UPDATE public.tables_tickets "
                           "SET status='available-pars' "
                           f"WHERE id IN ({set_to_true}) AND "
                           f"status='not';")
        for price_and_sell_price, ticket_ids in true_with_price.items():
            price, sell_price = price_and_sell_price
            scripts.append("UPDATE public.tables_tickets "
                           f"SET status='available-pars', original_price={price}, "
                           f"sell_price={sell_price} "
                           f"WHERE id IN ({ticket_ids}) AND "
                           f"status='not';")
        if scripts:
            self.execute('\n'.join(scripts))
            self.commit()

    @locker
    def add_parsed_events(self, rows):
        str_rows = [f"('{v1}', '{v2}', '{v3}', '{v4}', '{json.dumps(v5)}', '{v6}')"
                    for v1, v2, v3, v4, v5, v6 in rows]
        values = ", ".join(str_rows)
        columns = [
            'parent', 'event_name', 'url',
            'venue', 'extra', 'date'
        ]
        joined_cloumns = ', '.join(columns)
        script = (f"INSERT INTO public.tables_parsedevents ({joined_cloumns}) "
                  f"VALUES {values}")
        self.execute(script)
        self.commit()

    @locker
    def get_parsed_events(self, types=None):
        if types is None:
            self.execute('SELECT id, name from public.tables_parsingtypes')
            types = {id_: name for id_, name in self.fetchall()}
        self.execute('SELECT parent, event_name, url, venue, '
                     'extra, date from public.tables_parsedevents')

        records = self.fetchall()
        dicted = [{'parent': parent, 'event_name': name, 'url': url,
                   'venue': venue if venue != 'null' else None, 'extra': extra, 'date': date}
                  for parent, name, url, venue, extra, date in records]

        for object_ in dicted:
            type_id = utils.find_by_value(types, object_['parent'])
            object_['type_id'] = type_id

        return dicted

    @locker
    def get_parsing_types(self):
        self.execute('SELECT id, name from public.tables_parsingtypes')
        return {id_: name for id_, name in self.fetchall()}

    @locker
    def add_parsing_type(self, name):
        self.execute('INSERT INTO public.tables_parsingtypes (id, name) '
                     f"VALUES (DEFAULT, '{name}')")
        self.commit()

    @locker
    def get_site_parsers(self):
        self.execute('SELECT id, parsers from public.tables_sites WHERE disabled=FALSE')
        return {id_: int_keys(parsers) for id_, parsers in self.fetchall()
                if parsers is not None}

    @locker
    def get_site_names(self, already=None):
        if already:
            found = ', '.join(str(elem) for elem in already)
            self.execute(f'SELECT id, name from public.tables_sites WHERE id NOT IN ({found})')
        else:
            self.execute(f'SELECT id, name from public.tables_sites')
        return {id_: name for id_, name in self.fetchall()}

    @locker
    def get_margins(self):
        self.execute('SELECT id, name, rules from public.tables_margin')
        rules = {id_: (name, value,) for id_, name, value in self.fetchall()}
        return rules

    @locker
    def remove_parsed_events(self, events):
        requests = [(f"DELETE FROM public.tables_parsedevents WHERE"
                     f" event_name='{ev_name}' AND url='{url}' AND date='{date}';")
                     for ev_name, url, date in events]
        combined_request = '\n'.join(requests)
        self.execute(combined_request)
        self.commit()

    @locker
    def get_event_aliases(self):
        self.execute("SELECT * from public.parsing_aliases")
        aliases = {origin: alias for origin, alias in self.fetchall()}
        return aliases

    @locker
    def delete_parsed_events(self, parent):
        self.execute("DELETE FROM public.tables_parsedevents "
                     f"WHERE parent='{parent}'")
        self.commit()

    @locker
    def store_urls(self, parser_urls):
        str_rows = [f"({event_id}, '{urls}')" for event_id, urls in parser_urls]
        values = ", ".join(str_rows)
        self.execute('TRUNCATE TABLE public.tables_stored_urls')
        self.commit()
        self.execute('INSERT INTO public.tables_stored_urls (id, urls) '
                     f"VALUES {values}")
        self.commit()

    @locker
    def get_parser_notifiers(self):
        columns = ['name', 'delay', 'tele_profiles',
                   'print_minus', 'min_amount',
                   'min_increase', 'repeats_until_succeeded',
                   'autorun_seats', 'autorun_delay',
                   'autorun_min_amount', 'autorun_min_increase']
        rows = self.select(f'SELECT {", ".join(columns)} FROM public.tables_eventnotifier')
        event_parsers = []
        for row in rows:
            db_data = {column: value for column, value in zip(columns, row)}
            event_parsers.append(db_data)

        columns = ['event_id', 'delay', 'tele_profiles',
                   'print_minus', 'min_amount',
                   'min_increase', 'repeats_until_succeeded']
        rows = self.select(f'SELECT {", ".join(columns)} FROM public.tables_seatsnotifier')
        seats_parsers = []
        for row in rows:
            db_data = {column: value for column, value in zip(columns, row)}
            seats_parsers.append(db_data)

        return event_parsers, seats_parsers


class TableDict(dict):

    def __init__(self, update_func):
        super().__init__()
        self.update_func = update_func

    def update_names(self):
        actual_data = self.update_func(self.keys())
        self.update(actual_data)

    def __getitem__(self, item):
        if item not in self:
            self.update_names()
        return super().__getitem__(item)

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default


def divide_tickets(tickets):
    set_to_false = []
    set_to_true = []
    true_with_price_str = defaultdict(list)
    for ticket_id, availability in tickets.items():
        if availability is False:
            set_to_false.append(ticket_id)
        elif availability is True:
            set_to_true.append(ticket_id)
        elif isinstance(availability, tuple):
            true_with_price_str[availability].append(ticket_id)
        else:
            raise TypeError(f'Parsed ticket value should be int or bool,'
                            f' not {type(availability).__name__}')
    true_with_price_dict = {}
    for price, ticket_ids in true_with_price_str.items():
        price_strs = [str(price) for price in ticket_ids]
        true_with_price_dict[price] = ", ".join(price_strs)
    return set_to_false, set_to_true, true_with_price_dict


def int_keys(dict_):
    if dict_ is None:
        return {}
    if not dict_:
        return {}
    new_dict = {}
    for key, value in dict_.items():
        key = int(key)
        new_dict[key] = value
    return new_dict


lock = Lock()
