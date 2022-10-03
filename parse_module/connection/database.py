import sys
import json
import threading
from threading import Lock

import psycopg2
import time

from ..utils.provision import multi_try
from ..utils import utils, provision


def locker(func):
    def wrapper(*args):
        try:
            lock.acquire()
            return func(*args)
        except psycopg2.ProgrammingError as err:
            print(f'Retrying {func.__name__}: {err}')
            return wrapper(*args)
        finally:
            lock.release()
    return wrapper


class DBConnection:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = str(port)
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.cursor = None
        self.connect_db()

    def connect_db(self):
        multi_try(self._connect_db, name='Database', tries=5)

    def _connect_db(self):
        self.connection = psycopg2.connect(user=self.user,
                                           password=self.password,
                                           host=self.host,
                                           port=self.port,
                                           database=self.database)
        self.cursor = self.connection.cursor()
        self.cursor.execute("SELECT version();")
        record = self.cursor.fetchone()
        print("Подключение к БД успешно: ", record, "\n")

    def execute(self, request):
        return provision.multi_try(self.cursor.execute, args=(request,),
                                   to_except=self._connect_db, name='DB', tries=9)

    def fetchall(self):
        return provision.multi_try(self.cursor.fetchall, to_except=self._connect_db,
                                   name='DB', tries=9)

    def commit(self):
        return provision.multi_try(self.connection.commit, to_except=self._connect_db,
                                   name='DB', tries=9)


class ParsingDB(DBConnection):
    def __init__(self):
        super().__init__(host="195.2.81.173",
                         port="5432",
                         user="tenerunayo",
                         password="umauwuNg24@A",
                         database="crmdb")

    @locker
    def get_scheme_id(self, event_id):
        self.execute("SELECT scheme_id "
                     "FROM public.tables_event "
                     f"WHERE id={event_id}")
        records = self.fetchall()
        return records[0][0]

    @locker
    def get_scheme(self, scheme_id):
        self.execute("SELECT name, json FROM "
                     "public.tables_constructor "
                     f"WHERE id={scheme_id}")
        records = self.fetchall()
        return records[0]

    @locker
    def get_all_tickets(self, event_id):
        self.execute("SELECT id, status FROM public.tables_tickets "
                     f"WHERE event_id_id={event_id}")
        records = self.fetchall()
        tickets = {id_: status == 'available-pars' for id_, status in records}
        return tickets

    @locker
    def get_unfilled_tickets(self, event_id):
        self.execute("SELECT sector, id, row, seat "
                     "FROM public.tables_tickets "
                     f"WHERE event_id_id={event_id} AND NOT status='available'")
        return self.fetchall()

    @locker
    def get_event_parsers(self):
        self.execute("SELECT parent FROM public.tables_parsedevents")
        records = self.fetchall()
        return records

    @locker
    def get_events_for_parsing(self):
        self.execute("SELECT id, parsed_url FROM "
                     "public.tables_event "
                     "WHERE parsed_url IS NOT NULL")
        records = self.fetchall()
        return records

    @locker
    def update_tickets(self, tickets, margin_func):
        set_to_false, set_to_true, true_with_price = divide_tickets(tickets)
        set_to_false_str = map(str, set_to_false)
        set_to_true_str = map(str, set_to_true)
        false_string = ", ".join(set_to_false_str)
        true_string = ", ".join(set_to_true_str)

        if false_string:
            self.execute("UPDATE public.tables_tickets "
                         "SET status='not' WHERE "
                         f"id IN ({false_string}) AND NOT status='available';")
            self.commit()
            print(f'Falsed: {len(set_to_false)}')
        if true_string:
            self.execute("UPDATE public.tables_tickets "
                         "SET status='available-pars' "
                         f"WHERE id IN ({set_to_true}) AND NOT status='available';")
            self.commit()
        scripts = []
        for price in true_with_price:
            sell_price = margin_func(price)
            scripts.append("UPDATE public.tables_tickets "
                          f"SET status='available-pars', original_price={price}, "
                          f"sell_price={sell_price} "
                          f"WHERE id IN ({true_with_price[price]}) AND NOT status='available';")
            true_count = true_with_price[price].count(',') + 1
            print(f'Trued: {true_count} with price {price}')
        if scripts:
            self.execute('\n'.join(scripts))
        self.commit()

    @locker
    def add_parsed_events(self, rows):
        str_rows = [f"('{v1}', '{v2}', {v3}, '{v4}', '{v5}', '{json.dumps(v6)}', '{v7}')"
                    for v1, v2, v3, v4, v5, v6, v7 in rows]
        values = ", ".join(str_rows)
        columns = [
            'parent', 'event_name', 'timeout', 'url',
            'venue', 'extra', 'date'
        ]
        joined_cloumns = ', '.join(columns)
        script = (f"INSERT INTO public.tables_parsedevents ({joined_cloumns}) "
                  f"VALUES {values}")
        self.execute(script)
        self.commit()

    @locker
    def get_parsed_events(self):
        self.execute('SELECT event_name, url, venue, timeout, '
                     'extra, date from public.tables_parsedevents')
        records = self.fetchall()
        return records

    @locker
    def get_margin(self, margin_name):
        self.execute('SELECT rules from public.tables_margin '
                         f"WHERE name='{margin_name}'")
        rules = self.fetchall()[0][0]
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
    def delete_parsed_events(self, parent):
        self.execute("DELETE FROM public.tables_parsedevents "
                     f"WHERE parent='{parent}'")
        self.commit()


def divide_tickets(tickets):
    set_to_false = []
    set_to_true = []
    true_with_price = {}
    for ticket in tickets:
        ticket_id = ticket[0]
        availability = ticket[1]
        if len(ticket) == 3:
            price = ticket[2]
            if price not in true_with_price:
                true_with_price[price] = []
            true_with_price[price].append(ticket_id)
        elif availability:
            set_to_true.append(ticket_id)
        else:
            set_to_false.append(ticket_id)
    for price in true_with_price:
        price_strs = [str(price) for price in true_with_price[price]]
        true_with_price[price] = ", ".join(price_strs)
    return set_to_false, set_to_true, true_with_price


lock = threading.Lock()
db_manager = ParsingDB()