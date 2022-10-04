import time

from ..manager import core
from ..connection import db_manager
from ..utils import utils
from ..utils.date import Date
from ..utils.parse_utils import double_split


class EventParser(core.BotCore):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.events = {}
        self._new_condition = {}
        self._events_state = []
        self.session = None

    def _change_events_state(self):
        to_remove, _, to_add = utils.differences(self.events, self._new_condition)

        if to_remove:
            db_manager.remove_parsed_events(to_remove)
        for event in to_remove:
            del self.events[event]

        events_to_add = {data: self._new_condition[data] for data in to_add}
        self._add_events(events_to_add)
        self.events.update(events_to_add)

    def _add_events(self, events_to_send):
        listed_events = []
        for event_name, url, date in events_to_send:
            columns = self._new_condition[event_name, url, date]
            columns = columns.copy()
            if date is None:
                date = "null"
            date = str(date)
            venue = columns.pop('venue')
            if venue is None:
                venue = "null"
            listed_event = [
                self.name, event_name, columns['create_time'],
                url, venue, columns, date
            ]
            listed_events.append(listed_event)
        if listed_events:
            db_manager.add_parsed_events(listed_events)

    def register_event(self, event_name, url, date=None,
                       venue=None, **columns):
        columns['venue'] = venue
        columns['create_time'] = int(time.time())
        formatted_date = str(Date(date))
        self._new_condition[event_name, url, formatted_date] = columns

    def run_try(self):
        super().run_try()
        if self.step == 0:
            db_manager.delete_parsed_events(self.name)
        self._change_events_state()
        self._new_condition.clear()

    def run(self):
        self.proxy = self.controller.proxy_hub.get()
        super().run()


class SeatsParser(core.BotCore):
    event = 'Parent Event'
    url_filter = lambda event: 'ticketland.ru' in event

    def __init__(self, controller, *event_data, **extra):
        super().__init__()
        self.controller = controller
        self.event_name, self.url, self.date, \
            self.venue, self.parsing_initial, \
            self.scheme, self.priority = event_data
        self.domain = double_split(self.url, '://', '/')
        self.name = self._format_name()
        self.session = None
        self._set_extra(extra)
        self._parsed_sectors = {}

    def __del__(self):
        self.scheme.unbind(self.priority)

    def register_sector(self, sector_name, seats):
        """
        Registers sector ``sector_name`` during ``body``
        execution. ``seats`` can be of two formats:
         - ``{(row1, seat1): price1, (row2, seat2): price2, ...}``,
         - ``[[row1, seat1], [row2, seat2], ...]``
        It's desirable to use the first one

        :param sector_name: the same name as in database
        :param seats: list or dict of seats data
        """
        assert isinstance(seats, (dict, list, tuple)), \
            'Wrong seats data format: should be iterable'
        assert sector_name not in self._parsed_sectors, \
            f"Sector '{sector_name}' has already been registered"
        lower_sectors = (sector.lower() for sector in self.scheme.sectors)
        if sector_name.lower() not in lower_sectors:
            mes = f"Sector '{sector_name}' wasn\'t found on the scheme, being ignored!"
            self.bprint(mes, color=utils.Fore.YELLOW)

        if seats:
            if isinstance(seats, dict):
                row, seat = list(seats.keys())[0]
                price = seats[row, seat]
                assert isinstance(row, int), ('row is not an integer, got '
                                              f'{type(row).__name__} instead')
                assert isinstance(seat, int), ('row is not an integer, got '
                                               f'{type(seat).__name__} ({seat}) instead')
                assert isinstance(price, int), ('row is not an integer, got '
                                                f'{type(price).__name__} ({price}) instead')
            else:
                row, seat = seats[0]
                assert isinstance(row, int), ('row is not an integer, got '
                                              f'{type(row).__name__} ({row}) instead')
                assert isinstance(seat, int), ('seat is not an integer, got '
                                               f'{type(seat).__name__} {type(seat)} ({seat}) instead')
        self._parsed_sectors[sector_name] = seats

    def print_sectors_level1(self):
        """
        Helping utility which prints sector names
        on scheme stored in database
        """
        sector_names = self.scheme.sector_names()
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
        for name, id_range, row_range, seat_range in self.scheme.sector_data():
            str_data = (f'{utils.red(name)} ranges: '
                        f'rows {format_range(id_range)} '
                        f'seats {format_range(row_range)} '
                        f'ids {format_range(seat_range)}')
            to_print.append(str_data)
        combined_rows = '\n'.join(to_print)
        self.bprint(combined_rows)

    def check_sectors(self):
        db_sectors = self.scheme.sector_names()
        parsed_sectors = self._parsed_sectors.keys()
        db_sectors = list(db_sectors)
        parsed_sectors = list(parsed_sectors)
        if not db_sectors:
            self.bprint('Got empty scene from database', color=utils.Fore.RED)
            return
        if not parsed_sectors:
            self.bprint('Any parsed sectors were registered', color=utils.Fore.YELLOW)
            return
        missing, found, extra = utils.differences(db_sectors, parsed_sectors)

        print_mes = ''
        missing_mes = ('Missing sectors. These sectors were '
                       'not registered, but should be')
        print_mes += format_sectors_block(missing_mes, missing, utils.Fore.YELLOW)
        extra_mes = ('Extra sectors. These sectors are unexpected '
                     'and must be removed')
        print_mes += format_sectors_block(extra_mes, extra, utils.Fore.RED)
        found_mes = 'Found sectors. They were registered correctly'
        print_mes += format_sectors_block(found_mes, found, utils.Fore.GREEN)
        print(print_mes, end='')
        input(utils.green('Press enter to continue...\n'))

    def _format_name(self):
        event_name = self.event_name.replace(' - ', '-') \
                                    .replace('\n', ' ')[:12]
        date = self.date.short()
        return f'{event_name} {date} {self.scheme.name}'

    def _set_extra(self, extra):
        for attr, value in extra.items():
            setattr(self, attr, value)

    def run_try(self):
        if self.terminator:
            return False
        if self.driver:
            self.driver.get(self.url)
        self.body()
        self.scheme.release_sectors(self._parsed_sectors, self.priority)
        self._parsed_sectors.clear()

    def run_except(self):
        self._parsed_sectors.clear()
        super().run_except()

    def body(self):
        pass

    def run(self):
        self.proxy = self.controller.proxy_hub.get()
        super().run()


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


def format_range(range):
    if range[0] == range[1]:
        formatted = str(range[0])
        return utils.green(formatted)
    elif range[0] == -float('inf'):
        return utils.red('<EMPTY>')
    else:
        formatted = str(range)
        return utils.green(formatted)

