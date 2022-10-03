import datetime as dt
import time


class Date:
    this_year = int(time.strftime('%Y'))

    def __init__(self, initial: str):
        """
        Initial parameter ``initial`` can be of four formats:
         - ``datetime.datetime`` instance
         - "03 Sep 19:00"
         - "03 Sep 2023 19:00"
         - "03 Sep 2023"
        """
        self.year = 0
        self.day = 0
        self.month = 0
        self.hour = 0
        self.minute = 0
        self._parse_initial(initial)

    def __str__(self):
        month_str = month_list[self.month]
        year = f'{self.year} ' if self.year != self.this_year else ''
        hour = str(self.hour).zfill(2)
        minute = str(self.minute).zfill(2)
        return f'{self.day} {month_str} {year}{hour}:{minute}'

    def short(self):
        month_str = month_list[self.month].lower()
        hour = str(self.hour).zfill(2)
        return f'{self.day}{month_str}{hour}'

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
        else:
            raise ValueError('Invalid date string format. Check docstring')
        self.year = int(year)
        self.month = month_num_by_str[month.capitalize()]
        self.day = int(day)
        hour, minute = time_.split(':')
        self.hour = int(hour)
        self.minute = int(minute)

    def _parse_initial(self, initial):
        if isinstance(initial, dt.datetime):
            self._parse_datetime(initial)
        elif isinstance(initial, str):
            self._parse_string(initial)
        else:
            raise TypeError('Initial argument for Date instance should be str or datetime.datetime')

    def datetime(self):
        return dt.datetime(self.year, self.month, self.day, self.hour, self.minute)

    def delta(self):
        delta = dt.datetime.now() - self.datetime()
        seconds = delta.total_seconds()
        return int(seconds)

    def delta_datetime(self):
        delta = dt.datetime.now() - self.datetime()
        return delta


month_num_by_str = {
    "Янв": 1, "Фев": 2, "Мар": 3, "Апр": 4,
    "Май": 5, "Июн": 6, "Июл": 7, "Авг": 8,
    "Сен": 9, "Окт": 10, "Ноя": 11, "Дек": 12,
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}
month_list = [
    "", "Янв", "Фев", "Мар", "Апр",
    "Май", "Июн", "Июл", "Авг",
    "Сен", "Окт", "Ноя", "Дек"
]