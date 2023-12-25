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
    """All the tries were not succeeded"""


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
                  handle_error=None,
                  tries=3,
                  args=None,
                  kwargs=None,
                  print_errors=True,
                  multiplier=1.14):
    """
    The same as multi_try, but executes ``to_try`` code
    into a new thread. After the new thread is started,
    function return thread object but doesn't return a
    result as ``multi_try``

    If you still want the result, you can send a mutable
    object as argument and handle it

    Args:
        to_try: main function
        name: name to identify logs
        handle_error: called if attempt was not succeeded
        tries: number of attempts to execute ``to_try``
        args: arguments sent to ``to_try``
        kwargs: keyword arguments sent to ``to_try``
        print_errors: log errors on each try
        multiplier: wait ratio, increase up to 1.5

    Returns: created ``threading.Thread`` object
    """
    kwargs = {
        'name': name,
        'handle_error': handle_error,
        'tries': tries,
        'args': args,
        'kwargs': kwargs,
        'raise_exc': False,
        'print_errors': print_errors,
        'multiplier': multiplier
    }
    thread = threading.Thread(target=multi_try, args=(to_try,), kwargs=kwargs)
    thread.start()
    return thread


def multi_try(to_try: Callable,
              handle_error: Callable = None,
              tries=3,
              raise_exc=True,
              name='Main',
              args: Iterable = None,
              kwargs: dict = None,
              print_errors=True,
              use_logger=True,
              multiplier=1.14):
    """
    Try to execute smth ``tries`` times.
    If all attempts are unsuccessful and ``raise_exc``
    is True, raise an exception. ``handle_error`` is called
    every time attempt was not succeeded.

    Args:
        to_try: main function
        name: name to identify logs
        handle_error: called if attempt was not succeeded
        tries: number of attempts to execute ``to_try``
        args: arguments sent to ``to_try``
        kwargs: keyword arguments sent to ``to_try``
        raise_exc: raise exception or not after all
        print_errors: log errors on each try
        use_logger: log errors via the custom logger
        multiplier: wait ratio, increase up to 1.5

    Returns: value from a last successful attempt.
    If all attempts fail, exception is raised or
    provision.TryError is returned.
    """
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    if handle_error is None:
        handle_error = fpass
    seconds = 3.0
    if tries == 1 and raise_exc is True:
        raise RuntimeError('If tries == 1, exception should not be raised.'
                           ' Set raise_exc argument to False')

    for i in range(tries):
        seconds = seconds ** multiplier
        level = logger.error if i == tries - 1 else logger.warning
        result, exc = _tryfunc(to_try,
                               name,
                               print_errors=print_errors,
                               use_logger=use_logger,
                               args=args,
                               kwargs=kwargs,
                               from_multi_try=(i, tries),
                               level=logger.error)
        if result is not TryError:
            return result
        else:
            error_prefix = '[Exception during `handle_error`]\n'
            exc_args = None if len(inspect.signature(handle_error).parameters) == 0 else (exc, *args,)
            _tryfunc(handle_error,
                     name,
                     args=exc_args,
                     kwargs=kwargs,
                     error_prefix=error_prefix)
    else:
        if raise_exc:
            raise TryError(f'Превышено число попыток ({tries})')
        else:
            return TryError


def _tryfunc(func,
             name='',
             error_prefix='',
             print_errors=True,
             use_logger=True,
             level=logger.error,
             args=None,
             kwargs=None,
             from_multi_try=None):
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        if print_errors:
            tried_overall = ''
            if level == logger.error:
                color_switcher1, color_switcher2 = utils.Fore.YELLOW, utils.Fore.RED
            else:
                color_switcher1, color_switcher2 = utils.Fore.RED, utils.Fore.YELLOW

            if from_multi_try is not None:
                tried, overall = from_multi_try
                if overall != 1:
                    tried_overall = f' {color_switcher1}[{tried + 1}/{overall}]{color_switcher2}'
            str_exception = str(exc).split('\n')[0]
            error = f'({type(exc).__name__}){tried_overall} {str_exception}'
            error_with_prefix = error_prefix + error

            if use_logger:
                level(error_with_prefix, name=name)
            else:
                name_part = f'{name} | ' if name else ''
                print(f'{name_part}{color_switcher2}{error_with_prefix}{utils.Fore.RESET}')
        return TryError, exc
    else:
        return result, None


def just_try(to_try,
             name='Main',
             args=None,
             kwargs=None,
             print_errors=True):
    """
    A simplified multi_try statement.
    The same as multi_try, but executes ``to_try`` code
    only once and doesn't raise an exception.

    Args:
        to_try: main function
        name: name to identify logs
        args: arguments sent to ``to_try``
        kwargs: keyword arguments sent to ``to_try``
        print_errors: log errors on each try

    Returns: value from a last successful attempt.
    If all attempts fail, exception is raised or
    provision.TryError is returned.
    """
    kwargs = {
        'name': name,
        'tries': 1,
        'args': args,
        'kwargs': kwargs,
        'raise_exc': False,
        'print_errors': print_errors
    }
    return multi_try(to_try, **kwargs)


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
