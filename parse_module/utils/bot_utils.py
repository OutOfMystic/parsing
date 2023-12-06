import itertools
import json
import os
import random
from importlib.resources import files

from . import resources


def get_resource_lines(filename):
    file = files(resources).joinpath(filename).read_text(encoding='utf-8')
    lines = [line for line in file.split('\n') if line]
    random.shuffle(lines)
    return itertools.cycle(lines)


_first_names = [
    get_resource_lines('first_names_0.txt'),
    get_resource_lines('first_names_1.txt'),
    get_resource_lines('first_names_2.txt'),
    get_resource_lines('first_names_3.txt')
]
_second_names = [
    get_resource_lines('second_names_0.txt'),
    get_resource_lines('second_names_1.txt'),
    get_resource_lines('second_names_2.txt'),
    get_resource_lines('second_names_3.txt')
]
_addresses = get_resource_lines('addresses_ru.txt')
_middle_names = get_resource_lines('Middle_Name_M_rus.txt')
_indexes = get_resource_lines('index.txt')
_emails = get_resource_lines('e-mails.txt')
_moscow_codes = ['901', '903', '905', '906', '909', '910', '915', '916',
                 '917', '919', '925', '926', '929', '936', '958', '962',
                 '963', '964', '965', '966', '967', '968', '969', '977',
                 '980', '983', '985', '986', '995', '996', '999']


def get_first_name(lang='rus', sex='m'):
    i1 = 0 if lang == 'eng' else 1
    i2 = 0 if sex == 'm' else 1
    arr_num = (i1 * 2) + i2
    choice = next(_first_names[arr_num])
    return choice


def get_second_name(lang='rus', sex='m'):
    i1 = 0 if lang == 'eng' else 1
    i2 = 0 if sex == 'm' else 1
    arr_num = (i1 * 2) + i2
    choice = next(_second_names[arr_num])
    return choice


def get_middle_name():
    return next(_middle_names)


def get_identity(lang='rus'):
    sex = random.choice(['m', 'w'])
    first_name = get_first_name(lang, sex)
    second_name = get_second_name(lang, sex)
    middle_name = get_middle_name()
    return first_name, second_name, middle_name


def get_email():
    return next(_emails)


def get_passport(country_code='RU'):
    if country_code == 'DE':
        digits = 9
        passport = 'C0'
        chars = '0123456789CFGHJKLMNPRTVWXYZ'
    elif country_code == 'DK':
        digits = 9
        passport = '2'
        chars = '0123456789'
    elif country_code == 'NL':
        digits = 9
        passport = 'S'
        chars = '0123456789ECP'
    elif country_code == 'PT':
        digits = 7
        passport = 'K'
        chars = '0123456789'
    elif country_code == 'FR':
        digits = 9
        passport = '0'
        chars = '0123456789CFGMNPTU'
    else:
        digits = 10
        passport = '4'
        chars = '0123456789'
    last_digits = [random.choice(chars) for _ in range(digits - len(passport))]
    for digit in last_digits:
        passport += digit
    return passport


def get_address(country_code='RU'):
    street = next(_addresses)
    if country_code == 'RU':
        prefixes = ['улица', 'улица', 'ул.', 'шоссе', 'ул.', 'пр.', 'т.']
        separators = [', к.', '\\', '/']
    else:
        prefixes = ['street', 'st.', 'avenue', 'av.', 'path', 'street', 'str.', 'Street', 'ul.', 'pr.']
        separators = [', b.', ', ']
    street_values = [random.choice(prefixes), street]
    separator = random.choice(separators)
    random.shuffle(street_values)
    street_name = ' '.join(street_values)
    house = random.randint(1, 78)
    building = random.choice([0, 0, 0, 0, 0, 0])
    flat = random.randint(1, 120)
    if building:
        numeric_name = f', {house}{separator}{building}, {flat}'
    else:
        numeric_name = f', {house}, {flat}'
    full_address = street_name + numeric_name
    return full_address


def get_index(country_code='RU'):
    if country_code == 'RU':
        index = random.randint(101, 199) * 1000 + random.randint(2, 100)
    else:
        index = random.randint(10, 40) * 1000 + random.randint(2, 500)
    return str(index)


def get_phone(country_code='RU'):
    if country_code == 'RU':
        return '9' + random.choice(_moscow_codes) + \
            ''.join([str(random.randint(0, 6)) for _ in range(9)])
    if country_code == 'FR':
        return random.choice(['1', '4']) + ''.join([str(random.randint(0, 9)) for _ in range(8)])
    elif country_code == 'PT':
        return '21' + ''.join([str(random.randint(0, 9)) for _ in range(7)])
    elif country_code == 'DK':
        return '9' + ''.join([str(random.randint(0, 9)) for _ in range(7)])
    elif country_code == 'NL':
        return '70' + ''.join([str(random.randint(0, 9)) for _ in range(7)])
    else:
        raise IndexError(f'Code {country_code} isn\'t supported')


def get_birthday(drange=(1, 28,), mrange=(1, 12,), yrange=(1980, 2004,)):
    d = random.randint(*drange)
    m = random.randint(*mrange)
    y = random.randint(*yrange)
    return d, m, y
