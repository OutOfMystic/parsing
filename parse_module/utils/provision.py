import os
import sys
import threading
import time
import json
import inspect
import traceback
import concurrent.futures
from typing import Callable, Iterable

from . import utils
import colorama
from colorama import Fore, Back

colorama.init()


class TryError(Exception):
    pass


def pool(function, aims, max_threads):
    """
     aims = [
         [args, kwargs, key_to_find_result],
         [args2, kwargs2],
         [args3, key_to_find_result3],
         [args4],
         arg5
     ]
    """
    results = {}
    maims = []
    for i, aim in enumerate(aims):
        maims.append(parse_aim(aim, i))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures_dict = {
            executor.submit(function, *args, **kwargs): key for args, kwargs, key in maims
        }
        for future in concurrent.futures.as_completed(futures_dict):
            key = futures_dict[future]
            try:
                result = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (key, exc))
                result = None
            results[key] = result
    return results


def threading_try(to_try,
                  name='Main',
                  to_except=None,
                  tries=3,
                  args=None,
                  raise_exc=True,
                  print_errors=True,
                  multiplier=1.14,
                  prefix='',
                  error_descr=''):
    """
    The same as multi_try, but executes to_try code
    into a new thread. After the new thread is started,
    function return thread object but doesn't return a
    result as multi_try

    If you still want the result, you can send a mutable
    object as argument and handle it
    """
    kwargs = {
        'name': name,
        'to_except': to_except,
        'tries': tries,
        'args': args,
        'raise_exc': raise_exc,
        'print_errors': print_errors,
        'multiplier': multiplier,
        'prefix': prefix,
        'error_descr': error_descr
    }
    thread = threading.Thread(target=multi_try, args=(to_try,), kwargs=kwargs)
    thread.start()
    return thread


def multi_try(to_try: Callable,
              name='Main',
              to_except: Callable = None,
              tries=3,
              args: Iterable = None,
              kwargs: dict = None,
              raise_exc=True,
              print_errors=True,
              multiplier=1.14,
              prefix='',
              error_descr=''):
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    if to_except is None:
        to_except = fpass
    seconds = 3.0
    if tries == 1 and raise_exc is True:
        raise RuntimeError('If tries == 1, exception should not be raised.'
                           ' Set raise_exc to False')

    for i in range(tries):
        seconds = seconds ** multiplier
        result, exc = _tryfunc(to_try,
                               name,
                               prefix=prefix,
                               print_errors=print_errors,
                               args=args,
                               kwargs=kwargs)
        error = str(exc)
        if result != TryError:
            return result
        else:
            wait_time = seconds - 3.0
            if print_errors:
                mes = ''
                if 'Ожидание досрочно прервано' not in error:
                    mes += ' | '
                mes += 'Объект %s не обнаружен' % error_descr if error_descr else ''
                if 'Ожидание досрочно прервано' not in error:
                    mes += '. Жду %.1fс' % wait_time
                utils.lprint(mes, prefix=False, color=Fore.YELLOW, name=prefix)
            _tryfunc(to_except, 'Exception', prefix=prefix)
            if 'Ожидание досрочно прервано' not in error:
                time.sleep(wait_time)
    else:
        if raise_exc:
            raise RuntimeError('Превышено число попыток - ' + str(tries))
        else:
            return TryError


def _tryfunc(func, name='', tries=1, prefix='',
             print_errors=True, args=None, kwargs=None):
    # Если код выполнился без ошибок, вернёт True
    # Если была ошибка, а tries == 1, вернёт False
    # Если была ошибка, а tries != 1, рэйзнет RuntimeError
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    for i in range(tries):
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            if 'topping explicit waiting' in str(exc):
                raise RuntimeError('Ожидание досрочно прервано...')
            error = f'({type(exc).__name__}) {exc}'
            printing_error = error.split('\n')[0]
            if print_errors:
                end_char = '\n' if name == 'Exception' else ''
                utils.lprint(name + ': ' + printing_error, end=end_char,
                             color=Fore.RED, name=prefix)
                utils.lprint(name + ': ' + error, console_print=False, name=prefix)
                utils.lprint(traceback.format_exc(), console_print=False,
                             prefix=False, color=Fore.RED, name=prefix)
        else:
            return result, None
    else:
        if tries == 1:
            try:
                return TryError, exc
            except:
                return TryError, ''
        else:
            raise RuntimeError('Превышено число попыток - ' + str(tries))


def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False):  # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)


def delete_module(modname, paranoid=None):
    try:
        thismod = sys.modules[modname]
    except KeyError:
        raise ValueError(modname)
    these_symbols = dir(thismod)
    if paranoid:
        try:
            paranoid[:]  # sequence support
        except:
            raise ValueError('must supply a finite list for paranoid')
        else:
            these_symbols = paranoid[:]
    del sys.modules[modname]
    for mod in sys.modules.values():
        try:
            delattr(mod, modname)
        except AttributeError:
            pass
        if paranoid:
            for symbol in these_symbols:
                if symbol[:2] == '__':  # ignore special symbols
                    continue
                try:
                    delattr(mod, symbol)
                except AttributeError:
                    pass


def fpass():
    pass


def load_data(source, json_=True):
    if isinstance(source, (dict, list)):
        return source
    elif isinstance(source, str):
        with open(source, 'r') as f:
            data = json.load(f) if json_ else f.read()
        if not json_:
            data = data.split('\n')
        return data
    else:
        return json.load(source) if json_ else source.read()


def parse_aim(aim, key):
    kwargs = {}
    if not isinstance(aim, list):
        key = aim
        return [[aim], kwargs, key]
    elif len(aim) == 3:
        args, kwargs, key = aim
    elif len(aim) == 2:
        if isinstance(aim[1], dict):
            args, kwargs = aim
        else:
            args, key = aim
    elif len(aim) == 1:
        args = aim[0]
        if len(args) == 0:
            key = aim[0]
    elif len(aim) == 0:
        args = []
    else:
        raise AttributeError(f'Wrong format of pool task: {aim}')
    return args, kwargs, key


def try_open(path, default, json_=True):
    tries = 3
    for i in range(tries):
        try:
            with open(path, 'r') as f:
                payload = f.read()
            if payload == '':
                print(f'Set default value on "{path}"')
                payload = default
            if json_ and (payload != default):
                payload = json.loads(payload)
            return payload
        except Exception as err:
            if not 'No such file or directory' in err.args:
                print(f'Error opening "{path}" file: {err}')
            try_write(path, default, json_=json_)
            time.sleep(0.5)
    else:
        raise RuntimeError(f'Out of attempts ({tries}) on opening file')


def try_write(path, to_write, json_=True):
    tries = 5
    for _ in range(tries):
        try:
            f = open(path, 'w+')
            if json_:
                json.dump(to_write, f)
            else:
                f.write(to_write)
            return True
        except Exception as err:
            print(f'Error writing "{path}" file: {err}')
            time.sleep(1)
        finally:
            try:
                f.close()
            except:
                print(f'File "{path}" can\'t be opened')
    else:
        raise RuntimeError(f'Out of attempts ({tries}) on writing file')
