import time

from . import scheme, observe, event_alias, sector
from . import base
from ..connection import db_manager
from ..utils import utils


class CustomPrompt(base.CommandPrompt):
    event_aliases = set()

    def __init__(self):
        super().__init__()
        self.first_cmds = [] # ['select scheme 19', 'select sector 0', 'apply "row==\'_\'" "row=\'1\'"', 'quit']
        self.handler = get_home
        self.handle('', '')

    @staticmethod
    def select(args_row):
        """
        params: ["scheme"/"sector"] [name]
        selects scheme or sector with given name and changes user dialog scenario
        """
        args = args_row.split(' ')
        if args[0] == 'scheme':
            if len(args) != 2:
                raise RuntimeError('Incorrect syntax')
            scheme_id = args[1]
            return scheme.select_scheme(scheme_id)
        elif not args[0]:
            print('What needs to be selected? May be "select scheme"?')
        else:
            print(f'{args[0]} cannot be selected')

    @staticmethod
    def db_command(args_row, search_key=None):
        """
        params: [command]
        select or update or delete request to database
        """
        assert (args_row != 'SELECT * from public.tables_tickets') or search_key, 'Ebobo?'
        allowed_cmds = ['select', 'update', 'delete']
        args = base.split_args(args_row)
        command = ' '.join(args)
        com_type = command.lower().split(' ')[0]

        db_manager.execute(command)
        if com_type == 'select':
            rows = db_manager.fetchall()
            if search_key is None:
                base.print_cols(rows)
            else:
                filtered = [row for row in rows if utils.str_in_elem(row, search_key)]
                base.print_cols(filtered)
        elif com_type in allowed_cmds:
            db_manager.commit()

    @staticmethod
    def get_db_table(args_row):
        """
        params: [name] (search_key)
        prints table with given {name} in console with {search_key} occurrence
        """
        args = base.split_args(args_row)
        if len(args) == 1:
            name, search_key = args[0], None
        elif len(args) == 2:
            name, search_key = args
        else:
            raise ValueError('There are should be 1 or 2 arguments')
        command = f'SELECT * from public.tables_{name}'
        return CustomPrompt.db_command(command, search_key=search_key)


def show_help(args_row):
    """
    show help on MAIN level
    """
    for original_command, cmd_func in commands.items():
        docs = base.get_command_docs(original_command, cmd_func)
        print(docs)


def show_help_all():
    print(f'1. Help on {utils.red("MAIN")} level')
    show_help(None)
    print(f'2. Help on {utils.red("SCHEME")} level')
    scheme.show_help()
    print(f'3. Help on {utils.red("SECTOR")} level')
    sector.show_help()


def get_home(cmd, args_row, value):
    print('You are now in a main menu')
    return home, None, 'Main'


def home(cmd, args_row, value):
    if cmd in commands:
        to_call = commands[cmd]
        return to_call(args_row)
    else:
        raise RuntimeError(f'No command "{cmd}" found')


def command(prompt):
    cmd_type, args_row = prompt.split(' ', 1)
    return home(cmd_type, args_row, None)


commands = {
    'list': scheme.list_scheme,
    'select': CustomPrompt.select,
    'table': CustomPrompt.get_db_table,
    'ai': observe.route_cmd,
    'event_alias': event_alias.route_cmd,
    'db': CustomPrompt.db_command,
    'help': show_help
}
