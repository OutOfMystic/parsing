from . import scheme, constructing, base
from ..utils import utils


def select_sector(constructor, sector_id, scheme_id):
    sector_name, sector = get_sector(constructor, sector_id)
    to_store = [sector_name, sector, scheme_id]
    return handle_sector, to_store, sector_name


def handle_sector(cmd, args_row, value):
    sector_name, sector, scheme_id = value
    if cmd == 'quit':
        return scheme.select_scheme(scheme_id)
    elif cmd == 'show':
        detail_sector(sector_name, sector)
    elif cmd == 'apply':
        apply(sector, args_row)
    else:
        print(f'Unknown command "{cmd}". May be you wanted to quit before?')


def get_sector(constructor, sector_id: int):
    if sector_id >= len(constructor['sectors']):
        raise RuntimeError(f'No sector with id {sector_id}')
    seats = constructor['seats']
    sector = [seat for seat in seats if seat[3] == sector_id]
    sector_name = constructor['sectors'][sector_id]['name']
    return sector_name, sector


def detail_sector(sector_name, sector):
    rows = {}
    for ticket in sector:
        row = ticket[5]
        seat = ticket[6]
        if row not in rows:
            rows[row] = []
        rows[row].append(seat)
    if not rows:
        print(f'{sector_name}\n' + utils.red('Empty sector'))
        return

    rows_mins = [min(row) for row in rows.values()]
    min_seat = min(rows_mins)

    str_rows = []
    for row_num, row in rows.items():
        row = list(set(row))
        row.sort()
        last_seat = min_seat - 1
        row_str = f'|{row_num}|'.ljust(5)
        for seat in row:
            backspaces = (seat - last_seat - 1) * 3
            if backspaces > 0:
                row_str += '-' + ('-' * (backspaces - 2)) + ' '
            row_str += str(seat).ljust(3)
            last_seat = seat
        str_rows.append(row_str)
    connected_rows = '\n'.join(str_rows)

    mes = f'{sector_name}\n{connected_rows}'
    print(mes)


def apply(sector, arg_row):
    args = base.split_args(arg_row)
    if len(args) != 2:
        raise RuntimeError('There should be two arguments in the command: '
                           'condition and operation')
    condition, operation = args
    program = (f'if ({condition}):\n'
               f'    {operation}\n'
               f'    affected += 1')

    affected = 0
    for ticket in sector:
        seat = ticket[6]
        row = ticket[5]
        exec(program, {'seat': seat, 'row': row, 'affected': affected})
    print(f'{affected} seats were affected')
