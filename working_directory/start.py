import json
import sys

from parse_module.manager.controller import Controller
from parse_module.connection import db_manager
from parse_module.manager.proxy.loader import parse_domain

DEBUG = False
DEBUG_DATA = 20207

"""print(parse_domain('https://msk.kassir.ru/'))"""


if __name__ == '__main__':
    release = 'release' in sys.argv[1:]
    debug_url, debug_event_id = None, None
    if DEBUG:
        if isinstance(DEBUG_DATA, str):
            debug_url = DEBUG_DATA
        elif isinstance(DEBUG_DATA, int):
            debug_event_id = DEBUG_DATA

    controller = Controller('parsers', 'parsers.json', debug_url=debug_url,
                            debug_event_id=debug_event_id, release=release)
    controller.run()


"""if __name__ == '__main__':
    db_manager.execute('UPDATE public.tables_tickets '
                       "SET status='not' "
                       "WHERE status='available'")
    db_manager.commit()
    print('request complete')"""


"""if __name__ == '__main__':
    mes = ('UPDATE public.tables_tickets '
           "SET status='not' "
           "WHERE (status='available')")
           #" AND (event_id_id=3119)")
    db_manager.execute(mes)
    db_manager.commit()
    print('request complete')"""


"""
if __name__ == '__main__':
    bookings = {}

    def init(source, priority):
        bookings[priority] = set()
        update(arr, source, priority)
        booking = []
        for i, ticket in enumerate(source):
            if ticket == 1:
                booking.append(i)
        bookings[priority] = set(booking)

    def get_prohibited(cur_priority):
        prohibited = set()
        to_union = [bookings[prior] for prior in bookings if prior < cur_priority]
        for booking in to_union:
            prohibited.update(booking)
        return prohibited

    def update(arr, source, cur_priority):
        prohibited = get_prohibited(cur_priority)
        booking = bookings[cur_priority]

        for i in range(len(arr)):
            if source[i] == 1:
                arr[i] = 1
                booking.add(i)
            elif source[i] == 0:
                if (i in booking) and (i not in prohibited):
                    arr[i] = 0
                booking.discard(i)
        print(cur_priority, arr)

    source10 = [1, 0, 0, 0, 0, 0, 0, 0, 0]
    source20 = [0, 0, 0, 1, 0, 0, 0, 0, 0]
    source30 = [0, 0, 0, 0, 0, 0, 1, 0, 0]

    source11 = [1, 0, 0, 1, 0, 0, 0, 0, 0]
    source21 = [0, 0, 0, 1, 0, 0, 1, 0, 0]
    source31 = [1, 0, 0, 0, 0, 0, 1, 0, 0]

    source12 = [0, 0, 0, 1, 1, 1, 0, 0, 0]
    source22 = [1, 1, 1, 0, 0, 0, 0, 0, 0]
    source32 = [0, 0, 0, 0, 0, 0, 1, 1, 1]

    arr = [0, 0, 0, 0, 0, 0, 0, 0, 0]"""
