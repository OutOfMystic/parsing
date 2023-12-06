import itertools
import time
from typing import Iterable, Any

from colorama import Fore, Back

from parse_module.utils.types import HashDict


def green(mes: str):
    return Fore.GREEN + Back.RESET + str(mes) + default_fore + default_back


def red(mes: str):
    return Fore.RED + Back.RESET + str(mes) + default_fore + default_back


def blue(mes: str):
    return Fore.BLUE + Back.RESET + str(mes) + default_fore + default_back


def blueprint(mes: str):
    mes = Fore.BLUE + Back.RESET + str(mes) + default_fore + default_back
    print(mes)


def yellow(mes: str):
    return Fore.YELLOW + Back.RESET + str(mes) + default_fore + default_back


def colorize(mes: str,
             color):
    return color + default_back + str(mes) + default_fore


def lprint(mes: str,
           console_print=True,
           prefix=True,
           encoding=None,
           color=None,
           filename='log.txt',
           end='\n',
           name=''):
    if color:
        mes = colorize(mes, color)
    if prefix and name:
        mes = name + '| ' + mes
    lmes = time.asctime() + ' ' + mes + end if prefix else mes + end
    try:
        with open(filename, 'a+', encoding=encoding) as logs:
            logs.write(lmes)
    except:
        print(colorize('Log file is used by another app', Fore.RED))
    if console_print:
        print(mes, end=end)


def differences(left: Iterable, right: Iterable, key_filter=None):
    # Returns items which are only in the
    # left array and only in the right array
    left_unique = {key_filter(item): item for item in left} if key_filter else left
    right_unique = {key_filter(item): item for item in right} if key_filter else right
    set1 = set(left_unique)
    set2 = set(right_unique)
    dif1 = list(set1 - set2)
    intersection = list(set1 & set2)
    dif2 = list(set2 - set1)
    if key_filter:
        dif1 = [key_filter(item) for item in dif1]
        intersection = [key_filter(item) for item in intersection]
        dif2 = [key_filter(item) for item in dif2]
    return dif1, intersection, dif2


def find_by_value(dict_, value):
    for key in dict_:
        if dict_[key] == value:
            return key
    else:
        return None


def str_in_elem(list_, str_, low=True):
    str_ = str_.lower()
    for elem in list_:
        if low:
            if str_ in str(elem).lower():
                return True
        else:
            if str_ in elem:
                return True
    return False


def elem_in_str(list_, str_, low=True):
    str_ = str_.lower()
    for elem in list_:
        if low:
            if elem.lower() in str(str_):
                return True
        else:
            if elem in str_:
                return True
    return False


def pp_dict(dict_: dict):
    for key, value in dict_.items():
        print("{0}: {1}".format(key, value))


def lp_dict(dict_: dict):
    mes_lines = []
    for key, value in dict_.items():
        mes_lines.append("{0}: {1}".format(key, value))
    mes = '\n'.join(mes_lines)
    lprint(mes)


def reg_changes(item: Any,
                key='1'):
    global reg_change_state
    if key not in reg_change_state:
        reg_change_state[key] = item
    if item != reg_change_state[key]:
        reg_change_state[key] = item
        return True
    else:
        return False


def groupby(iterable, key=None):
    groups = groupdict(iterable, key=key)
    group_list = list(groups.items())
    group_list.sort(key=lambda row: row[0])
    for key, elements in group_list:
        yield key, elements


def groupdict(iterable, key=None, hash_=False):
    if key is None:
        key = lambda x: x
    groups = HashDict()
    for elem in iterable:
        group_key = key(elem)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(elem)
    return groups


def get_dict_hash(dict_):
    listed = list(dict_.items())
    listed.sort(key=lambda row: row[0])
    plain = itertools.chain(listed)
    return tuple(plain)


reg_change_state = {}
default_fore = Fore.RESET
default_back = Back.RESET