import inspect
import json
import re
import sys
import threading
import time
import traceback
from datetime import datetime

from colorama import Fore, Back

from parse_module.utils.date import readable_datetime
from parse_module.utils.utils import lprint, default_fore, default_back


class Logger(threading.Thread):

    def __init__(self, log_path='main.log',
                 release=True,
                 ignore_files=None,
                 drop_path_level=0,
                 test=False):
        super().__init__()

        if ignore_files is None:
            ignore_files = ['manager.core.debug',
                            'manager.core.error',
                            'manager.core.critical',
                            'models.group.error',
                            'utils.provision.multi_try',
                            'utils.logger.error',
                            'utils.logger.critical',
                            'utils.provision._tryfunc',
                            'models.parser._debug_only']
        self.release = release
        self.log_path = log_path
        self.ignore_files = ignore_files
        self.drop_path_level = drop_path_level
        self.source_filter = None
        self.level_filter = None
        self.test = test

        self._buffer = []
        self._debug_buffer = []
        self._stub_buffer = []
        self._print_locker = False

        self.start()
        if not test:
            self.info('Logger started', name='Controller')

    def log(self, message: str, level, **kwargs):
        now = datetime.now()
        if level == 'DEBUG' and self.release:
            return

        if 'traceback' in kwargs:
            call_stack = parse_traceback(kwargs['traceback'],
                                         ignore_files=self.ignore_files,
                                         drop_path_level=self.drop_path_level)
            call_stack = Fore.RED + call_stack
        elif level == 'DEBUG':
            call_stack = get_current_stack(self.ignore_files, drop_path_level=self.drop_path_level)
        else:
            call_stack = None

        log = {
            'timestamp': now.isoformat(),
            'level': level,
            'message': message[:10000],
            **kwargs
        }
        if call_stack is not None:
            log['call_stack'] = call_stack
        self._buffer.append(log)

        if not self.release:
            name = f' | {kwargs["name"]}' if 'name' in kwargs else ''
            debug_log = f'{level} {readable_datetime(now)}{name}\n'
            for kwarg, value in kwargs.items():
                if kwarg == 'name':
                    continue
                debug_log += f'{kwarg}: {value}\n'
            debug_log += message
            debug_log += '\n'
            self._debug_buffer.append(debug_log)

        if self._print_locker:
            self._stub_buffer.append(log)
        else:
            self.filter_and_print(log, message=message)

    def filter_and_print(self, log, message=None):
        if self.level_filter is not None:
            if self.level_filter != log['level']:
                return
        if self.source_filter is not None:
            if self.source_filter.lower() not in log['name'].lower():
                return
        try:
            self.print_log(log, message=message)
        except Exception as err:
            if not self._print_locker:
                logger.error(f'Error printing message from a log. {err}')

    @staticmethod
    def print_log(log, message=None):
        if message is None:
            message = log['message']
        level = log['level']
        call_stack = log.get('call_stack', '')
        name = log.get('name', 'Main')
        timestamp = datetime.fromisoformat(log['timestamp'])

        fore_back = default_fore
        fore_front = COLORS.get(level, Fore.LIGHTGREEN_EX)
        if level != 'DEBUG':
            if message.count('\n') > 2:
                parts = message.split('\n')[:2]
                message = '\n'.join(parts) + '...'
        dt_str = readable_datetime(timestamp).ljust(17, ' ')
        if call_stack:
            call_stack = ' | ' + call_stack

        # if level == 'INFO' or name != 'Controller':
        #     return
        if level == 'CRITICAL':
            mes = (f'{fore_back}{dt_str} | {Fore.LIGHTWHITE_EX}{Back.RED}{level}{fore_back}{default_back} '
                   f'| {Fore.LIGHTCYAN_EX}{name}{fore_back}{call_stack} - '
                   f'{Fore.LIGHTWHITE_EX}{Back.RED}{message}{fore_back}{default_back}\n')
        else:
            mes = (f'{fore_back}{dt_str} | {fore_front}{level} {fore_back}'
                   f'| {Fore.LIGHTCYAN_EX}{name}{fore_back}{call_stack} - {fore_front}{message}{default_fore}\n')
        print(mes, end='')

    def debug(self, *messages, **kwargs):
        message = ' '.join(str(arg) for arg in messages)
        self.log(message, 'DEBUG', **kwargs)

    def info(self, *messages, **kwargs):
        message = ' '.join(str(arg) for arg in messages)
        self.log(message, 'INFO', **kwargs)

    def warning(self, *messages, **kwargs):
        message = ' '.join(str(arg) for arg in messages)
        self.log(message, 'WARNING', **kwargs)

    def error(self, *messages, **kwargs):
        message = ' '.join(str(arg) for arg in messages)
        kwargs['traceback'] = traceback.format_exc()[:-1]
        self.log(message, 'ERROR', **kwargs)

    def critical(self, *messages, **kwargs):
        message = ' '.join(str(arg) for arg in messages)
        kwargs['traceback'] = traceback.format_exc()[:-1]
        self.log(message, 'CRITICAL', **kwargs)

    def success(self, *messages, **kwargs):
        message = ' '.join(str(arg) for arg in messages)
        self.log(message, 'SUCCESS', **kwargs)

    def bprint_compatible(self, message, name, color):
        level = colors_reversed.get(color, Fore.LIGHTGREEN_EX)
        self.log(message, level, name=name)

    def send_logs(self):
        logs = self._buffer
        self._buffer = []
        jsoned = ''.join(json.dumps(log, ensure_ascii=False, separators=(',', ':')) + '\n'
                         for log in logs)
        with open(self.log_path, 'a', encoding='utf-8') as fp:
            fp.write(jsoned)
        del logs

        logs = self._debug_buffer
        self._debug_buffer = []
        if logs:
            to_print = '\n'.join(logs)
            lprint(to_print, console_print=False, prefix=self.name)
            del logs

    def apply_filter(self, source, level):
        self.source_filter = source
        self.level_filter = level

        print('\n' * 1000 + 'Collecting last messages ...')

        start_time = time.time()
        rows = []
        self.pause()
        with open(self.log_path, 'r', encoding='utf-8') as file:
            file.seek(0, 2)
            file_size = file.tell()
            start_pos = max(0, file_size - 2 * 1024 * 1024)
            file.seek(start_pos)
            lines = file.readlines()
            for line in lines:
                rows.append(line)
                if '"message":"Logger started"' in line:
                    rows.clear()
        print(time.time() - start_time)

        start_time = time.time()
        for row in rows:
            try:
                log = json.loads(row)
                self.filter_and_print(log)
            except Exception as err:
                self.warning(f'Lost log: {err}')
        print(time.time() - start_time)

        start_time = time.time()
        self.resume()
        print(time.time() - start_time)

    def pause(self):
        self._print_locker = True

    def resume(self):
        while self._stub_buffer:
            try:
                log = self._stub_buffer.pop(0)
                self.filter_and_print(log)
            except Exception as err:
                self.warning(f'Lost log: {err}')
        self._print_locker = False

    def run(self):
        while True:
            try:
                if self._buffer:
                    self.send_logs()
            except Exception as err:
                logger.error(f'logger thread error: {err}', name='Logger')
            time.sleep(1)


def get_current_stack(ignore_files=None, drop_path_level=0):
    if ignore_files is None:
        ignore_files = []

    str_calls = []
    calls = [call for call in inspect.stack() if 'parsing' in call.filename]
    for call in calls:
        file_path = call.filename.split('parsing', 1)[-1]
        file_path_prep= file_path.replace('\\', '.').replace('/', '.')
        file_parts = file_path_prep.split('.')[1 + drop_path_level:]
        if file_parts[-1] == 'py':
            del file_parts[-1]
        file_path_formatted = '.'.join(file_parts)
        str_call = f'{file_path_formatted}.{call.function}'
        if not any(str_call.endswith(end) for end in ignore_files):
            call_with_lineno = str_call + f':{call.lineno}'
            str_calls.append(call_with_lineno)
    try:
        return str_calls[3]
    except:
        try:
            return str_calls[-1]
        except:
            return "--Callstack cannot be traced--"


def parse_traceback(traceback_string, ignore_files=None,
                    drop_path_level=0, project_name='parsing'):
    if ignore_files is None:
        ignore_files = []
    matches = re.findall(rf'File "([^"]*\\working_directory[^"]+)", line (\d+), in (\w+)\n', traceback_string)
    not_mult_matches = [match for match in matches if 'multi_try.py' not in match]
    if not matches:
        matches = re.findall(r'File "([^"]*\\parse_module[^"]+)", line (\d+), in (\w+)\n', traceback_string)
        not_mult_matches = [match for match in matches if 'multi_try.py' not in match]
    if not matches:
        return get_current_stack(ignore_files=ignore_files, drop_path_level=drop_path_level)
    file_path, line_number, func_name = not_mult_matches[-1]
    file_path = file_path.split(project_name, 1)[-1]
    if file_path.endswith('.py'):
        file_path = file_path[:-3]
    file_path_prep = file_path.replace('\\', '.').replace('/', '.')
    file_parts = file_path_prep.split('.')[1 + drop_path_level:]
    file_path_formatted = '.'.join(file_parts)
    return f'(Traceback) {file_path_formatted}.{func_name}:{line_number}'


COLORS = {
    'CRITICAL': Fore.LIGHTWHITE_EX,
    'ERROR': Fore.RED,
    'WARNING': Fore.YELLOW,
    'INFO': Fore.LIGHTGREEN_EX,
    'DEBUG': Fore.BLUE,
    'SUCCESS': Fore.GREEN
}
colors_reversed = {value: key for key, value in COLORS.items()}
logger = Logger(release='release' in sys.argv, drop_path_level=1, test=True)
