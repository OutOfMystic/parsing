import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append('/home/lon8/python/parsing/')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from parse_module.manager import backend

from parse_module.manager.controller import Controller

DEBUG = False
DEBUG_DATA = 19309


if __name__ == '__main__':
    router, process = backend.get_router('parsing_main', 'cnwhUCJMIIrF2g')
    time.sleep(1)
    release = 'release' in sys.argv
    debug_url, debug_event_id = None, None
    if DEBUG:
        if isinstance(DEBUG_DATA, str): 
            debug_url = DEBUG_DATA
        elif isinstance(DEBUG_DATA, int):
            debug_event_id = DEBUG_DATA

    controller = Controller('parsers', 'parsers.json', router, debug_url=debug_url,
                            debug_event_id=debug_event_id, release=release)
    controller.run()
