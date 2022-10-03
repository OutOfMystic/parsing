from threading import Lock

from ..connection import db_manager
from ..utils import utils, provision


class Scheme:
    def __init__(self, scheme_id):
        self.scheme_id = scheme_id
        self.name = ''
        self.sectors = {}

    def get_scheme(self):
        name, scheme = db_manager.get_scheme(self.scheme_id)
        self.name = name.replace(' - ', '-') \
                        .replace('сцена', '') \
                        .replace('театр', '') \
                        .replace('Театр', '') \
                        .replace('  ', ' ').strip()
        sector_names = [sector['name'] for sector in scheme['sectors']]
        seats_list = scheme['seats']

        for sector_name in sector_names:
            self.sectors[sector_name] = {}
        for ticket_id, ticket in enumerate(seats_list):
            sector_id = ticket[3]
            sector_name = sector_names[sector_id]
            id_row_seat = (ticket_id, ticket[5], ticket[6])
            self.sectors[sector_name][id_row_seat] = False

    def sector_names(self):
        return list(self.sectors.keys())

    def sector_data(self):
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

    def __init__(self, scheme, event_id):
        super().__init__(scheme.scheme_id)
        self.event_id = event_id
        self.name = scheme.name
        self._lock = Lock()
        self._margins = {}
        self._prohibitions = {}
        self._bookings = {}
        self._customize(scheme)

    def bind(self, priority, margin_func):
        try:
            self._lock.acquire()
            self._margins[priority] = margin_func
            self._bookings[priority] = set()
            self._prohibitions[priority] = set()
            self._update_prohibitions(priority)
        except Exception as err:
            mes = utils.red(f'{self.name}: Error binding parser to scheme: {err}')
            print(mes)
        finally:
            self._lock.release()

    def unbind(self, priority):
        try:
            self._lock.acquire()

            wiped_sectors = {sector_name: [] for sector_name in self.sectors}
            self.release_sectors(wiped_sectors, priority)

            del self._margins[priority]
            del self._bookings[priority]
            del self._prohibitions[priority]
        except Exception as err:
            mes = utils.red(f'{self.name}: Error unbinding parser from scheme: {err}')
            print(mes)
        finally:
            self._lock.release()

    def release_sectors(self, parsed_sectors, cur_priority):
        self._lock.acquire()
        args = (parsed_sectors, cur_priority,)
        provision.multi_try(self._release_sectors, name='Scheme', tries=1,
                            args=args, raise_exc=False, prefix=self.name,
                            to_except=self._lock.release)

    def _release_sectors(self, parsed_sectors, cur_priority):
        # calculations
        to_change, to_book, to_discard = [], [], []
        differences = differences_lower(self.sectors, parsed_sectors)
        empty_sector_names, sector_names, unexpected_names = differences
        prohibited = self._prohibitions[cur_priority]
        bookings = self._bookings[cur_priority]

        # handle empty sectors
        for empty_sector_name in empty_sector_names:
            sector_all = self.sectors[empty_sector_name]
            for elem in self._wipe_sector(sector_all, prohibited, bookings):
                to_change.append(elem)

        # handle not empty sectors
        for scheme_name, parsed_name in sector_names:
            sector_all = self.sectors[scheme_name]
            sector_parsed = parsed_sectors[parsed_name]
            dict_sector = isinstance(sector_parsed, dict)
            handle_func = self._handle_sector_dict if dict_sector else self._handle_sector_list
            payload = handle_func(sector_all, sector_parsed, prohibited, bookings)
            changes, bookings_, discards = payload
            to_change.extend(changes)
            to_book.extend(bookings_)
            to_discard.extend(discards)

        # sending changes to database
        parsed_sectors.clear()
        margin_func = self._margins[cur_priority]
        db_manager.update_tickets(to_change, margin_func)

        # applying changes of tickets in local storage
        changes = {ticket[0]: ticket[1] for ticket in to_change}
        for scheme_name, parsed_name in sector_names:
            sector_all = self.sectors[scheme_name]
            for id_row_seat in sector_all:
                id_ = id_row_seat[0]
                if id_ not in changes:
                    continue
                sector_all[id_row_seat] = changes[id_]

        # applying changes of bookings in local storage
        self._bookings[cur_priority] = bookings.union(to_book)
        self._bookings[cur_priority] = bookings.difference(to_discard)
        if to_book or to_discard:
            self._update_prohibitions(cur_priority)

        self._lock.release()

    def _customize(self, scheme):
        db_tickets = db_manager.get_all_tickets(self.event_id)
        first_id = min(db_tickets.keys())
        try:
            for sector_name, sector_all in scheme.sectors.items():
                new_sector = {}
                self.sectors[sector_name] = new_sector
                for id_, row, seat in sector_all:
                    new_id = first_id + id_
                    new_ticket = (new_id, row, seat)
                    new_sector[new_ticket] = db_tickets[new_id]
        except KeyError:
            print(utils.red(f'Schema configuration was changed on event {self.event_id}!\n'
                            f'Scheme is {self.scheme_id}'))

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

        to_change = []

        for seat, seat_avail_subject in sector_all.items():
            ticket_id = seat[0]
            if seat_avail_subject:
                if (ticket_id in booking) and (ticket_id not in prohibited):
                    to_change.append((ticket_id, False,))
        return to_change

    @staticmethod
    def _handle_sector_list(sector_all, sector_parsed, prohibited, booking):
        to_change = []
        to_discard = []
        to_book = []

        for seat, seat_avail_subject in sector_all.items():
            row_seat = seat[1:]
            ticket_id = seat[0]

            if row_seat in sector_parsed:
                if not seat_avail_subject:
                    to_change.append((ticket_id, True,))
                to_book.append(ticket_id)
            else:
                if seat_avail_subject:
                    if (ticket_id in booking) and (ticket_id not in prohibited):
                        to_change.append((ticket_id, False,))
                to_discard.append(ticket_id)
        return to_change, to_book, to_discard

    @staticmethod
    def _handle_sector_dict(sector_all, sector_parsed, prohibited, booking):
        to_change = []
        to_discard = []
        to_book = []

        for seat, seat_avail_subject in sector_all.items():
            row_seat = seat[1:]
            ticket_id = seat[0]

            if row_seat in sector_parsed:
                if not seat_avail_subject:
                    price = sector_parsed[row_seat]
                    to_change.append((ticket_id, True, price,))
                to_book.append(ticket_id)
            else:
                if seat_avail_subject:
                    if (ticket_id in booking) and (ticket_id not in prohibited):
                        to_change.append((ticket_id, False,))
                to_discard.append(ticket_id)
        return to_change, to_book, to_discard


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
