import json
import os
import time
from abc import ABC
from typing import Union, Iterable

import requests
from loguru import logger

from ..manager.backstage import tasker
from ..manager.core import ThreadedBot
from ..manager.proxy import check
from ..manager.proxy.instances import UniProxy
from ..manager.proxy.loader import ProxyHub
from ..manager.telecore import tele_core
from ..utils import utils
from ..utils.provision import try_open


class Notifier(ThreadedBot, ABC):
    proxy_check = check.NormalConditions()

    def __init__(self,
                 proxy: UniProxy = None,
                 proxy_hub: ProxyHub = None,
                 tele_profiles: Iterable = None):
        if proxy and proxy_hub:
            raise SyntaxWarning('Use proxy_hub or proxy parameter, not both.\nProxy argument will be taken.')
        elif proxy_hub:
            proxy = proxy_hub.get(self.proxy_check)
        super().__init__(proxy=proxy)
        self.proxy_hub = proxy_hub
        self.tele_bool = True
        self.tele_profiles = tele_profiles if tele_profiles else []
        self.tickets_state = {}
        self.tele_ids = tele_core.get_tele_ids(self.tele_profiles)

        self._last_call = time.time()
        self._default_delay = self.delay
        self._check_counter = {}
        self._events_to_check = {}
        self._events_state = {}
        self._first_change = []
        self._last_update = None

    def tprint(self,
               message: str,
               tele_name: str = 'notifications'):
        tele_core.send_message(str(message), self.tele_ids, tele_name)

    def cprint(self,
               message: str):
        if (time.time() - self._last_call) < 600:
            return False
        self._last_call = time.time()

        json_path = os.path.join('config', 'phones.json')
        if self.tele_bool:
            with open(json_path, 'r') as read_file:
                phones_arr = json.load(read_file)
        else:
            phones_arr = []

        log_mes = 'ЗВОНОК: ' + message + '\n'
        with open(r'log.txt', 'a', encoding='utf-8') as logs:
            logs.write(log_mes)

        phones = ';'.join(phones_arr)
        params = {
           'login': 'OutOfMystic',
           'psw': 'Vlad12345123@',
           'phones': phones,
           'mes': message,
           'call': '1'
           }
        requests.get('https://smsc.ru/sys/send.php', params=params)
        self.bprint(message)
        return True

    def _check_for_repeat(self, key, to_state, repeat_delay,
                          repeats_trigger_amount=1):
        if repeats_trigger_amount == 1:
            return True
        if key not in self._check_counter:
            self._check_counter[key] = 0
        if isinstance(to_state, str):
            events_bool = to_state == self.tickets_state[key]
        else:
            new_events = [event for event in to_state if event not in self.tickets_state[key]]
            old_events = [event for event in self.tickets_state[key] if event not in to_state]
            events_bool = new_events or old_events
        if self._check_counter[key] == 0:
            if events_bool:
                self._events_to_check[key] = to_state
                self._check_counter[key] = 1
                self.delay = repeat_delay
                self.bprint('Detected different value, starting check (1)')
                return False
            else:
                return True
        else:
            new_events_check = [event for event in to_state if event not in self._events_to_check[key]]
            old_events_check = [event for event in self._events_to_check[key] if event not in to_state]
            events_check_bool = new_events_check or old_events_check
            if events_check_bool:
                if not events_bool:
                    self.delay = self._default_delay
                    self.bprint(utils.yellow(f'Changes declined ({self._check_counter[key] + 1})'))
                    self._check_counter[key] = 0
                    return False
                else:
                    self.delay = repeat_delay
                    self.bprint(utils.yellow(f'Bot has got new instant changes ({self._check_counter[key]})'))
                    self._check_counter[key] = 0
                    self.tickets_state[key] = to_state
                    return False
            else:
                self._check_counter[key] += 1
                if self._check_counter[key] == repeats_trigger_amount:
                    self.bprint(f'Value changes accepted ({self._check_counter[key]})')
                    self._check_counter[key] = 0
                    self.delay = self._default_delay
                    return True
                else:
                    self.delay = repeat_delay
                    self.bprint(f'Checking values ({self._check_counter[key]})')
                    return False

    def change_ticket_state(self,
                            event_name: str,
                            new_state: Union[str, list, dict],
                            url='',
                            comments: dict = None,
                            appeared='билеты',
                            separator='\n',
                            print_minus=True,
                            min_increase=5,
                            min_amount=2,
                            repeats_until_succeeded=1,
                            repeater_delay=5,
                            cprint=False,
                            only_first=False,
                            skip_sending=False):
        """
        Main ``Notifier`` function. You send tickets' state stored in
        ``new_state`` to a system by a specified ``event_name``

        ``to_state`` type can be a ``bool``, ``list`` or ``dict``.
        Each type specifies its special behavior.
        ``dict`` is more preferred than ``list``,
        ``list`` is more preferred than ``bool``

        NEVER INSPECT THE CODE!!! ТУТ СТРАШНО
        """

        if comments is None:
            comments = {}

        self._last_update = time.asctime()
        to_plus = []
        first_plus = []
        appeared_upper = appeared.capitalize()
        if isinstance(new_state, list):
            if event_name not in self.tickets_state:
                self.tickets_state[event_name] = new_state
            if event_name not in self._events_state:
                self._events_state[event_name] = []
            if event_name not in self._first_change:
                self._events_state[event_name] = list(set(self._events_state[event_name]) | set(new_state))
                tasker.put(self._events_state_write, event_name)
                self._first_change.append(event_name)

            no_repeat = self._check_for_repeat(event_name, new_state, repeater_delay,
                                               repeats_trigger_amount=repeats_until_succeeded)
            if (set(self.tickets_state[event_name]) != set(new_state)) and no_repeat:
                mes = ''
                to_minus = [i for i in self.tickets_state[event_name] if i not in new_state]
                to_plus = [i for i in new_state if i not in self.tickets_state[event_name]]
                to_first_plus = [i for i in new_state if i not in self._events_state[event_name]]  # отсеиваю не новые
                if isinstance(comments, dict):
                    minus = [f'{state}{comments[state]}' for state in to_minus if state in comments]
                    minus += [f'{state}' for state in to_minus if state not in comments]
                    plus = [f'{state}{comments[state]}' for state in to_plus if state in comments]
                    plus += [f'{state}' for state in to_plus if state not in comments]
                    first_plus = [f'{state}{comments[state]}' for state in to_first_plus if state in comments]
                    first_plus += [f'{state}' for state in to_first_plus if state not in comments]
                else:
                    minus = [f'{state}{comment}' for state, comment in zip(to_minus, comments)]
                    plus = [f'{state}{comment}' for state, comment in zip(to_plus, comments)]
                    first_plus = [f'{state}{comment}' for state, comment in zip(to_first_plus, comments)]
                psep = ',' + separator
                if first_plus:
                    self._check_events_state(event_name, plus, first_plus)
                    first_plus_mes = psep.join(first_plus)
                    first_plus_mes = f"ВПЕРВЫЕ появились {appeared}. {event_name}: {separator}{first_plus_mes}\n"
                    mes += first_plus_mes
                if plus and not only_first:
                    plus_mes = psep.join(plus)
                    mes += f"Появились {appeared}. {event_name}:{separator}{plus_mes}"
                    if cprint:
                        self.cprint('Ахтунг. ' + mes)
                if print_minus:
                    if plus and minus:
                        mes += '\n'
                    if minus and not only_first:
                        minus_mes = psep.join(minus)
                        mes += f"{appeared_upper} исчезли из продажи. {event_name}:{separator}{minus_mes}"

                mes += f'\n{url}'
                if skip_sending:
                    pass
                elif only_first:
                    if first_plus:
                        self.tprint(mes)
                elif print_minus:
                    self.tprint(mes)
                else:
                    if plus or first_plus:
                        self.tprint(mes)
            if no_repeat:
                self.tickets_state[event_name] = new_state
            if first_plus:
                tasker.put(self._events_state_write, event_name)
            return to_plus
        elif isinstance(new_state, dict):
            refreshed_state = {}
            only_plus = []
            for i in new_state:
                if isinstance(new_state[i], str) or (new_state[i] >= min_amount):
                    refreshed_state[i] = new_state[i]
            if not (event_name in self.tickets_state):
                self.tickets_state[event_name] = refreshed_state.copy()
            if event_name not in self._events_state:
                self._events_state[event_name] = []
            if event_name not in self._first_change:
                united = set(self._events_state[event_name]) | set(self.tickets_state[event_name].keys())
                self._events_state[event_name] = list(united)
                tasker.put(self._events_state_write, event_name)
                self._first_change.append(event_name)

            no_repeat = self._check_for_repeat(event_name, new_state, repeater_delay,
                                               repeats_until_succeeded)
            if (self.tickets_state[event_name] != refreshed_state) and no_repeat:
                to_minus = [[i, self.tickets_state[event_name][i]] for i in self.tickets_state[event_name] if
                            i not in refreshed_state]
                to_plus = [[i, refreshed_state[i]] for i in refreshed_state if i not in self.tickets_state[event_name]]
                only_plus = [plus[0] for plus in to_plus]
                to_increase = []  # возможно снизу надо if not in self.tickets_state добавить
                to_first_plus = [[i, refreshed_state[i]] for i in refreshed_state if
                                 i not in self._events_state[event_name]]  # отсеиваю не новые
                only_first_plus = [f_plus[0] for f_plus in to_first_plus]
                for i in refreshed_state:
                    if i in self.tickets_state[event_name]:
                        if isinstance(refreshed_state[i], int):
                            if refreshed_state[i] > self.tickets_state[event_name][i]:
                                start = self.tickets_state[event_name][i]
                                diverg = refreshed_state[i] - start
                                if diverg >= min_increase:
                                    to_append = [i, diverg, start]
                                    to_increase.append(to_append)
                if isinstance(comments, dict):
                    minus = [f'{state[0]}{comments[state[0]]}' for state in to_minus if state[0] in comments]
                    minus += [f'{state[0]}' for state in to_minus if state[0] not in comments]
                    plus = [f'{state[0]}|{state[1]}{comments[state[0]]}' for state in to_plus if state[0] in comments]
                    plus += [f'{state[0]}|{state[1]}' for state in to_plus if state[0] not in comments]
                    first_plus = [f'{state[0]}|{state[1]}{comments[state[0]]}' for state in to_first_plus if
                                  state[0] in comments]
                    first_plus += [f'{state[0]}|{state[1]}' for state in to_first_plus if state[0] not in comments]
                    increase = [f'{state[0]}|{state[2]}{comments[state[0]]}| + {state[1]}шт' for state in to_increase if
                                state[0] in comments]
                    increase += [f'{state[0]}|{state[2]}|+{state[1]}шт' for state in to_increase if
                                 (state[0] not in comments)]
                else:
                    minus = [f'{state[0]}{comment}' for state, comment in zip(to_minus, comments)]
                    plus = [f'{state[0]}|{state[1]}{comment}' for state, comment in zip(to_plus, comments)]
                    first_plus = [f'{state[0]}|{state[1]}{comment}' for state, comment in zip(to_first_plus, comments)]
                    increase = [f'{state[0]}{comment}|+{state[1]}шт' for state, comment in zip(to_increase, comments)]
                psep = ',' + separator
                to_mes = []
                if first_plus:
                    self._check_events_state_dict(event_name, plus, only_first_plus)
                    first_plus_mes = psep.join(first_plus)
                    first_plus_mes = f"ВПЕРВЫЕ появились {appeared}. {event_name}: {separator}{first_plus_mes}"
                    to_mes.append(first_plus_mes)
                if plus and not only_first:
                    plus_mes = psep.join(plus)
                    to_mes.append(f"Появились {appeared}. {event_name}:{separator}{plus_mes}")
                    if cprint:
                        self.cprint('Ахтунг. ' + ', '.join(to_mes))
                if increase:
                    increase_mes = psep.join(increase)
                    to_mes.append(f"{appeared_upper}: наличие увеличилось. {event_name}:{separator}{increase_mes}")
                if print_minus:
                    if minus and not only_first:
                        minus_mes = psep.join(minus)
                        to_mes.append(f"{appeared_upper} исчезли из продажи. {event_name}:{separator}{minus_mes}")
                to_mes.append(f'{url}')
                mes = '\n'.join(to_mes)
                if skip_sending:
                    pass
                elif only_first:
                    if first_plus:
                        self.tprint(mes)
                elif print_minus:
                    if plus or first_plus or increase or minus:
                        self.tprint(mes)
                else:
                    if plus or first_plus or increase:
                        self.tprint(mes)
            if no_repeat:
                self.tickets_state[event_name] = refreshed_state.copy()
            if first_plus:
                tasker.put(self._events_state_write, event_name)
            return only_plus
        else:
            no_repeat = self._check_for_repeat(event_name, new_state, repeater_delay,
                                               repeats_until_succeeded)
            if (self.tickets_state[event_name] != new_state) and no_repeat:
                if skip_sending:
                    pass
                elif new_state:
                    self.tprint(f'Появились {appeared}. {event_name}:\n{url}')
                    to_plus = [event_name]
                    if cprint:
                        self.cprint('Ахтунг. Появились билеты. ' + event_name)
                else:
                    if print_minus:
                        self.tprint(f'{appeared_upper} исчезли из продажи. {event_name}:\n{url}')
            if no_repeat:
                self.tickets_state[event_name] = new_state
            return to_plus

    def _events_state_write(self, key):
        try:
            events_state_file = try_open('events_state.json', {}, json_=True)
            if key not in events_state_file:
                events_state_file[key] = self._events_state[key]
            else:
                events_state_file[key] += self._events_state[key]
                events_state_file[key] = list(set(events_state_file[key]))
            with open('events_state.json', 'w') as events_state_json:
                json_ = json.dumps(events_state_file, indent=4)
                events_state_json.write(json_)
        except Exception as err:
            print(utils.yellow(f'Error writing events state. {err}'
                               'This may cause problems with events_state.json'))

    def _check_events_state(self, key, plus, first_plus):
        self._events_state[key].extend(first_plus)
        for item in first_plus:
            plus.pop(plus.index(item))

    def _check_events_state_dict(self, key, plus, first_plus):
        self._events_state[key].extend(first_plus)
        for item in first_plus:
            for item_ in plus:
                if item in item_:
                    plus.pop(plus.index(item_))
                    break
