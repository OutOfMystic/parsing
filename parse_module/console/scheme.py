import json

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
        print('You are now in a main menu')
        return command.get_home('', '', None)
    elif cmd == 'list':
        return list_sectors(scheme_name, scheme)
    elif cmd == 'select':
        if args_row.startswith('sector'):
            return select_sector(args_row, scheme, scheme_id)
        else:
            print('Have you meant "select sector"?')
    elif cmd == 'show':
        print(scheme_name + ':')
        for i, _ in enumerate(scheme['sectors']):
            print(i, end=' ')
            sector_data = sector.get_sector(scheme, i)
            sector.detail_sector(*sector_data)
    elif cmd == 'concat':
        args = base.split_args(args_row)
        if len(args) < 2:
            print('Not enough arguments')
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
    else:
        print(f'Unknown command "{cmd}". May be you wanted to'
              f' quit before?')


def list_scheme():
    db_manager.execute("SELECT id, name FROM public.tables_constructor")
    records = db_manager.fetchall()
    base.print_cols(records, (4, 60))


def select_sector(args_row, constructor, scheme_id):
    args = args_row.split(' ')
    if args[0] == 'sector':
        if len(args) != 2:
            raise RuntimeError('Incorrect syntax')
        sector_id = int(args[1])
        return sector.select_sector(constructor, sector_id, scheme_id)
    else:
        print(f'{args[0]} cannot be selected?')


def list_sectors(sector_name, constructor):
    sectors = constructor['sectors']
    sectors_counter = [0 for _ in sectors]
    for ticket in constructor['seats']:
        sector_num = ticket[3]
        sectors_counter[sector_num] += 1

    print_data = []
    for i, sector_count in enumerate(sectors_counter):
        row = [i, sectors[i]['name'], sector_count]
        print_data.append(row)
    print(f'"{sector_name}" sectors:')
    base.print_cols(print_data, (4, 30, 5))
    return handle_scheme, None


def concat_sectors(constructor, main_sector_id, *sector_ids, name=None):
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
    constructing.change_outline(constructor, new_main_id)
    if name:
        constructor['sectors'][new_main_id]['name'] = name
        main_name = name
    print(f'Sectors were concatenated into a one sector with name {main_name}')


def save_scheme(constructor, scheme_id):
    jsoned = json.dumps(constructor)
    script = ("UPDATE public.tables_constructor " 
             f"SET json='{jsoned}' WHERE id={scheme_id}")
    db_manager.execute(script)
    db_manager.commit()
    print(f'Successfully saved scheme #{scheme_id}!')
