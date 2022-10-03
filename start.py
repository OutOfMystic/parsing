from parse_module.manager.controller import Controller
from parse_module.connection import db_manager


if __name__ == '__main__':
    controller = Controller('parsers', 'parsers.json')
    controller.run()
    print('Ran')


"""if __name__ == '__main__':
    db_manager.execute('SELECT date from public.tables_event')
    data = db_manager.fetchall()
    print(data)
    print(data[0])
    print(type(data[0]))


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
