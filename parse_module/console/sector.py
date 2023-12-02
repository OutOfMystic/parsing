from . import scheme, base
from .base import get_command_docs
from ..utils import utils


def select_sector(constructor, sector_id, scheme_name, scheme_id):
    sector_name, sector = get_sector(constructor, sector_id)
    to_store = [constructor, scheme_name, scheme_id, sector_name, sector, sector_id]
    return handle_sector, to_store, sector_name


def handle_sector(cmd, args_row, value):
    constructor, scheme_name, scheme_id, sector_name, sector, sector_id = value
    if cmd == 'quit':
        return get_back_to_scheme(*value)
    elif cmd == 'show':
        detail_sector(sector_name, sector)
    elif cmd == 'apply':
        apply(sector, args_row)
    else:
        print(f'Unknown command "{cmd}". May be you wanted to quit before?')


def get_back_to_scheme(constructor, scheme_name, scheme_id, _, sector, sector_id):
    """
    return to SCHEME mode
    """
    apply_changes(constructor, sector, sector_id)
    value_to_store = [scheme_name, constructor, scheme_id]
    return scheme.handle_scheme, value_to_store, scheme_name


def get_sector(constructor, sector_id: int):
    if sector_id >= len(constructor['sectors']):
        raise RuntimeError(f'No sector with id {sector_id}')
    seats = constructor['seats']
    sector = [seat for seat in seats if seat[3] == sector_id]
    sector_name = constructor['sectors'][sector_id]['name']
    return sector_name, sector


def apply_changes(constructor, sector, sector_id):
    seats = constructor['seats']
    ticket_indexes = [index for index, ticket in enumerate(seats)
                      if ticket[3] == sector_id]
    for index in ticket_indexes[::-1]:
        del seats[index]
    seats.extend(sector)


def detail_sector(sector_name, sector):
    """
    detailed display of rows and seats of the current sector
    """
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

    list_rows = rows.items()
    list_rows = list(list_rows)
    list_rows.sort(key=lambda row: row[0])

    """last_row = list_rows[0][0]
    list_rows_solid = []
    for row in list_rows:
        row_num = row[0]
        for inserting_row in range(last_row + 1, row_num):
            to_insert = [inserting_row, []]
            list_rows_solid.append(to_insert)
        list_rows_solid.append(row)
        last_row = row_num"""

    rows_mins = [min(int_row(row)) for row in rows.values()]
    min_seat = min(rows_mins)

    str_rows = []
    for row_num, row in list_rows:
        row = list(set(row))
        int_part = int_row(row)
        str_part = [item for item in row if isinstance(item, str)]
        int_part.sort()
        last_seat = min_seat - 1
        row_str = f'|{row_num}|'.ljust(5)
        for seat in int_part:
            backspaces = (seat - last_seat - 1) * 3
            if backspaces > 0:
                row_str += '-' + ('-' * (backspaces - 2)) + ' '
            row_str += str(seat).ljust(3)
            last_seat = seat
        row_str += ' '
        for seat in str_part:
            row_str += seat.ljust(3)
        str_rows.append(row_str)
    connected_rows = '\n'.join(str_rows)

    mes = f'{sector_name}\n{connected_rows}'
    print(mes)


def apply(sector, arg_row):
    """
    params: [selector] [command]
    applies {command} to tickets' configuration selected by {selector}, eg (apply "row == 2" "seat += 1")
    """
    args = base.split_args(arg_row)
    if len(args) != 2:
        raise RuntimeError('There should be two arguments in the command: '
                           'condition and operation')
    condition, operation = args
    compliance = {
        'row': 'ticket[5]',
        'seat': 'ticket[6]'
    }
    for keyword, alias in compliance.items():
        operation = operation.replace(keyword, alias)
        condition = condition.replace(keyword, alias)

    affected = 0
    program = (f'if {condition}:\n'
               f'    {operation}\n'
               f'    affected += 1')
    for ticket_id, ticket in enumerate(sector):
        bare_try(ticket, 5)
        bare_try(ticket, 6)

        current_locals = {'ticket': ticket, 'affected': affected}
        exec(program, {}, current_locals)

        got_ticket = current_locals['ticket']
        sector[ticket_id] = got_ticket
        affected = current_locals['affected']
    print(f'{affected} seats were affected')


def bare_try(ticket, index):
    try:
        ticket[index] = int(ticket[index])
    except:
        pass


def int_row(row):
    return [item for item in row if isinstance(item, int)]


def show_help():
    """
    show help on SECTOR level
    """
    for original_command, cmd_func in commands.items():
        docs = get_command_docs(original_command, cmd_func)
        print(docs)


commands = {
    'quit': get_back_to_scheme,
    'show': detail_sector,
    'apply': apply,
    'help': show_help
}