import time
from colorama import Fore, Back


def green(mes):
    return Fore.GREEN + Back.RESET + str(mes) + default_fore + default_back


def red(mes):
    return Fore.RED + Back.RESET + str(mes) + default_fore + default_back


def blue(mes):
    return Fore.BLUE + Back.RESET + str(mes) + default_fore + default_back


def blueprint(mes):
    mes = Fore.BLUE + Back.RESET + str(mes) + default_fore + default_back
    print(mes)


def yellow(mes):
    return Fore.YELLOW + Back.RESET + str(mes) + default_fore + default_back


def colorize(mes, color):
    return color + default_back + str(mes) + default_fore


def lprint(mes, console_print=True, prefix=True, encoding=None,
           color=None, filename='log.txt', end='\n', name=''):
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


def differences(left, right):
    # Returns items which are only in the
    # left array and only in the right array
    set1 = set(left)
    set2 = set(right)
    dif1 = list(set1 - set2)
    intersection = list(set1 & set2)
    dif2 = list(set2 - set1)
    return dif1, intersection, dif2


def find_by_value(dict_, value):
    for key in dict_:
        if dict_[key] == value:
            return key
    else:
        return None


def str_in_elem(list_, str_):
    for elem in list_:
        if str_ in elem:
            return True
    return False


def elem_in_str(list_, str_):
    for elem in list_:
        if elem in str_:
            return True
    return False


def pp_dict(d):
    for key, value in d.items():
        print("{0}: {1}".format(key, value))


def lp_dict(d):
    mes_lines = []
    for key, value in d.items():
        mes_lines.append("{0}: {1}".format(key, value))
    mes = '\n'.join(mes_lines)
    lprint(mes)


def reg_changes(item, key='1'):
    global reg_change_state
    if key not in reg_change_state:
        reg_change_state[key] = item
    if item != reg_change_state[key]:
        reg_change_state[key] = item
        return True
    else:
        return False


reg_change_state = {}
default_fore = Fore.BLACK
default_back = Back.RESET