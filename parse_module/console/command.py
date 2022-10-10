from . import scheme
from . import base


class CustomPrompt(base.CommandPrompt):
    def __init__(self):
        super().__init__()
        self.handler = get_home
        self.handle('', '')

    @staticmethod
    def select(args_row):
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


def get_home(cmd, args_row, value):
    return home, None, 'Main'


def home(cmd, args_row, value):
    if cmd == 'list':
        return scheme.list_scheme()
    elif cmd == 'select':
        return CustomPrompt.select(args_row)
    else:
        raise RuntimeError(f'No command "{cmd}" found')