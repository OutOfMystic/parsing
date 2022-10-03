from . import scheme
from . import base


class CustomPrompt(base.CommandPrompt):
    def __init__(self):
        super().__init__()
        self.handler = home

    @staticmethod
    def list_(args_row):
        args = args_row.split(' ')
        if args[0] == 'scheme':
            return scheme.list_scheme()
        else:
            print('What needs to be listed?')

    @staticmethod
    def select(args_row):
        args = args_row.split(' ')
        if args[0] == 'scheme':
            if len(args) != 2:
                raise RuntimeError('Incorrect syntax')
            scheme_id = args[1]
            return scheme.select_scheme(scheme_id)
        else:
            print(f'{args[0]} cannot be selected?')


def home(cmd, args_row, value):
    if cmd == 'list':
        return CustomPrompt.list_(args_row)
    elif cmd == 'select':
        return CustomPrompt.select(args_row)
    else:
        raise RuntimeError(f'No command "{cmd}" found')