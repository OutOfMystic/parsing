import threading
from collections import namedtuple
from importlib.resources import files
from threading import Lock

from psycopg2 import extras

from .. import connection
from ..connection import db_manager
from ..manager.backstage import tasker
from ..utils import utils, provision
from ..utils.exceptions import SchemeError, ParsingError, InternalError
from ..manager.controller import logger
from ..utils.provision import multi_try
from ..utils.types import LocalDict

Ticket = namedtuple('Ticket', ['x_coord', 'y_coord', 'sector', 'sector_id',
                               'row', 'seat', 'status', 'original_price', 'sell_price',
                               'event_id', 'scheme_id', 'no_schema_available'])


class Dancefloor:
    def __init__(self, ticket_id):
        self.ticket_id = ticket_id
        self.amount = 0
        self.price = 0


class Scheme:
    saved_schemes = LocalDict('constructors.sql')

    def __init__(self, scheme_id):
        self.scheme_id = scheme_id
        self.name = ''
        self.sectors = {}
        self.dancefloors = {}
        self.sector_names = []
        self.sector_data = []

    def setup_sectors(self, wait_mode=False):
        """with shelve.open('schemes') as shelf:
            name_scheme = shelf.get(str(self.scheme_id), None)
        if name_scheme:
            name, scheme = name_scheme
        else:
            event_locker = threading.Event()
            task = [self.scheme_id, callback, event_locker]
            tasker.put_throttle(db_manager.get_scheme, task,
                                from_iterable=False,
                                from_thread='Controller')
            event_locker.wait(600)
            del event_locker
            with shelve.open('schemes') as shelf:
                shelf[str(self.scheme_id)] = callback
            name, scheme = callback"""
        if wait_mode:
            name, scheme = self.saved_schemes.wait_and_get(self.scheme_id, timeout=1800, delay=10)
        else:
            name, scheme = self._get_scheme_wrapper(self.scheme_id)

        if name is None and scheme is None:
            return False
        self.name = name.replace(' - ', '-') \
                        .replace('сцена', '') \
                        .replace('театр', '') \
                        .replace('Театр', '') \
                        .replace('  ', ' ').strip()
        if self.name.startswith('-'):
            self.name = self.name[1:]
        all_sectors = scheme['sectors']

        seats_list = scheme['seats']

        for sector in all_sectors:
            sector_name = sector['name']
            if 'count' not in sector:
                self.sectors[sector_name] = {}
        for ticket_id, ticket in enumerate(seats_list):
            sector_id = ticket[3]
            sector_name = all_sectors[sector_id]['name']
            if ticket[8] == 1:
                if sector_name in self.dancefloors:
                    raise SchemeError(name)
                self.dancefloors[sector_name] = Dancefloor(ticket_id)
            else:
                id_row_seat = (ticket_id, str(ticket[5]), str(ticket[6]))
                self.sectors[sector_name][id_row_seat] = False

        self.sector_data = self._sector_data()
        self.sector_names = self._sector_names()
        return True

    def _get_scheme_wrapper(self, scheme_id):
        callback = self.saved_schemes.get(scheme_id, [])
        if callback:
            return callback

        event_locker = threading.Event()
        task = [scheme_id, callback, event_locker]
        tasker.put_throttle(db_manager.get_scheme, task,
                            self.saved_schemes,
                            from_iterable=False,
                            from_thread='Controller',
                            kwargs={'get_scheme': ''})
        logger.info(f'Pulling scheme {scheme_id} from the database!')
        event_locker.wait(1800)
        del event_locker

        if not callback:
            raise RuntimeError('Scheme awaiting timed out')
        return callback

    def _sector_names(self):
        return list(self.sectors.keys())

    def _sector_data(self):
        for sector_name, tickets in self.sectors.items():
            min_id, max_id = float('inf'), float('-inf')
            min_row, max_row = float('inf'), float('-inf')
            min_seat, max_seat = float('inf'), float('-inf')
            for id_, row, seat in tickets:
                min_id = min(min_id, id_)
                max_id = max(max_id, id_)
                min_row = min(min_row, row)
                max_row = max(max_row, row)
                min_seat = min(min_seat, seat)
                max_seat = max(max_seat, seat)
            id_range = [min_id, max_id]
            row_range = [min_row, max_row]
            seat_range = [min_seat, max_seat]
            yield sector_name, id_range, row_range, seat_range


class ParserScheme(Scheme):

    def __init__(self, scheme, event_id, group_name):
        super().__init__(scheme.scheme_id)
        self.event_id = event_id
        self.name = scheme.name
        self.group_name = group_name
        self._margins = {}
        self._lock = Lock()
        self._prohibitions = {}
        self._bookings = {}
        multi_try(self._customize, handle_error=self.reassign_scheme,
                  args=(scheme,), tries=5, name=group_name)

    def bind(self, priority, margin_func):
        try:
            self._lock.acquire()
            if priority in self._margins:
                raise InternalError(f"Scheme (event {self.event_id}) with the same priority "
                                    f"({margin_func.name}) has already been binded")
            self._margins[priority] = margin_func
            self._bookings[priority] = set()
            self._prohibitions[priority] = set()
            self._update_prohibitions(priority)
        finally:
            self._lock.release()

    def unbind(self, priority):
        try:
            self._lock.acquire()

            wiped_sectors = {sector_name: {} for sector_name in self.sectors}
            self._release_sectors(wiped_sectors, priority)

            del self._margins[priority]
            del self._bookings[priority]
            del self._prohibitions[priority]
        except Exception as err:
            logger.error(f'Error unbinding parser from scheme: {err}', name=self.name)
        finally:
            self._lock.release()

    def restore_margin(self, priority):
        return self._margins[priority]

    def release_sectors(self, parsed_sectors, parsed_dancefloors,
                        cur_priority, from_thread):
        self._lock.acquire()
        args = (parsed_sectors, cur_priority,)
        provision.multi_try(self._release_sectors, name=from_thread, tries=1,
                            args=args, raise_exc=False)
        args = (parsed_dancefloors, cur_priority)
        provision.multi_try(self._release_dancefloors, name=from_thread, tries=1,
                            args=args, raise_exc=False)
        self._lock.release()

    def _release_sectors(self, parsed_sectors, cur_priority):
        # calculations
        to_change, to_book, to_discard = {}, [], []
        differences = differences_lower(self.sectors, parsed_sectors)
        empty_sector_names, sector_names, unexpected_names = differences
        prohibited = self._prohibitions[cur_priority]
        bookings = self._bookings[cur_priority]

        # handle empty sectors
        for empty_sector_name in empty_sector_names:
            sector_all = self.sectors[empty_sector_name]
            tickets_to_wipe = self._wipe_sector(sector_all, prohibited, bookings)
            to_change.update(tickets_to_wipe)

        # handle non-empty sectors
        for scheme_name, parsed_name in sector_names:
            sector_all = self.sectors[scheme_name]
            sector_parsed = parsed_sectors[parsed_name]
            dict_sector = isinstance(sector_parsed, dict)
            if not dict_sector:
                raise ParsingError('List sectors are restricted in '
                                   'current version, use dict instead')
            handle_func = self._handle_sector_dict
            # handle_func = self._handle_sector_dict if dict_sector else self._handle_sector_list
            changes, bookings_, discards = handle_func(sector_all, sector_parsed,
                                                       prohibited, bookings)
            to_change.update(changes)
            to_book.extend(bookings_)
            to_discard.extend(discards)

        # sending changes to database
        parsed_sectors.clear()
        margin_func = self._margins[cur_priority]
        if to_change:
            tasker.put_throttle(db_manager.update_tickets, [to_change, margin_func],
                                from_thread='Controller', from_iterable=False,
                                kwargs={'update_tickets': ''})

        # applying changes of tickets in local storage
        for scheme_name, parsed_name in sector_names:
            sector_all = self.sectors[scheme_name]
            for id_row_seat in sector_all:
                id_ = id_row_seat[0]
                if id_ in to_change:
                    sector_all[id_row_seat] = to_change[id_]

        # applying changes of bookings in local storage
        self._bookings[cur_priority] = bookings.union(to_book)
        bookings = self._bookings[cur_priority]
        self._bookings[cur_priority] = bookings.difference(to_discard)
        if to_book or to_discard:
            self._update_prohibitions(cur_priority)

    def _release_dancefloors(self, parsed_dancefloors, cur_priority):
        to_change = {}
        differences = differences_lower(self.dancefloors, parsed_dancefloors)
        empty_sector_names, sector_names, unexpected_names = differences

        # handle empty sectors
        for empty_sector_name in empty_sector_names:
            dancefloor_all = self.dancefloors[empty_sector_name]
            to_change[dancefloor_all] = None

        for sector_name, parsed_name in sector_names:
            dancefloor_all = self.dancefloors[sector_name]
            amount_parsed, price_parsed = parsed_dancefloors[parsed_name]
            if dancefloor_all.amount != amount_parsed:
                to_change[dancefloor_all] = (price_parsed, amount_parsed,)
            elif dancefloor_all.price != price_parsed:
                to_change[dancefloor_all] = (price_parsed, amount_parsed,)

        # sending changes to database
        parsed_dancefloors.clear()
        margin_func = self._margins[cur_priority]
        if to_change:
            tasker.put_throttle(db_manager.update_dancefloors, to_change, margin_func,
                                from_thread='Controller',
                                kwargs={'update_dancefloors': ''})

        # applying changes of tickets in local storage
        for dancefloor, price_amount in to_change.items():
            if price_amount is None:
                dancefloor.amount = 0
            else:
                price, amount = price_amount
                dancefloor.amount = amount
                dancefloor.price = price

    def _customize(self, scheme):
        db_tickets = {}
        event_locker = threading.Event()
        task = [self.event_id, db_tickets, event_locker]

        tasker.put_throttle(db_manager.get_all_tickets, task,
                            from_iterable=False,
                            from_thread='Controller',
                            kwargs={'get_all_tickets': ''})
        event_locker.wait(600)
        del event_locker

        if not db_tickets:
            raise SchemeError(f'Schema {self.scheme_id} cannot '
                              f'be applied to event {self.event_id}!\n'
                              f'No tickets on scheme! Try to reassign it')
        first_id = min(db_tickets.keys())
        try:
            to_change = {}
            for sector_name, sector_all in scheme.sectors.items():
                new_sector = {}
                self.sectors[sector_name] = new_sector
                for id_, row, seat in sector_all:
                    new_id = first_id + id_
                    new_ticket = (new_id, row, seat)
                    # if db_tickets[new_id]:
                    #     to_change[new_id] = False
                    # new_sector[new_ticket] = False
                    new_sector[new_ticket] = db_tickets[new_id]
            if to_change:
                tasker.put_throttle(db_manager.update_tickets, [to_change, lambda price: price],
                                    from_thread='Controller', from_iterable=False)
            for sector_name, dancefloor in scheme.dancefloors.items():
                ticket_id = dancefloor.ticket_id
                new_id = ticket_id + first_id
                new_sector = Dancefloor(new_id)
                self.dancefloors[sector_name] = new_sector
        except KeyError:
            raise SchemeError(f'Schema {self.scheme_id} cannot '
                              f'be applied to event {self.event_id}!\n'
                              f'This scheme was assigned wrong! Try to reassign it')

    def _update_prohibitions(self, cur_priority):
        for priority in self._bookings:
            if priority >= cur_priority:
                continue
            self._prohibitions[priority] = self._get_prohibited(priority)

    def _get_prohibited(self, cur_priority):
        prohibited = set()
        to_union = [self._bookings[prior] for prior in self._bookings
                    if prior < cur_priority]
        for booking in to_union:
            prohibited.update(booking)
        return prohibited

    def _wipe_sector(self, sector_all, prohibited, booking):
        to_change = {}

        for seat, seat_avail_subject in sector_all.items():
            ticket_id = seat[0]
            if seat_avail_subject:
                if (ticket_id in booking) and (ticket_id not in prohibited):
                    to_change[ticket_id] = False
        return to_change

    @staticmethod
    def _handle_sector_list(sector_all, sector_parsed, prohibited, booking):
        to_change = {}
        to_discard = []
        to_book = []

        for seat, seat_avail_subject in sector_all.items():
            row_seat = seat[1:]
            ticket_id = seat[0]

            if row_seat in sector_parsed:
                if not seat_avail_subject:
                    to_change[ticket_id] = True
                to_book.append(ticket_id)
            else:
                if seat_avail_subject:
                    if (ticket_id in booking) and (ticket_id not in prohibited):
                        to_change[ticket_id] = False
                to_discard.append(ticket_id)
        return to_change, to_book, to_discard

    def _handle_sector_dict(self, sector_all, sector_parsed, prohibited, booking):
        to_change = {}
        to_discard = []
        to_book = []

        for seat, seat_avail_subject in sector_all.items():
            row_seat = seat[1:]
            ticket_id = seat[0]

            if row_seat in sector_parsed:
                price = sector_parsed[row_seat]
                price = price // 100 * 100
                if price < 100:
                    logger.info(f'Tickets with price below 100 ({ticket_id}) are skipped', name=self.name)
                    continue
                if seat_avail_subject != price:
                    # logger.debug(ticket_id, seat_avail_subject, price)
                    to_change[ticket_id] = price
                to_book.append(ticket_id)
            else:
                if seat_avail_subject:
                    if (ticket_id in booking) and (ticket_id not in prohibited):
                        to_change[ticket_id] = False
                to_discard.append(ticket_id)
        #print(to_change)
        #print(to_book)
        #print(to_discard)
        return to_change, to_book, to_discard

    def reassign_scheme(self, exception, scheme):
        """
        Создать билеты у event_id
        взять схему для билетов в public.tables_constructor с scheme_id
        """
        if not isinstance(exception, SchemeError):
            raise exception

        scheme_box = self._get_scheme_wrapper(scheme.scheme_id)
        scheme_json = scheme_box[-1]

        all_tickets = []

        for ticket in scheme_json["seats"]:
            sector = scheme_json["sectors"][ticket[3]]
            if "count" in sector:
                new_dance_ticket = {
                    'x_coord': 0,
                    'y_coord': 0,
                    'sector': sector["name"],
                    'sector_id': ticket[3],
                    'row': "no_schema",
                    'seat': "no_schema",
                    'status': "not",
                    'original_price': 1,
                    'sell_price': 1,
                    'event_id': self.event_id,
                    'scheme_id': scheme.scheme_id,
                    'no_schema_available': 0
                }
                tickets = Ticket(**new_dance_ticket)
                all_tickets.append(tuple(tickets))
            else:
                new_ticket = {
                    "x_coord": ticket[0],
                    "y_coord": ticket[1],
                    "sector": sector["name"],
                    "sector_id": ticket[3],
                    "row": ticket[5],
                    "seat": ticket[6],
                    "status": 'not',
                    "original_price": 1,
                    "sell_price": 1,
                    "event_id": self.event_id,
                    "scheme_id": scheme.scheme_id,
                    'no_schema_available': 0
                }
                tickets = Ticket(**new_ticket)
                all_tickets.append(tuple(tickets))
        clear_query = "DELETE FROM public.tables_tickets " \
                      f"WHERE event_id_id={self.event_id}"
        insert_query = """
            INSERT INTO public.tables_tickets (
                x_coord, y_coord, sector, sector_id, 
                row, seat, status, original_price, sell_price, 
                event_id_id, scheme_id_id,  no_schema_available
            ) VALUES %s
        """
        db_manager.execute(clear_query)
        db_manager.commit()
        extras.execute_values(db_manager.cursor, insert_query, all_tickets, template=None, page_size=100)
        logger.info(f'Scheme reassigned successfully '
                    f'(event_id: {self.event_id}, scheme_id: {scheme.scheme_id})',
                    name=self.group_name)
        db_manager.commit()


def differences_lower(left, right):
    # Returns items which are only in the
    # left array and only in the right array
    left_lower = {elem.lower(): elem for elem in left}
    right_lower = {elem.lower(): elem for elem in right}
    names_right = left_lower.copy()
    names_right.update(right_lower)
    names_left = right_lower.copy()
    names_left.update(left_lower)

    set1 = set(left_lower)
    set2 = set(right_lower)
    dif1 = list(set1 - set2)
    intersection = list(set1 & set2)
    dif2 = list(set2 - set1)

    dif1_upper = [names_left[elem] for elem in dif1]
    intersection = [[names_left[elem], names_right[elem]] for elem in intersection]
    dif2_upper = [names_right[elem] for elem in dif2]
    return dif1_upper, intersection, dif2_upper
