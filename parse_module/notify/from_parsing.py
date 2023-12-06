import threading
import weakref
from abc import ABC
from typing import Union, Iterable

from loguru import logger

from .notifier import Notifier
from ..models.parser import EventParser, SeatsParser


class ParsingNotifier(Notifier, ABC):

    def __init__(self,
                 controller,
                 parser: Union[EventParser, SeatsParser],
                 name: str,
                 delay: float = None,
                 tele_profiles: Iterable = None,
                 print_minus: bool = False,
                 min_amount: int = 2,
                 min_increase: int = 5,
                 repeats_until_succeeded: int = 1):
        super().__init__(tele_profiles=tele_profiles)
        self.controller = controller
        self.parser = parser
        self.min_amount = min_amount
        self.min_increase = min_increase
        self.print_minus = print_minus
        self.repeats_until_succeeded = repeats_until_succeeded
        self.delay = 0
        self.step_counter = float('+inf')
        if name:
            self.name = f'Notifier ({name})'
        if delay:
            self.parser.delay = delay

        self._notifier_event = threading.Event()
        self._notifier_locker = threading.Event()
        self.parser.set_notifier(self._notifier_event, self._notifier_locker)
        if self.parser.last_state is not None and self.parser.error_timer == float('inf'):
            self.body(with_state=self.parser.last_state)
        self.stop = weakref.finalize(self, self._finalize_notifier)

    def _finalize_notifier(self):
        super().stop()
        self.parser.detach_notifier()

    def on_many_exceptions(self):
        self._notifier_event.clear()

    def run_try(self):
        self._notifier_event.wait()
        try:
            if not self.parser.stop.alive:
                self.stop()
            super().run_try()
        except Exception as err:
            raise err
        finally:
            self._notifier_event.clear()
        if not self._terminator.alive:
            return False


class EventNotifier(ParsingNotifier, ABC):

    def __init__(self,
                 controller,
                 event_parser: EventParser,
                 **kwargs):
        super().__init__(controller, event_parser, **kwargs)

    def body(self, with_state=None):
        skip_sending = False
        try:
            self._notifier_locker.set()
            events_chosen = with_state if with_state is not None else self.parser.events
            events_n_comments = {event_name: f'. **{date}**\n{url}' for event_name, url, date, _ in events_chosen}
        except Exception as err:
            raise err
        finally:
            self._notifier_locker.clear()
        parsed_event_names = list(events_n_comments)
        total_mes = '\n  '.join(f'{key}{value}' for key, value in events_n_comments.items())
        total_len = len(self.parser.name) + len(total_mes) + len(self.parser.url) + 100

        if total_len > 4096:
            events_n_comments = None
            total_mes = '\n  '.join(parsed_event_names)
            total_len = len(self.parser.name) + len(total_mes) + len(self.parser.url) + 100
        if total_len > 4096:
            self.tprint(f'{self.parser.name}\nМНОГО мероприятий добавлено\n\n'
                        f'Настолько много, что в сообщение не помещается')
            skip_sending = True

        self.change_ticket_state(self.parser.name, [], url=self.parser.url,
                                 appeared='События')
        self.change_ticket_state(f'**{self.parser.name}**', parsed_event_names,
                                 url=self.parser.url,
                                 appeared='События',
                                 separator='\n  ',
                                 comments=events_n_comments,
                                 skip_sending=skip_sending,
                                 print_minus=self.print_minus,
                                 repeats_until_succeeded=self.repeats_until_succeeded)


class SeatsNotifier(ParsingNotifier, ABC):

    def __init__(self,
                 controller,
                 seats_parser: SeatsParser,
                 event_id: int,
                 **kwargs):
        super().__init__(controller, seats_parser, **kwargs)
        self.event_id = event_id

    def body(self, with_state=None):
        try:
            self._notifier_locker.set()
            if with_state is None:
                parsed_sectors, parsed_dancefloors = self.parser.parsed_sectors, self.parser.parsed_dancefloors
            else:
                parsed_sectors, parsed_dancefloors = with_state
            sectors_dict = {sector_name: len(seats) for sector_name, seats in parsed_sectors.items()}
            dancefloors = [dancefloor for dancefloor, amount in parsed_dancefloors.items() if amount]
        except Exception as err:
            raise err
        finally:
            self._notifier_locker.clear()

        parser_name = f'**{self.parser.name}** ({self.parser.parent})'
        self.change_ticket_state(parser_name + ' танцполы', dancefloors,
                                 url=self.parser.url,
                                 print_minus=self.print_minus,
                                 repeats_until_succeeded=self.repeats_until_succeeded)
        self.change_ticket_state(parser_name, sectors_dict,
                                 url=self.parser.url,
                                 min_amount=self.min_amount,
                                 min_increase=self.min_increase,
                                 print_minus=self.print_minus,
                                 repeats_until_succeeded=self.repeats_until_succeeded)
