import _thread
import os
import sys
import threading
import time
import json
import inspect
from typing import Callable, Iterable, Awaitable, Coroutine, Optional

from . import utils
import colorama

from .logger import logger, track_coroutine

colorama.init()


class TryError(Exception):
    """All the tries were not succeeded"""


def threading_try(to_try: Callable,
                  name='Main',
                  handle_error=None,
                  tries=3,
                  args=None,
                  kwargs=None,
                  print_errors=True):
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

    Returns: created ``threading.Thread`` object
    """
    kwargs = {
        'name': name,
        'handle_error': handle_error,
        'tries': tries,
        'args': args,
        'kwargs': kwargs,
        'raise_exc': False,
        'print_errors': print_errors
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
              log_func: Optional[Callable] = logger.error):
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
        log_func: logging function, e.g., ``logger.error``

    Returns: value from a last successful attempt.
    If all attempts fail, exception is raised or
    provision.TryError is returned.
    """
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    if tries == 1 and raise_exc is True:
        raise RuntimeError('If tries == 1, exception should not be raised.'
                           ' Set raise_exc argument to False')

    for i in range(tries):
        result, exc = _tryfunc(to_try,
                               name,
                               print_errors=print_errors,
                               log_func=log_func,
                               args=args,
                               kwargs=kwargs,
                               from_multi_try=(i, tries))
        if result is not TryError:
            return result
        elif handle_error:
            error_prefix = '[Exception during `handle_error`] '
            if does_func_has_arguments(handle_error):
                exc_args, exc_kwargs = (exc, *args,), kwargs
            else:
                exc_args, exc_kwargs = None, None
            _tryfunc(handle_error,
                     name,
                     args=exc_args,
                     kwargs=exc_kwargs,
                     error_prefix=error_prefix)
    else:
        if raise_exc:
            raise TryError(f'Превышено число попыток ({tries})')
        else:
            return TryError


def just_try(to_try: Callable,
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


def _tryfunc(func: Callable,
             name='',
             error_prefix='',
             print_errors=True,
             log_func=None,
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
            if log_func == logger.error:
                color_switcher1, color_switcher2 = utils.Fore.YELLOW, utils.Fore.RED
            elif log_func == logger.warning:
                color_switcher1, color_switcher2 = utils.Fore.RED, utils.Fore.YELLOW
            else:
                color_switcher1, color_switcher2 = utils.Fore.RED, utils.Fore.RED

            if from_multi_try is not None:
                tried, overall = from_multi_try
                if overall != 1:
                    tried_overall = f' {color_switcher1}[{tried + 1}/{overall}]{color_switcher2}'
            str_exception = str(exc).split('\n')[0]
            error = f'({type(exc).__name__}){tried_overall} {str_exception}'
            error_with_prefix = error_prefix + error

            if log_func:
                log_func(error_with_prefix, name=name)
            else:
                name_part = f'{name} | ' if name else ''
                print(f'{name_part}{color_switcher2}{error_with_prefix}{utils.Fore.RESET}')
        return TryError, exc
    else:
        return result, None


def async_just_try(to_try: Callable,
                   name='Main',
                   args=None,
                   kwargs=None,
                   print_errors=True,
                   semaphore=None):
    """
    A simplified async_try statement.
    The same as async_try, but executes ``to_try`` code
    only once and doesn't raise an exception.

    Args:
        to_try: main async function
        name: name to identify logs
        args: arguments sent to ``to_try``
        kwargs: keyword arguments sent to ``to_try``
        print_errors: log errors on each try
        semaphore: release semaphore at the execution end

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
        'print_errors': print_errors,
        'semaphore': semaphore
    }
    return async_try(to_try, **kwargs)


@track_coroutine
async def async_try(to_try: Callable[..., Awaitable],
                    handle_error: Optional[Callable[..., Awaitable]] = None,
                    tries=3,
                    raise_exc=True,
                    name='Main',
                    args: Iterable = None,
                    kwargs: dict = None,
                    print_errors=True,
                    log_func: Optional[Callable] = logger.error,
                    semaphore=None):
    """
    Try to execute smth ``tries`` times sequentially.
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
        log_func: logging function, e.g., ``logger.error``
        semaphore: release semaphore at the execution end

    Returns: value from a last successful attempt.
    If all attempts fail, exception is raised or
    provision.TryError is returned.
    """
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    if tries == 1 and raise_exc is True:
        raise RuntimeError('If tries == 1, exception should not be raised.'
                           ' Set raise_exc argument to False')

    """prnt = []
    try:
        prnt.append(to_try.__self__.__class__.__name__)
    except:
        pass
    try:
        prnt.append(to_try.__name__)
    except:
        pass
    logger.debug('called', *prnt, name=name)"""
    for i in range(tries):
        result, exc = await _asynctry(to_try,
                                      name=name,
                                      print_errors=print_errors,
                                      log_func=log_func,
                                      args=args,
                                      kwargs=kwargs,
                                      from_multi_try=(i, tries),
                                      level=logger.error)
        if result is not TryError:
            if semaphore:
                semaphore.release()
            return result
        elif handle_error:
            error_prefix = '[Exception during `handle_error`] '
            if does_func_has_arguments(handle_error):
                exc_args, exc_kwargs = (exc, *args,), kwargs
            else:
                exc_args, exc_kwargs = None, None
            await _asynctry(handle_error,
                            name=name,
                            args=exc_args,
                            kwargs=exc_kwargs,
                            error_prefix=error_prefix)
    else:
        if semaphore:
            semaphore.release()
        if raise_exc:
            raise TryError(f'Превышено число попыток ({tries})')
        else:
            return TryError


@track_coroutine
async def _asynctry(func: Callable[..., Awaitable],
                    name='',
                    error_prefix='',
                    print_errors=True,
                    args=None,
                    kwargs=None,
                    log_func=None,
                    from_multi_try=None):
    if kwargs is None:
        kwargs = {}
    if args is None:
        args = tuple()
    coroutine = func(*args, **kwargs)
    if not isinstance(coroutine, Coroutine):\
        raise TypeError('first argument should be an awaitable function')
    try:
        result = await coroutine
    except Exception as exc:
        if print_errors:
            tried_overall = ''
            if log_func == logger.error:
                color_switcher1, color_switcher2 = utils.Fore.YELLOW, utils.Fore.RED
            elif log_func == logger.warning:
                color_switcher1, color_switcher2 = utils.Fore.RED, utils.Fore.YELLOW
            else:
                color_switcher1, color_switcher2 = utils.Fore.RED, utils.Fore.RED

            if from_multi_try is not None:
                tried, overall = from_multi_try
                if overall != 1:
                    tried_overall = f' {color_switcher1}[{tried + 1}/{overall}]{color_switcher2}'
            str_exception = str(exc).split('\n')[0]
            error = f'({type(exc).__name__}){tried_overall} {str_exception}'
            error_with_prefix = error_prefix + error

            if log_func:
                log_func(error_with_prefix, name=name)
            else:
                name_part = f'{name} | ' if name else ''
                print(f'{name_part}{color_switcher2}{error_with_prefix}{utils.Fore.RESET}')
        return TryError, exc
    else:
        return result, None


def does_func_has_arguments(func: Callable):
    if func.__name__ == 'release' and hasattr(func, '__self__'):
        if isinstance(func.__self__, _thread.LockType):
            return False
    elif len(inspect.signature(func).parameters) == 0:
        return False
    else:
        return True


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
        fp = None
        try:
            fp = open(path, 'w+')
            if json_:
                json.dump(to_write, fp)
            else:
                fp.write(to_write)
            return True
        except Exception as err:
            print(f'Error writing "{path}" file: {err}')
            time.sleep(1)
        finally:
            try:
                if fp:
                    fp.close()
            except:
                print(f'File "{path}" can\'t be opened')
    else:
        raise RuntimeError(f'Out of attempts ({tries}) on writing file')
