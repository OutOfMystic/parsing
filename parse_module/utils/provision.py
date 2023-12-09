import os
import sys
import threading
import time
import json
import inspect
import concurrent.futures
from typing import Callable, Iterable

from . import utils
import colorama

from .logger import logger

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
                  multiplier=1.14):
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
        'multiplier': multiplier
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
              multiplier=1.14):
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    if to_except is None:
        to_except = fpass
    seconds = 3.0
    if tries == 1 and raise_exc is True:
        raise RuntimeError('If tries == 1, exception should not be raised.'
                           ' Set raise_exc argument to False')

    for i in range(tries):
        seconds = seconds ** multiplier
        result, exc = _tryfunc(to_try,
                               name,
                               print_errors=print_errors,
                               args=args,
                               kwargs=kwargs,
                               from_multi_try=(i, tries))
        if result is not TryError:
            return result
        else:
            error_prefix = '[Another exception occurred during handling `to_except`]'
            _tryfunc(to_except, name, error_prefix=error_prefix)
    else:
        if raise_exc:
            raise RuntimeError(f'Превышено число попыток ({tries})')
        else:
            return TryError


def _tryfunc(func,
             name='',
             error_prefix='',
             print_errors=True,
             args=None,
             kwargs=None,
             from_multi_try=None):
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    if error_prefix:
        error_prefix += ' '
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        if print_errors:
            tried_overall = ''
            if from_multi_try is not None:
                tried, overall = from_multi_try
                if overall != 1:
                    tried_overall = f' {utils.Fore.YELLOW}[{tried + 1}/{overall}]{utils.Fore.RED}'
            str_exception = str(exc).split('\n')[0]
            error = f'({type(exc).__name__}){tried_overall} {str_exception}'
            error_with_prefix = error_prefix + error
            logger.error(error_with_prefix, name=name)
        return TryError, exc
    else:
        return result, None


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
