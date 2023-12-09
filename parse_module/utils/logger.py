import inspect
import json
import re
import sys
import threading
import time
import traceback
from datetime import datetime

from colorama import Fore

from parse_module.utils.date import readable_datetime
from parse_module.utils.utils import lprint, default_fore


class Logger(threading.Thread):

    def __init__(self, log_path='main.log', release=True):
        super().__init__()
        self.release = release
        self._stash = []
        self.info('Parsing system started', name='Controller')
        self.log_path = log_path
        self.start()

    def log(self, message: str, level, **kwargs):
        now = datetime.now()
        if self.release:
            log = {
                'timestamp': now.isoformat(),
                'level': level,
                'mes': message,
                **kwargs
            }
            self._stash.append(log)
        else:
            log = f'{level} {readable_datetime(now)} | {message}\n'
            for kwarg, value in kwargs.items():
                log += f'{kwarg}: {value}\n'
            self._stash.append(log)

        fore_back = Fore.LIGHTCYAN_EX
        fore_front = COLORS.get(level, Fore.LIGHTGREEN_EX)

        if 'traceback' in kwargs:
            call_stack = parse_traceback(kwargs['traceback'])
            call_stack = ' | ' + Fore.RED + '(Traceback) ' + call_stack
        elif level == 'DEBUG':
            call_stack = ' | ' + get_current_stack()
        else:
            call_stack = ''

        name = kwargs.get('name', 'Main')
        dt_str = readable_datetime(now).rjust(16, ' ')

        mes = (f'{fore_back}{dt_str} | {fore_front}{level} {fore_back}'
               f'| {name}{call_stack}{fore_front} - {message}{default_fore}\n')
        print(mes, end='')

    def debug(self, message, **kwargs):
        self.log(message, 'DEBUG', **kwargs)

    def info(self, message, **kwargs):
        self.log(message, 'INFO', **kwargs)

    def warning(self, message, **kwargs):
        self.log(message, 'WARNING', **kwargs)

    def error(self, message, **kwargs):
        kwargs['traceback'] = traceback.format_exc()
        self.log(message, 'ERROR', **kwargs)

    def critical(self, message, **kwargs):
        kwargs['traceback'] = traceback.format_exc()
        self.log(message, 'CRITICAL', **kwargs)

    def bprint_compatible(self, message, name, color):
        level = colors_reversed.get(color, Fore.LIGHTGREEN_EX)
        self.log(message, level, name=name)

    def send_logs(self):
        logs = self._stash
        self._stash = []
        if self.release:
            jsoned = ''.join(json.dumps(log, ensure_ascii=False, separators=(',', ':')) + '\n'
                             for log in logs)
            with open(self.log_path, 'a') as fp:
                fp.write(jsoned)
        else:
            to_print = '\n'.join(logs)
            lprint(to_print, console_print=False, prefix=self.name)
        del logs

    def run(self):
        while True:
            try:
                if self._stash:
                    self.send_logs()
            except Exception as err:
                logger.error(f'logger thread error: {err}', name='Logger')
            time.sleep(1)


def get_current_stack():
    calls = inspect.stack()
    last_call = calls[3]
    file_path = last_call.filename.split('\\parse_module\\')[-1]
    file_path_formatted = file_path.replace('\\', '.')
    if file_path_formatted.endswith('.py'):
        file_path_formatted = file_path_formatted[:-3]
    return f'{file_path_formatted}.{last_call.function}:{last_call.lineno}'


def parse_traceback(traceback_string):
    matches = re.findall(r'File "([^"]*\\parse_module[^"]+)", line (\d+)', traceback_string)
    not_mult_matches = [match for match in matches if 'multi_try' not in match]
    if not matches:
        return "Не найдено информации об ошибке в строке"
    file_path, line_number = not_mult_matches[-1]
    file_path = file_path.split('\\parse_module\\')[-1]
    file_path_formatted = file_path.replace('\\', '.')
    return f'{file_path_formatted}:{line_number}'


COLORS = {
    'CRITICAL': Fore.RED,
    'ERROR': Fore.RED,
    'WARNING': Fore.YELLOW,
    'INFO': Fore.LIGHTGREEN_EX,
    'DEBUG': Fore.BLUE
}
colors_reversed = {value: key for key, value in COLORS.items()}
logger = Logger(release='release' in sys.argv)
