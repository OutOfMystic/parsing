import json
import requests

from loguru import logger

from .base import get_command_docs
from ..connection import db_manager
from . import sector, constructing, base, command


def select_scheme(id_):
    db_manager.execute("SELECT name, json FROM public.tables_constructor"
                       f" WHERE id={id_}")
    payload = db_manager.fetchall()
    if not payload:
        raise RuntimeError(f'Didn\'t find scheme with id {id_}')
    to_store = list(payload[0])
    to_store.append(id_)
    return handle_scheme, to_store, to_store[0]


def handle_scheme(cmd, args_row, value):
    scheme_name, scheme, scheme_id = value
    if cmd == 'quit':
        return command.get_home('', '', None)
    elif cmd == 'list':
        return list_sectors(scheme_name, scheme)
    elif cmd == 'select':
        select_sector(args_row, scheme, scheme_name, scheme_id)
    elif cmd == 'show':
        show_sectors(scheme_name, scheme)
    elif cmd == 'concat':
        args = base.split_args(args_row)
        if len(args) < 2:
            raise RuntimeError('Not enough arguments')
        else:
            if args[-2] == '-n':
                name = args[-1]
                args = args[:-2]
            else:
                name = None
            if len(args) < 2:
                print('Not enough arguments')
            try:
                int_args = [int(arg) for arg in args]
            except:
                raise RuntimeError('Concat arguments in exclusion of name should be numbers')
            concat_sectors(scheme, *int_args, name=name)
    elif cmd == 'save':
        save_scheme(scheme, scheme_id)
    elif cmd == 'outline':
        new_main_id = int(args_row)
        main_sector = scheme['sectors'][new_main_id]
        constructing.change_outline(main_sector)
    else:
        print(f'Unknown command "{cmd}". May be you wanted to'
              f' quit before?')


def show_sectors(scheme_name, scheme):
    """
    detailed display of each sector
    """
    print(scheme_name + ':')
    for i, _ in enumerate(scheme['sectors']):
        print(i, end=' ')
        sector_data = sector.get_sector(scheme, i)
        sector.detail_sector(*sector_data)


def list_scheme(args_row):
    """
    lists scheme ids and names from the database
    """
    db_manager.execute("SELECT id, name FROM public.tables_constructor")
    records = db_manager.fetchall()
    base.print_cols(records, (4, 60))


def select_sector(args_row, constructor, scheme_name, scheme_id):
    """
    params: ["sector"] [sector_name]
    select sector with name {sector_name} and switches to SECTOR mode
    """
    if not args_row.startswith('sector'):
        print('Have you meant "select sector"?')
        return
    args = args_row.split(' ')
    if args[0] == 'sector':
        if len(args) != 2:
            raise RuntimeError('Incorrect syntax')
        sector_id = int(args[1])
        return sector.select_sector(constructor, sector_id, scheme_name, scheme_id)
    else:
        print(f'{args[0]} cannot be selected?')


def list_sectors(sector_name, constructor):
    """
    list sector names in the current scheme
    """
    sectors = constructor['sectors']
    sectors_counter = [0 for _ in sectors]
    for ticket in constructor['seats']:
        sector_num = ticket[3]
        sectors_counter[sector_num] += 1

    print_data = []
    for i, sector_count in enumerate(sectors_counter):
        row = [i, sectors[i]['name'], sector_count]
        print_data.append(row)
    max_sec_name_length = max([len(sec['name']) for sec in sectors])

    print(f'"{sector_name}" sectors:')
    base.print_cols(print_data, (4, max_sec_name_length + 1, 5))
    return handle_scheme, None


def concat_sectors(constructor, main_sector_id, *sector_ids, name=None):
    """
    params: [subject_sector] [object_sector1] (object_sector2...) ("-n" new_name)
    replaces seats from object sectors into a subject. {"-n"} param is applied if you also want to name a new sector
    """
    assert main_sector_id not in sector_ids, f"Sector #{main_sector_id} is in both" \
                                             f" main and minor cases"
    sector_count = len(constructor['sectors'])
    assert max(sector_ids) < sector_count, f"Sector #{max(sector_ids)} is not " \
                                            f"less than amount ({sector_count})"
    main_name, main_sector = sector.get_sector(constructor, main_sector_id)
    for sector_id in sector_ids:
        minor_sector = sector.get_sector(constructor, sector_id)
        constructing.union(main_name, main_sector, *minor_sector)
    new_main_id = constructing.delete_sectors(constructor, sector_ids,
                                              main_sector_id=main_sector_id)
    main_sector = constructor['sectors'][new_main_id]
    constructing.change_outline(main_sector)
    if name:
        constructor['sectors'][new_main_id]['name'] = name
        main_name = name
    print(f'Sectors were concatenated into a one sector with name {main_name}')


def save_scheme(constructor, scheme_id):
    """
    saves changes to the database
    """
    print('Updating constructor...')
    jsoned = json.dumps(constructor)
    script = ("UPDATE public.tables_constructor " 
             f"SET json='{jsoned}' WHERE id={scheme_id}")
    db_manager.execute(script)
    db_manager.commit()

    print('Refrshing all events with given scheme. It may take a while...')
    url = 'http://nebilet.fun/api/refresh_scheme'
    try:
        r = requests.post(url, json={'id': scheme_id})
    except Exception as err:
        raise RuntimeError(f'Request error: {err}\nSAVE SCHEME AGAIN OR IT WILL CAUSE A SHIT')
    if not r.text:
        raise RuntimeError('Empty response. SAVE SCHEME AGAIN OR IT WILL CAUSE A SHIT')
    try:
        r.json()
    except:
        print(r.text)
        raise RuntimeError(f'Response has unexpected format\n'
                           f'SAVE SCHEME AGAIN OR IT WILL CAUSE A SHIT')
    status = r.json()['status']
    if status != 'Success':
        raise RuntimeError(f'Error: {status}. SAVE SCHEME AGAIN OR IT WILL CAUSE A SHIT')
    print(f'Successfully saved scheme #{scheme_id}!')


def show_help():
    """
    show help on SCHEME level
    """
    for original_command, cmd_func in commands.items():
        docs = get_command_docs(original_command, cmd_func)
        print(docs)


def get_home(cmd, args_row, value):
    """
    switch back to MAIN mode
    """
    print('You are now in a main menu')
    return home, None, 'Main'


def home(cmd, args_row, value):
    if cmd in commands:
        to_call = commands[cmd]
        return to_call(args_row)
    else:
        raise RuntimeError(f'No command "{cmd}" found')


commands = {
    'list': list_sectors,
    'show': show_sectors,
    'select': select_sector,
    'save': save_scheme,
    'quit': get_home,
    'concat': concat_sectors,
    'outline': constructing.change_outline,
    'help': show_help
}
