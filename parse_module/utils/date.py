import datetime as dt
import time
from calendar import monthrange


class Date:
    __slots__ = ('year', 'day', 'month', 'hour', 'minute')
    this_year = int(time.strftime('%Y'))

    def __init__(self, initial: (str, dt.datetime)):
        """
        Initial parameter ``initial`` can be of five formats:
         - ``datetime.datetime`` instance
         - "03 Sep 19:00"
         - "03 Sep 2023 19:00"
         - "03 Sep 2023"
         - "03 Sep"
        """
        self.year = 0
        self.day = 0
        self.month = 0
        self.hour = 0
        self.minute = 0
        self._parse_initial(initial)

    def __hash__(self):
        return self.delta()

    def __str__(self):
        month_str = month_list[self.month]
        year = f'{self.year} ' if self.year != self.this_year else ''
        hour = str(self.hour).zfill(2)
        minute = str(self.minute).zfill(2)
        return f'{self.day} {month_str} {year}{hour}:{minute}'

    def __repr__(self):
        return f'<date.Date object ({self.__str__()})>'

    def __sub__(self, other):
        if isinstance(other, (Date, Day, Month)):
            delta = self.datetime() - other.datetime()
            return delta.total_seconds()
        elif isinstance(other, dt.datetime):
            delta = self.datetime() - other
            return delta.total_seconds()
        else:
            raise TypeError(f'Can subtract only Date and datetime objects')

    def __eq__(self, other):
        if isinstance(other, (Date, Day, Month)):
            delta = self.datetime() - other.datetime()
            return delta.total_seconds() == 0
        elif isinstance(other, dt.datetime):
            delta = self.datetime() - other
            return delta.total_seconds() == 0
        else:
            raise TypeError(f'Can compare only Date and datetime objects')

    def __lt__(self, other):
        if isinstance(other, (Date, Day, Month)):
            delta = self.datetime() - other.datetime()
            return delta.total_seconds() < 0
        elif isinstance(other, dt.datetime):
            delta = self.datetime() - other
            return delta.total_seconds() < 0
        else:
            raise TypeError(f'Can compare only Date and datetime objects')

    def __ge__(self, other):
        return not self.__lt__(other) and not self.__eq__(other)

    @classmethod
    def now(cls):
        return cls(dt.datetime.now())

    def short(self):
        month_str = month_list[self.month]
        day_part = get_day_part(self.hour)
        return f'{self.day}_{month_str}_{day_part}'

    def _parse_datetime(self, datetime: dt.datetime):
        self.year = datetime.year
        self.month = datetime.month
        self.day = datetime.day
        self.hour = datetime.hour
        self.minute = datetime.minute

    def _parse_string(self, string):
        string = string.strip()
        if ':' in string and string.count(' ') == 3:
            day, month, year, time_ = string.split(' ')
        elif ':' in string and string.count(' ') == 2:
            day, month, time_ = string.split(' ')
            year = self.this_year
        elif string.count(' ') == 2:
            day, month, year = string.split(' ')
            time_ = '00:00'
        elif string.count(' ') == 1:
            day, month = string.split(' ')
            year = self.this_year
            time_ = '00:00'
        else:
            raise ValueError(f'Invalid date string format: {string}. Check docstring')
        self.year = int(year)
        self.month = month_num_by_str[month.capitalize()]
        self.day = int(day)
        hour, minute = time_.split(':')
        self.hour = int(hour)
        self.minute = int(minute)
        try:
            self.datetime()
        except:
            raise TypeError(f'Wrong date or time values! Check it properly: {self}')

    def _parse_initial(self, initial):
        if isinstance(initial, dt.datetime):
            self._parse_datetime(initial)
        elif isinstance(initial, str):
            self._parse_string(initial)
        elif isinstance(initial, Date):
            self._parse_datetime(initial.datetime())
        else:
            raise TypeError('Initial argument for a Date instance should be str or Date or datetime.datetime')

    def datetime(self):
        return dt.datetime(self.year, self.month, self.day, self.hour, self.minute)

    def delta(self):
        delta = self.datetime() - dt.datetime.now()
        seconds = delta.total_seconds()
        return int(seconds)

    def delta_datetime(self):
        return self.datetime() - dt.datetime.now()

    def is_outdated(self, beforehand=0):
        return self.delta() < beforehand


class Day(Date):
    __slots__ = tuple()

    def __init__(self, initial: (str, dt.datetime, Date)):
        """
        Initial parameter ``initial`` can be of four formats:
         - "03 Sep"
         - "03 Sep 2023"
         - ``datetime.datetime`` instance
         - ``Date`` instance
        """
        if isinstance(initial, Date):
            day = str(initial).split(' ')[:-1]
            day = ' '.join(day)
            super().__init__(day)
        else:
            super().__init__(initial)
        self.hour = 23
        self.minute = 59

    def __contains__(self, item: Date):
        assert isinstance(item, Date), 'Should be a Date class example'
        if item.day == self.day:
            if item.month == item.month:
                if item.year == item.year:
                    return True
        return False

    def __str__(self):
        month_str = month_list[self.month]
        # year = f' {self.year}' if self.year != self.this_year else ''
        return f'{self.day} {month_str} {self.year}'


class Month(Date):
    __slots__ = tuple()

    def __init__(self, initial: (str, dt.datetime, Date, Day)):
        """
        Initial parameter ``initial`` can be of five formats:
         - "Sep"
         - "Sep 2023"
         - ``datetime.datetime`` instance
         - ``Date`` instance
         - ``Day`` instance
        """
        if isinstance(initial, (Date, Day)):
            year = initial.year
            month = month_list[initial.month]
            str_month = f'{month} {year}'
            super().__init__(str_month)
            self._parse_initial(str_month)
        else:
            super().__init__(initial)
            self._parse_initial(initial)
        self.day = 27
        self.hour = 23
        self.minute = 59

    def __contains__(self, item: (Date, Day)):
        assert isinstance(item, Date), 'Should be a Date or Day class example'
        return self.month == item.month and self.year == item.year

    def __str__(self):
        month_str = month_list[self.month]
        return f'{month_str} {self.year}'

    def _parse_initial(self, initial):
        if isinstance(initial, dt.datetime):
            self._parse_datetime(initial)
        elif isinstance(initial, str):
            self._parse_string(initial)
        else:
            raise TypeError('Initial argument for Date instance should be str or datetime.datetime')

    def _parse_datetime(self, datetime: dt.datetime):
        self.year = datetime.year
        self.month = datetime.month

    def _parse_string(self, string):
        string = string.strip()
        if string.count(' ') == 1:
            month, year = string.split(' ')
        else:
            month = string
            year = self.this_year
        self.year = int(year)
        self.month = month_num_by_str[month.capitalize()]


def readable_datetime(datetime):
    year = datetime.year
    month = datetime.month
    day = datetime.day
    hour = datetime.hour
    minute = datetime.minute
    second = datetime.second
    msec = str(datetime.microsecond)[0]

    month_str = month_list[month]
    year = f'{year} ' if year != Date.this_year else ''
    hour = str(hour).zfill(2)
    minute = str(minute).zfill(2)
    return f'{day} {month_str} {year}{hour}:{minute}:{second}.{msec}'


def days_iterator(month):
    m = month.month
    y = month.year
    _, max_day = monthrange(y, m)
    for day in range(max_day):
        day += 1
        daytime = dt.datetime(year=y, month=m, day=day)
        yield Day(daytime)


def now():
    datetime = dt.datetime.now()
    return Date(datetime)


def get_day_part(hour):
    for range_ in day_parts:
        if hour in range_:
            return day_parts[range_]
    else:
        return 'н'


def native_issubitem(item, iterable):
    item_hash = hash(item)
    for dict_item in iterable:
        if hash(dict_item) == item_hash:
            return True
    else:
        return False


month_num_by_str = {
    "Янв": 1, "Фев": 2, "Мар": 3, "Апр": 4,
    "Май": 5, "Июн": 6, "Июл": 7, "Авг": 8,
    "Сен": 9, "Окт": 10, "Ноя": 11, "Дек": 12,
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    "Мая": 5
}
month_list = [
    "", "Янв", "Фев", "Мар", "Апр",
    "Май", "Июн", "Июл", "Авг",
    "Сен", "Окт", "Ноя", "Дек"
]
day_parts = {
    range(6, 13): "у",
    range(13, 16): "д",
    range(16, 21): "в"
}


def encode_month():
    return None