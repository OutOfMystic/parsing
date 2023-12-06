import json
import threading
import datetime as dt
from urllib.parse import urlparse, urlunparse

from loguru import logger
from urllib3.util import parse_url

from .margin import MarginRules
from .router import SchemeRouter
from ..utils.date import Date
from ..connection import db_manager
from ..utils import utils, provision


class SeatsParserGroup:
    def __init__(self, controller, parser_class):
        self.controller = controller
        self.parent_event = parser_class.event
        self.parser_class = parser_class
        self.name = f'{self.parser_class.event}.{self.parser_class.__name__}'
        self.url_filter = parser_class.url_filter
        self.parsers = []
        self._router = SchemeRouter()
        self.start_lock = threading.Lock()

    def bprint(self, mes, color=utils.Fore.GREEN):
        with open('main.log', 'a+') as f:
            row = {'name': self.name, 'mes': mes, 'color': color}
            f.write(json.dumps(row) + '\n')
        mes = f'Group ({self.name})| {utils.colorize(mes, color)}\n'
        print(mes, end='')

    def _add_data_from_db(self, event_data):
        matching_events = [parsed_data for parsed_data in self.controller.parsed_events
                           if crop_url(event_data['url']) == crop_url(parsed_data['url'])]
        for parsed_data in matching_events:
            event_data['parent'] = parsed_data['parent']
            event_data['extra'] = parsed_data['extra']
            event_data['event_name'] = parsed_data['event_name']
            event_data['venue'] = parsed_data['venue']

            #parsed_date = Date(parsed_data['date'])
            try:
                time_delta = event_data['date'].datetime() - parsed_data['date'].datetime()
            except AttributeError:
                continue
            if event_data['date'].is_outdated():
                continue
            elif abs(time_delta.seconds) > 900:
                continue
            else:
                return event_data

        if matching_events:
            parsed_data = matching_events[0]
            try:
                time_delta = event_data['date'].datetime() - parsed_data['date'].datetime()
            except AttributeError:
                return
            if event_data['date'].is_outdated():
                return
            elif abs(time_delta.seconds) > 900:
                self.bprint('Date mismatch in parsed event and in the database!\n'
                            f'    Parsed data: {event_data["event_name"]} {event_data["date"]} ({event_data["parent"]})\n'
                            f'    Database date: {parsed_data["date"]}', color=utils.Fore.YELLOW)

    def stop_by_margin(self, margin):
        provision.threading_try(self._stop_by_margin, name='MarginRoute', tries=1,
                            args=(margin,), to_except=self.start_lock.release, raise_exc=False)

    def _stop_by_margin(self, margin):
        self.start_lock.acquire()
        for parser in self.parsers:
            parser_margin = parser.scheme.restore_margin(parser.priority)
            if parser_margin == margin:
                parser.stop()
        self.start_lock.release()

    def update(self, connections):
        """
        Connection (parsing initial) keys format is:
        {priority, event_id, subject_date, url, margin_name, signature}
        """
        provision.threading_try(self._update, name='GroupGlobal', args=(connections,),
                                to_except=self.start_lock.release, tries=1, raise_exc=False)

    def _update(self, connections):
        self.start_lock.acquire()

        # Stopping outdated and deleted connections
        to_del = []
        signatures = [connection['signature'] for connection in connections]
        for i, parser in enumerate(self.parsers):
            if parser.signature not in signatures:
                to_del.append(i)
                continue
            subject_date = Date(parser.date)
            if subject_date.is_outdated(900):
                to_del.append(i)
        for parser_index in to_del[::-1]:
            parser = self.parsers[parser_index]
            parser.stop()
            del self.parsers[parser_index]

        # Checking if not outdated or alredy started
        parsing_initials = []
        for parsing_initial in connections:
            subject_date = parsing_initial['date']
            if subject_date.is_outdated(beforehand=900):
                continue
            if self._parser_already_started(parsing_initial):
                continue
            parsing_initials.append(parsing_initial)

        if not parsing_initials:
            self.start_lock.release()
            return

        prepared_data = []
        for event_data in parsing_initials:
            if 'parsing_id' in event_data:
                del event_data['parsing_id']
                prepared_data.append(event_data)
                continue
            event_data = self._add_data_from_db(event_data)
            if not event_data:
                continue
            if event_data['margin'] not in self.controller.margins:
                raise RuntimeError('Trying to get access to a non-existent margin name')
            prepared_data.append(event_data)

        if prepared_data:
            message = f'{len(prepared_data)} parsers will be launched'
            self.bprint(message)

        for event_data in prepared_data:
            provision.multi_try(self._start_parser, tries=3,
                                args=(event_data,), raise_exc=False,
                                name='Group', prefix=self.name)
        self.start_lock.release()

    def _start_parser(self, event_data):
        scheme = self._router.get_scheme(event_data['event_id'], event_data['scheme_id'])
        if scheme is provision.TryError:
            self.bprint(f'SEATS parser {self.parent_event} ({event_data["event_name"]}'
                        f' {event_data["date"]}) has not started: scheme error', color=utils.Fore.RED)
            return
        event_data['scheme'] = scheme
        margin_rules = self.controller.margins[event_data['margin']]
        event_data['margin'] = margin_rules
        scheme.bind(event_data['priority'], margin_rules)
        extra = event_data.pop('extra')
        event_data.update(extra)

        parser = self.parser_class(self.controller, **event_data)
        if self.controller.debug:
            parser.delay = 10
        parser.start()
        self.bprint(f'SEATS parser {self.parent_event} ({event_data["event_name"]}'
                    f' {event_data["date"]}) has started')
        self.parsers.append(parser)

    def _parser_already_started(self, new_parser):
        for parser in self.parsers:
            if parser.signature == new_parser['signature']:
                return True
        else:
            return False


def crop_url(url):
    url_details = urlparse(url)
    cur_netloc = url_details.netloc
    new_netloc = url_details.netloc.replace('www.', '')
    url = url.replace(cur_netloc, new_netloc)
    if '://' in url[:10]:
        url = url.split('://', 1)[1]
    if url.endswith('/'):
        url = url[:-1]
    return url


def get_col(array, col):
    cols = [row[col] for row in array]
    return cols