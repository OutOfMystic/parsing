from ..utils import provision, utils
from ..utils.parse_utils import double_split, lrsplit


class CommandPrompt:

    def __init__(self):
        self.handler = self.home
        self.value = None
        self.prefix = None
        self.first_cmds = []

    def handle(self, cmd, args_row):
        """
        Handles command. If new handler is None, handler won't
        be changed. Stored value has the same behavior.
        """
        args_row = args_row.strip()
        result = provision.multi_try(self.handler, name='Command', tries=1,
                                     args=(cmd, args_row, self.value),
                                     raise_exc=False, use_logger=False)
        if result is None:
            handler, value = None, None
        elif result == provision.TryError:
            handler, value = None, None
        elif len(result) == 3:
            handler, value, prefix = result
            if prefix is not None:
                self.prefix = prefix
        else:
            handler, value = result
        if handler is not None:
            self.handler = handler
        if value is not None:
            self.value = value
        if self.prefix:
            print(self.prefix, end=': ')

    def start_prompt(self):
        while True:
            cmd = input() if not self.first_cmds else self.first_cmds.pop(0)
            cmd_parts = cmd.split(' ', 1)
            cmd = cmd_parts.pop(0)
            args_row = cmd_parts.pop(0) if cmd_parts else ''
            self.handle(cmd, args_row)

    def home(cmd, args_row, value):
        print('Blank prompt is used now. Overwrite the handler')
        return None, None, 'Main'


def get_home(cmd, args_row, value):
    print('You are now in a main menu')
    return CommandPrompt.home, None, 'Main' ###################


def print_cols(rows, widths=None, char=' ', indent=0):
    if not rows:
        print(' ' * indent + 'Nothing to display')
        return
    if not rows[0]:
        print('Nothing to display (empty columns)')
        return
    if widths is None:
        widths = [999999 for _ in rows[0]]

    cols = [[] for _ in rows[0]]
    for row in rows:
        for col_num, col_value in enumerate(row):
            item_len = len(str(col_value))
            cols[col_num].append(item_len)

    first_col = [row[0] for row in rows]
    if all(str(elem).isnumeric() for elem in first_col):
        rows.sort(key=lambda row: int(str(row[0])))

    to_print = ' ' * indent
    col_lens = [max(col) + 2 for col in cols]
    for row in rows:
        generator = zip(row, widths)
        for col_num, zipped in enumerate(generator):
            item, width = zipped
            width = min(width, col_lens[col_num])
            item = str(item).replace('\r', '').replace('\n', '\\n')
            if len(item) > width:
                to_print += item[:width]
            else:
                to_print += item.ljust(width, char)
        print(to_print)
        to_print = ' ' * indent


def split_args(args_row):
    delimiter = chr(12) + chr(228)

    quote_parts1 = args_row.split('"')[1:-1:2]
    for part in quote_parts1:
        args_row = args_row.replace(part, delimiter + chr(12), 1)

    quote_parts2 = args_row.split("'")[1:-1:2]
    for part in quote_parts2:
        args_row = args_row.replace(part, delimiter + chr(13), 1)

    args = args_row.split(' ')
    for i, arg in enumerate(args):
        if arg == '"' + delimiter + chr(12) + '"':
            replacement = quote_parts1.pop(0)
            args[i] = replacement
        if arg == "'" + delimiter + chr(13) + "'":
            replacement = quote_parts2.pop(0)
            args[i] = replacement

    return args


def get_y(message):
    message += ' [Y/N]: '
    answer = input(message)
    return answer.lower() == 'y'


def get_command_docs(name, func):
    docstring = func.__doc__
    if docstring is None:
        command = utils.green(name)
        return f'{command}: --no docs--'
    doc_rows = docstring.split('\n')
    doc_indent = 0
    first_row = doc_rows.pop()
    for char in first_row:
        if char == ' ':
            doc_indent += 1
        else:
            break

    formatted_rows = []
    for row in doc_rows:
        if not row.strip():
            continue
        row = row[doc_indent:]
        trigger = '- ' + name
        strip_row = row.strip()
        if not strip_row.startswith(trigger) or ': ' not in strip_row:
            formatted_rows.append(row)
            continue
        command_and_args = double_split(row, '- ', ': ')
        command = command_and_args.split('(')[0]
        command = command.split('[')[0]
        args = command_and_args.split(command)[1]
        command = utils.green(command)
        args = utils.blue(args)
        prefix = row.split('- ', 1)[0]
        content = row.split(': ', 1)[1]
        for arg in lrsplit(content, '{', '}'):
            arg = '{' + arg + '}'
            content = content.replace(arg, utils.blue(arg))
        formatted_row = f'{prefix}- {command}{args}: {content}'
        formatted_rows.append(formatted_row)

    params = ''
    first_row = formatted_rows[0]
    if first_row.startswith('params:'):
        formatted_rows.pop(0)
        params = first_row.split('params:')[1]
    content = formatted_rows.pop(0) if formatted_rows else ''
    for arg in lrsplit(content, '{', '}'):
        arg = '{' + arg + '}'
        content = content.replace(arg, utils.blue(arg))
    docstring = '\n'.join(formatted_rows)
    if docstring:
        docstring = '\n' + docstring
    command = utils.green(name)
    params = utils.blue(params)
    return f'{command}{params}: {content} {docstring}'
