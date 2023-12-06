from . import base
from ..models.parser import db_manager


def route_cmd(args_row):
    """
    managing methods for event aliases. Multiple use cases:
        - event_alias add [origin] [alias]: add origin-alias pair to the database
        - event_alias del [origin]: removes origin-alias with given {origin} name
        - event_alias list: lists all origin-alias pairs
    """
    args = base.split_args(args_row)
    commands = {
        'add': add_alias,
        'del': del_alias,
        'list': list_alias
    }
    available = ', '.join(commands)
    if not args:
        raise AttributeError(f'Specify attribute. '
                             f'Available attributes are: {available}')
    cmd = args.pop(0)
    if cmd not in commands:
        raise AttributeError(f'"event_alias" attribute "{cmd}" wasn\'t found. '
                             f'Available attributes are: {available}')
    return commands[cmd](args)


def add_alias(args):
    if len(args) != 2:
        raise RuntimeError('There are should be 2 arguments: original name and alias name')
    origin, alias = args
    get_names()

    if origin in aliases:
        raise RuntimeError(f'Origin {origin} is already added with alias {alias}')

    db_manager.execute('SELECT event_name FROM public.tables_parsedevents')
    parsed_event_names = set(row[0] for row in db_manager.fetchall())
    if origin not in parsed_event_names:
        answer = base.get_y(f'There is no parsed event with name "{origin}" '
                            f'at the moment. It seems to have no effect.\n'
                            f'Are you sure you want to add this alias?')
        if answer is False:
            return

    db_manager.execute(f'INSERT INTO public.parsing_aliases '
                       f"(origin, alias) VALUES ('{origin}', '{alias}')")
    db_manager.commit()
    aliases[origin] = alias


def del_alias(args):
    if len(args) != 1:
        raise RuntimeError('Expected only one argument: original name')
    origin = args[0]
    get_names()

    if origin not in aliases:
        raise RuntimeError('Didn\'t find origin with given name')

    db_manager.execute(f"DELETE from public.parsing_aliases WHERE "
                       f"origin='{origin}'")
    db_manager.commit()
    del aliases[origin]


def list_alias(args):
    get_names()
    cols = list(aliases.items())
    base.print_cols(cols)


def get_names():
    global aliases
    if not aliases:
        db_manager.execute('SELECT origin, alias FROM public.parsing_aliases')
        aliases = {origin: alias for origin, alias in db_manager.fetchall()}


aliases = {}
