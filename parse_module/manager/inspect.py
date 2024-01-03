import io
import sys
import threading

from parse_module.console import base
from parse_module.manager.backstage import tasker
from parse_module.utils import utils
from parse_module.utils.logger import logger


class ControllerInterface(base.CommandPrompt):
    level = None
    source = None
    controller = None

    def __init__(self, controller):
        super().__init__()
        self.first_cmds = []  # ['select scheme 19', 'select sector 0', 'apply "row==\'_\'" "row=\'1\'"', 'quit']
        ControllerInterface.controller = controller
        self.handler = get_home
        self.handle('', '')

    @staticmethod
    def log_source(args_row):
        args = base.split_args(args_row)
        if len(args) == 1:
            pattern, level = args[0], None
        elif len(args) == 2:
            pattern, level = args
        else:
            raise ValueError('There are should be 1 or 2 arguments')
        ControllerInterface.source = pattern
        if level is not None:
            ControllerInterface.level = level.upper()

    @staticmethod
    def log_level(args_row):
        args = base.split_args(args_row)
        if len(args) == 1:
            level = args[0]
        else:
            raise ValueError('1 argument should be sent')
        ControllerInterface.level = level.upper()

    @staticmethod
    def clear(args_row):
        ControllerInterface.source = None
        ControllerInterface.level = None

    @staticmethod
    def get_back(args_row):
        utils.blueprint('Console flow resumed')
        logger.resume()

    @staticmethod
    def backstage(args_row):
        tasker.inspect_queue()
        input(utils.blue('Press any key to continue output stream...'))
        logger.resume()

    @staticmethod
    def pooling(args_row):
        ControllerInterface.controller.pool.inspect_queue()
        input(utils.blue('Press any key to continue output stream...'))
        logger.resume()


def get_home(cmd, args_row, value):
    return prespell_home, None, ' '


def prespell_home(cmd, args_row, value):
    logger.pause()
    utils.blueprint('Waiting for a command...')
    return process_command, None, ''


def process_command(cmd, args_row, stored):
    if cmd in commands:
        to_call = commands[cmd]
        to_call(args_row)
        if cmd in ['filter', 'level', 'clear']:
            logger.apply_filter(ControllerInterface.source, ControllerInterface.level)
        return prespell_home, None, ''
    else:
        raise RuntimeError(f'No command "{cmd}" found')


def run_inspection(controller, release=True):
    if release:
        console = ControllerInterface(controller)
        threading.Thread(target=console.start_prompt).start()
        return console


commands = {
    'source': ControllerInterface.log_source,
    'filter': ControllerInterface.log_source,
    'level': ControllerInterface.log_level,
    'clear': ControllerInterface.clear,
    'resume': ControllerInterface.get_back,
    'backstage': ControllerInterface.backstage,
    'pooling': ControllerInterface.pooling,
    'pool': ControllerInterface.pooling,
    '': ControllerInterface.get_back
}