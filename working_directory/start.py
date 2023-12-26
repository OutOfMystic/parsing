import sys

from parse_module.models import router

sys.path.append("/home/lon8/python/work/parsing/")

from parse_module.manager.controller import Controller

DEBUG = False
DEBUG_DATA = 20207


if __name__ == '__main__':
    router = router.get_router()
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

