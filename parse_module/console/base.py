from .. utils import provision


class CommandPrompt:

    def __init__(self):
        self.handler = self.home
        self.value = None

    def handle(self, cmd, args_row):
        """
        Handles command. If new handler is None, handler won't
        be changed. Stored value has the same behavior.
        """
        args_row = args_row.strip()
        result = provision.multi_try(self.handler, name='Command', tries=1,
                                     args=(cmd, args_row, self.value),
                                     raise_exc=False)
        if result is None:
            handler, value = None, None
        elif result == provision.TryError:
            handler, value = None, None
        else:
            handler, value = result
        if handler is not None:
            self.handler = handler
        if value is not None:
            self.value = value

    def start_prompt(self):
        while True:
            cmd = input()
            cmd_parts = cmd.split(' ', 1)
            cmd = cmd_parts.pop(0)
            args_row = cmd_parts.pop(0) if cmd_parts else ''
            self.handle(cmd, args_row)

    def home(cmd, args_row, value):
        return None, None


def print_cols(rows, widths):
    if not rows:
        print('Nothing to display')
        return
    to_print = ''
    cols = [[] for _ in rows[0]]
    for row in rows:
        for col_num, col_value in enumerate(row):
            item_len = len(str(col_value))
            cols[col_num].append(item_len)
    col_lens = [max(col) + 2 for col in cols]
    for row in rows:
        generator = zip(row, widths)
        for col_num, zipped in enumerate(generator):
            item, width = zipped
            width = min(width, col_lens[col_num])
            item = str(item)
            if len(item) > width:
                to_print += item[:width]
            else:
                to_print += item.ljust(width)
        print(to_print)
        to_print = ''
