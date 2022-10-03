import threading
import time

from .scheme import ParserScheme
from .margin import MarginRules
from .router import SchemeRouter
from ..utils.date import Date
from ..connection import db_manager
from ..utils import utils, provision


class SeatsParserGroup:
    def __init__(self, controller, parser_class):
        self.controller = controller
        self.parent_event = parser_class.event
        self.router = SchemeRouter()
        self.parser_class = parser_class
        self.name = f'{self.parser_class.event}.{self.parser_class.__name__}'
        self.url_filter = parser_class.url_filter
        self.parsers = []
        self._start_lock = threading.Lock()

    def bprint(self, mes, color=utils.Fore.GREEN):
        mes = f'Group ({self.name})| {utils.colorize(mes, color)}\n'
        print(mes, end='')

    def _get_event_data_from_db(self, subject_url):
        events_data = db_manager.get_parsed_events()
        try:
            for event_name, object_url, venue, create_time, extra, date in events_data:
                if subject_url == object_url:
                    return event_name, object_url, date, venue, create_time, extra
            else:
                return None
        except:
            print(events_data)

    @staticmethod
    def format_event_data(event_data, parsing_initial):
        # GETTING EVENTS FROM DATABASE YOUNGER THAN DElAY
        subject_id, priority, subject_url, margin_name = parsing_initial

        if event_data is None:
            return None
        event_name, url, date, venue, create_time, extra = event_data
        all_data = [
            subject_id, priority, margin_name,
            event_name, url, Date(date), venue,
            parsing_initial
        ]
        return list(all_data), extra

    def update(self, connections):
        threading.Thread(target=self._update, args=(connections,)).start()

    def _update(self, connections):
        try:
            self._start_lock.acquire()
            for i, parser in enumerate(self.parsers):
                if parser.parsing_initial not in connections:
                    del parser
                    del self.parsers[i]

            parsing_initials = []
            for parsing_initial in connections:
                if not self._parser_already_started(parsing_initial):
                    parsing_initials.append(parsing_initial)
            for event_data, extra in self._event_data_prepared(parsing_initials):
                provision.multi_try(self._start_parser_and_add_data, tries=3,
                                    args=(event_data, extra), raise_exc=False,
                                    name='Group', prefix=self.name)
        except Exception as err:
            self.bprint(f'Global error starting parsers: {err}', color=utils.Fore.RED)
        finally:
            self._start_lock.release()

    def _start_parser_and_add_data(self, event_data, extra):
        priority, subject_id, margin_name = event_data[:3]
        margin_rules = db_manager.get_margin(margin_name)
        margin = MarginRules(margin_rules)

        scheme = self.router.get_scheme(subject_id)
        scheme.bind(priority, margin)

        event_data.append(scheme)
        event_data.append(priority)

        parser = self.parser_class(self.controller, *event_data[3:], **extra)
        parser.start()
        self.bprint(f'SEATS parser {self.parent_event} ({event_data[3]} {event_data[5]}) has started')
        self.parsers.append(parser)

    def _event_data_prepared(self, parsing_initials):
        for parsing_initial in parsing_initials:
            subject_url = parsing_initial[2]
            event_data = self._get_event_data_from_db(subject_url)
            if event_data is None:
                #self.bprint('Couldn\'t find event data for ' + subject_url, color=utils.Fore.YELLOW)
                continue
            yield self.format_event_data(event_data, parsing_initial)

    def _parser_already_started(self, url):
        for parser in self.parsers:
            if parser.url == url:
                return True
        else:
            return False
