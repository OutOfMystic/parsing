import os
import sys
import time
from importlib.resources import files

from ..drivers.selenium import ProxyWebDriver
from . import js
from ..utils import parse_utils


def union(main_name, main, minor_name, minor):
    check_storage = set()
    for ticket in main:
        to_store = (ticket[5], ticket[6],)
        check_storage.add(to_store)

    duplicates = []
    for ticket in minor:
        to_check = (ticket[5], ticket[6],)
        if to_check in check_storage:
            duplicates.append(to_check)

    if duplicates:
        dup_str = [str(duplicate) for duplicate in duplicates]
        dupes = ','.join(dup_str)
        raise RuntimeError(f'Found duplicates while merging {minor_name}'
                           f' into {main_name}\nDuplicates are the following:\n  '
                           f'{dupes}')
    if not main:
        raise RuntimeError(f'Sector {main_name} is empty')

    main += minor
    main.sort(key=ticket_sort_func)


def delete_sectors(constructor, sector_ids, main_sector_id=None):
    sector_ids = list(sector_ids)
    sector_ids.sort()
    sector_ids_copy = sector_ids.copy()
    sectors = constructor['sectors']
    decrement = 0
    replaces = {}

    last_sector_id = sector_ids_copy.pop(0)
    for cur_id, sector in enumerate(sectors):
        if cur_id == last_sector_id:
            decrement += 1
            if sector_ids_copy:
                last_sector_id = sector_ids_copy.pop(0)
        else:
            replaces[cur_id] = cur_id - decrement

    main_sector = None
    if main_sector_id:
        main_sector = constructor['sectors'][main_sector_id]
    for decrement_, sector_id in enumerate(sector_ids):
        sector_id_fixed = sector_id - decrement_
        if main_sector is not None:
            outline = sectors[sector_id_fixed]['outline']
            main_sector['outline'] += ' ' + outline.strip()
        del sectors[sector_id_fixed]

    replaces_list = [(key, value,) for key, value in replaces.items()]
    replaces_list.sort(key = lambda row: row[0])
    for before, after in replaces_list:
        apply_changes(constructor, before, after)

    return replaces[main_sector_id]


def apply_changes(constructor, before, after):
    for ticket in constructor['seats']:
        if ticket[3] == before:
            ticket[3] = after


def change_outline(constructor, sector_id):
    global driver
    sector = constructor['sectors'][sector_id]
    outline = sector['outline']
    if driver is None:
        driver = ProxyWebDriver()

    class_names = ('mat-focus-indicator mat-tooltip-trigger '
                   'mat-mini-fab mat-button-base mat-basic')
    xpath = parse_utils.class_names_to_xpath(class_names)
    if driver.current_url != 'https://yqnn.github.io/svg-path-editor/':
        driver.get('https://yqnn.github.io/svg-path-editor/')
        driver.expl_wait('xpath', xpath)

    textarea = _update_textarea(driver)
    driver.execute_script(f'var textArea = document.querySelectorA'
                          f'll(\'[class="input-block ng-tns-c80-0"'
                          f']\')[0].querySelector("textarea");'
                          f'textArea.value = "{outline}";')

    class_names = 'panel-info ng-tns-c83-4 ng-star-inserted'
    while driver.find_element_by_class_names(class_names).text == '265':
        time.sleep(0.2)
        textarea.send_keys(' ')

    outline = get_textfield(driver, textarea)
    sector['outline'] = outline.strip()


def get_textfield(driver, textarea):
    while True:
        if driver.execute_script('return localStorage.getItem("stopper");') == '1':
            driver.minimize_window()
            return driver.execute_script("return arguments[0].value;", textarea)
        else:
            time.sleep(0.1)


def ticket_sort_func(ticket):
    return ticket[3] * 1000000 + ticket[5] * 1000 + ticket[6]


def _update_textarea(driver):
    class_names = 'input-block ng-tns-c80-0'
    xpath = parse_utils.class_names_to_xpath(class_names)
    driver.expl_wait('xpath', xpath)
    driver.execute_script(inject_script)
    return driver.find_element_by_class_names(class_names) \
                 .find_element_by_tag_name('textarea')


driver = None

inject_script = files(js).joinpath('inject.js').read_text()
