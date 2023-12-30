import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parse_module.manager import backend

sys.path.append("/home/lon8/python/work/parsing/")

from parse_module.manager.controller import Controller

DEBUG = False
DEBUG_DATA = 26411


if __name__ == '__main__':
    router, process = backend.get_router()
    time.sleep(5)
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

