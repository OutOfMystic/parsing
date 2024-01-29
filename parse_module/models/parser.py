import time
import weakref
from abc import abstractmethod, ABC
from urllib.parse import urlparse

from ..manager import core, pooling
from ..connection import db_manager
from ..manager.proxy import check
from ..utils import utils, provision
from ..utils.date import Date
from ..utils.exceptions import ParsingError, ProxyHubError
from ..utils.logger import logger


RESTRICTED_COLUMNS = ['controller', 'event_id', 'event_name',
                      'url', 'date', 'signature', 'scheme',
                      'priority', 'parent', 'extra']


class ParserBase(core.Bot, ABC):
    proxy_check = check.NormalConditions()

    def __init__(self, controller):
        core.Bot.__init__(self, skip_postinit=True)
        ABC.__init__(self)
        self.controller = controller
        self.session = None
        self.last_state = None
        self.spreading = 0.2
        self._notifier = None

    def _get_proxy(self):
        self.proxy = self.controller.proxy_hub.get(self.proxy_check)
        if not self.proxy:
            raise ProxyHubError(f'Out of proxies!')

    def change_proxy(self, report=False):
        if report:
            self.controller.proxy_hub.report(self.proxy_check, self.proxy)
        self._get_proxy()
        self.before_body()

    def set_notifier(self, notifier):
        if self._notifier:
            self.error(f'Notifier for parser {self.name} has already been set. Refused.')
        else:
            self._notifier = notifier

    def detach_notifier(self):
        self._notifier = None

    def trigger_notifier(self):
        notifier = self._notifier
        if notifier:
            notifier.proceed()

    def proceed(self):
        start_time = time.time()
        next_step_delay = min(self.get_delay() / 15, 120)
        if self.proxy is None:
            self._debug_only('changing proxy', int((time.time() - start_time) * 10) / 10)
            provision.just_try(self._get_proxy, name=self.name)
            self._debug_only('changed proxy', int((time.time() - start_time) * 10) / 10)

        if self.proxy is not None:
            next_step_delay = self.get_delay()
            semaphore = self.proxy_check.get_proxy_semaphore(self.proxy)
            if semaphore:
                semaphore.acquire()
            if not self.fully_inited:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                provision.just_try(self.inthread_init, name=self.name)
                self._debug_only('inited', int((time.time() - start_time) * 10) / 10)
            if self.fully_inited and self._terminator.alive:
                self._debug_only('Proceeding', int((time.time() - start_time) * 10) / 10)
                super().proceed()
                self._debug_only('Proceeded', int((time.time() - start_time) * 10) / 10)
            else:
                next_step_delay = max(self.get_delay() / 7, 300)
            if semaphore:
                semaphore.release()

        if self._terminator.alive:
            task = pooling.Task(self.proceed, self.name, next_step_delay)
            self.controller.pool.add_task(task)
            self._debug_only('Pooled', int((time.time() - start_time) * 10) / 10)

    def _debug_only(self, mes, *args):
        if self.controller.debug:
            self.debug(mes, *args)

    def start(self, start_delay=0):
        task = pooling.Task(self.proceed, self.name, start_delay)
        self.controller.pool.add_task(task)


class EventParser(ParserBase, ABC):

    def __init__(self, controller, name):
        super().__init__(controller)
        self.name = f'EventParser ({name})'
        self._db_name = name
        self.events = {}
        self._new_condition = {}
        self.stop = weakref.finalize(self, self._finalize_parser)

    def _finalize_parser(self):
        super().stop()
        self.trigger_notifier()

    def _change_events_state(self):
        to_remove, _, to_add = utils.differences(self.events, self._new_condition)

        if to_remove:
            new_to_remove = [old_to_remove[:3] for old_to_remove in to_remove]
            db_manager.remove_parsed_events(new_to_remove)
            # db_manager.remove_parsed_events(to_remove)
        for event in to_remove:
            del self.events[event]

        events_to_add = {data: self._new_condition[data] for data in to_add}
        self._add_events(events_to_add)
        self.events.update(events_to_add)

    def _add_events(self, events_to_send):
        listed_events = []
        for event_name, url, date, hash_ in events_to_send:
            columns = self._new_condition[event_name, url, date, hash_]
            columns = columns.copy()
            if date is None:
                date = "null"
            date = str(date)
            venue = columns.pop('venue')
            if venue is None:
                venue = "null"
            listed_event = [
                self._db_name, event_name,
                url, venue, columns, date
            ]
            listed_events.append(listed_event)
        if listed_events:
            db_manager.add_parsed_events(listed_events)

    def register_event(self, event_name, url, date=None,
                       venue=None, **columns):
        event_name = event_name.replace('\n', ' ')
        if venue is not None:
            venue = venue.replace('\n', ' ')
        columns['venue'] = venue
        for restricted in RESTRICTED_COLUMNS:
            if restricted in columns:
                raise RuntimeError(f'`{restricted}` parameter is restricted for registration. Rename it')
        formatted_date = str(Date(date))
        aliased_name = self.controller.event_aliases[event_name]
        cols_hash = utils.get_dict_hash(columns)
        self._new_condition[aliased_name, url, formatted_date, cols_hash] = columns

    def run_try(self):
        super().run_try()

        if self.step == 0:
            db_manager.delete_parsed_events(self._db_name)
        self._change_events_state()
        self.last_state = self._new_condition.copy()
        self._new_condition.clear()
        self.trigger_notifier()


class SeatsParser(ParserBase, ABC):
    url_filter = lambda event: 'ticketland.ru' in event

    def __init__(self, controller, event_id, event_name,
                 url, date, venue, signature, scheme,
                 priority, parent, **extra):
        super().__init__(controller)
        self.event_id = event_id
        self.event_name = event_name
        self.url = url
        self.date = date
        self.venue = venue
        self.signature = signature
        self.scheme = scheme
        self.priority = priority
        self.parent = parent
        self.step_counter = 10
        self.domain = str(urlparse(self.url).hostname).replace('www.', '')
        self.name = self._format_name()

        self._set_extra(extra)
        self.parsed_sectors = {}
        self.parsed_dancefloors = {}
        self.stop = weakref.finalize(self, self._finalize_parser)

    def register_sector(self, sector_name, seats):
        """
        Registers sector ``sector_name`` during ``body``
        execution. ``seats`` should be formatted like:
         - ``{(row1, seat1): price1, (row2, seat2): price2, ...}``,

        :param sector_name: the same name as in database
        :param seats: list or dict of seats data
        """
        assert isinstance(seats, (dict, tuple)), \
            'Wrong seats data format, should be iterable'
        lower_sectors = (sector.lower() for sector in self.scheme.sector_names)
        if sector_name.lower() not in lower_sectors:
            mes = f"Sector '{sector_name}' wasn\'t found on the scheme! {self.url}"
            if hasattr(self, 'venue'):
                mes += f' {self.venue}'
            self.warning(mes)

        if seats:
            # f isinstance(seats, dict):
            row, seat = list(seats.keys())[0]
            price = seats[row, seat]
            assert isinstance(row, str), ('row is not a string, got '
                                          f'{type(row).__name__} ({row}) instead')
            assert isinstance(seat, str), ('seat is not a string, got '
                                           f'{type(seat).__name__} ({seat}) instead')
            assert isinstance(price, int), ('price is not an integer, got '
                                            f'{type(price).__name__} ({price}) instead')
            """else:
                row, seat = seats[0]
                assert isinstance(row, str), ('row is not a string, got '
                                              f'{type(row).__name__} ({row}) instead')
                assert isinstance(seat, str), ('seat is not a string, got '
                                               f'{type(seat).__name__} ({seat}) instead')"""

        """if sector_name in self.parsed_sectors:
            if isinstance(seats, tuple):
                seats = list(seats)
            if isinstance(seats, list):
                self.parsed_sectors[sector_name] += seats
            elif isinstance(seats, dict):
                self.parsed_sectors[sector_name].update(seats)
        else:
            if isinstance(seats, tuple):
                seats = list(seats)
            self.parsed_sectors[sector_name] = seats"""

        if sector_name in self.parsed_sectors:
            self.parsed_sectors[sector_name].update(seats)
        else:
            self.parsed_sectors[sector_name] = seats

    def register_dancefloor(self, sector_name, price, amount=1000):
        """
        Registers sector ``sector_name`` of dance floor type
        with ``amount`` number of tickets. ``amount`` should be
        specified only in certain cases. e.g., to limit table
        seats to 4.

        :param sector_name: the same name as in database
        :param amount: amount of available tickets
        """
        lower_sectors = (sector.lower() for sector in self.scheme.dancefloors)
        if sector_name.lower() not in lower_sectors:
            mes = f"Dance floor sector '{sector_name}' wasn\'t found on the scheme! {self.url}"
            self.bprint(mes, color=utils.Fore.YELLOW)
        if sector_name in self.parsed_dancefloors:
            raise ParsingError(f'Sector name {sector_name} is already registered')
        else:
            self.parsed_dancefloors[sector_name] = (price, amount,)

    def print_sectors_level1(self):
        """
        Helping utility which prints sector names
        on scheme stored in database
        """
        sector_names = self.scheme.sector_names
        sector_names_str = ', '.join(sector_names)
        self.bprint('Sector names available: ' + sector_names_str)

    def print_sectors_level2(self):
        """
        Helping utility which prints detailed data for each sector:
         - sector name
         - row range
         - seats range
         - id range
        """
        to_print = ['Sector scheme:']
        for name, id_range, row_range, seat_range in self.scheme.sector_data:
            str_data = (f'{utils.red(name)} ranges: '
                        f'rows {format_range(id_range)} '
                        f'seats {format_range(row_range)} '
                        f'ids {format_range(seat_range)}')
            to_print.append(str_data)
        combined_rows = '\n'.join(to_print)
        self.bprint(combined_rows)

    def check_sectors(self):
        db_sectors = self.scheme.sector_names
        parsed_sectors = self.parsed_sectors.keys()
        db_sectors = list(db_sectors)
        parsed_sectors = list(parsed_sectors)
        if not db_sectors:
            self.bprint('Got empty scene from the database', color=utils.Fore.RED)
            return
        if not parsed_sectors:
            self.bprint('No sector has been parsed', color=utils.Fore.YELLOW)
        missing, found, extra = utils.differences(db_sectors, parsed_sectors)

        print_mes = ''
        missing_mes = ('Missing sectors. These sectors were '
                       'not registered, but should be')
        print_mes += format_sectors_block(missing_mes, missing, utils.Fore.YELLOW)
        extra_mes = ('Extra sectors. These sectors are unexpected '
                     'and must be removed')
        print_mes += format_sectors_block(extra_mes, extra, utils.Fore.RED)
        found_mes = 'Found sectors. They were registered correctly'
        print_mes += format_sectors_block(found_mes, found, utils.Fore.LIGHTGREEN_EX)
        print(print_mes, end='')
        input(utils.green('Press enter to continue...\n'))

    def _format_name(self):
        event_name = self.event_name.replace(' - ', '-') \
                                    .replace('\n', ' ') \
                                    .replace(' ', '-')[:12]
        scheme_name = self.scheme.name[:20].replace(' ', '-')
        date = self.date.short()
        return f'#{self.event_id} {event_name} {date} {scheme_name} {self.domain}'

    def _set_extra(self, extra):
        for attr, value in extra.items():
            setattr(self, attr, value)

    def _finalize_parser(self):
        super().stop()
        self.scheme.unbind(self.priority)

    def run_try(self):
        if not self.stop.alive:
            return False
        if self.driver:
            self.driver.get(self.url)

        self._debug_only('body started')
        self.body()
        self._debug_only('body finished')

        if self.stop.alive:
            self.trigger_notifier()
            self.last_state = (self.parsed_sectors.copy(), self.parsed_dancefloors.copy(),)
            self._debug_only('releasing sectors')
            self.scheme.release_sectors(self.parsed_sectors, self.parsed_dancefloors,
                                        self.priority, self.name)
            self._debug_only('released sectors')
            self.parsed_sectors.clear()
            self.parsed_dancefloors.clear()

    def run_except(self):
        self.parsed_sectors.clear()
        super().run_except()

    @abstractmethod
    async def body(self):
        pass


def format_sectors_block(mes, sectors, color):
    if not sectors:
        return ''

    sectors_rows = []
    row_len = 0
    last_row = []
    for sector in sectors:
        row_len += len(sector) + 2
        if row_len < 70:
            last_row.append(sector)
        else:
            sectors_rows.append(last_row)
            last_row = [sector]
            row_len = len(sector) + 2
    else:
        if last_row:
            sectors_rows.append(last_row)

    print_block = mes + '\n'
    for row in sectors_rows:
        gen = (utils.colorize(sector, color) for sector in row)
        delimiter = utils.blue('; ')
        str_row = '    ' + delimiter.join(gen)
        print_block += str_row + '\n'
    return print_block


def format_range(range_):
    if range_[0] == range_[1]:
        formatted = str(range_[0])
        return utils.green(formatted)
    elif range_[0] == -float('inf'):
        return utils.red('<EMPTY>')
    else:
        formatted = str(range_)
        return utils.green(formatted)
