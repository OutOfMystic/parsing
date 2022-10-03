import os
import sys
import time
from importlib.resources import files

from ..drivers.selenium import ProxyWebDriver
from . import js


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

    new_sector = main + minor
    new_sector.sort(key=ticket_sort_func)
    return new_sector


def delete_sectors(constructor, sector_ids, main_sector_id=None):
    sector_ids = list(sector_ids)
    sector_ids.sort()
    sectors = constructor['sectors']
    decrement = 0
    replaces = {}

    last_sector_id = sector_ids.pop(0)
    for cur_id, sector in sectors:
        if cur_id - decrement > last_sector_id:
            if sector_ids:
                last_sector_id = sector_ids.pop(0)
                decrement += 1
            else:
                replaces[cur_id] = cur_id - decrement
        else:
            replaces[cur_id] = cur_id - decrement

    for decrement_, sector_id in enumerate(sector_ids):
        sector_id_fixed = sector_id - decrement_
        if main_sector_id:
            main_id_fixed = replaces[main_sector_id]
            main_sector = constructor['sectors'][main_id_fixed]
            outline = sectors[sector_id_fixed]
            main_sector['outline'] += ' ' + outline.strip()
        del sectors[sector_id_fixed]

    for before, after in replaces:
        apply_changes(constructor, before, after)


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

    class_names = 'app-input ng-tns-c80-0 ng-pristine ng-valid ng-touched'
    if driver.current_url != 'https://yqnn.github.io/svg-path-editor/':
        driver.get('https://yqnn.github.io/svg-path-editor/')
        driver.expl_wait('xpath', class_names)
        driver.execute_script(inject_script)

    textarea = driver.find_element_by_class_names(class_names)
    textarea.clear()
    textarea.send_keys(outline)

    outline = get_textfield(driver, textarea)
    sector['outline'] = outline


def get_textfield(driver, textarea):
    while True:
        if driver.execute_script("return stopper;"):
            driver.minimize_window()
            return driver.execute_script("return argumets[0].value;", textarea)
        else:
            time.sleep(0.1)


def ticket_sort_func(ticket):
    return ticket[3] * 1000000 + ticket[5] * 1000 + ticket[6]


driver = None

inject_script = files(js).joinpath('inject.js').read_text()
