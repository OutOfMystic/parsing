import _thread
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

import eel
import matplotlib.path as mplPath
import numpy as np
from bs4 import BeautifulSoup, ResultSet, Tag
from ..settings import BASE_DIR
from svg.path import parse_path


def _conversion_data_seats_and_sectors(
    svg_sceme: str,
    sectors_data: dict[str, str],
    coordinates_seats: list[tuple[int, ...]],
    correct_all_sectors: bool = False
) -> tuple[list]:
    soup_svg = BeautifulSoup(svg_sceme, 'xml')
    all_sector = soup_svg.find_all('tspan')#[<tspan x="104" y="31">Сцена</tspan>,
                                            # <tspan x="739.551" y="800">26</tspan>,...]

    dir_with_callback = os.path.join(BASE_DIR, 'dir_with_callback')
    file_callback_read = os.path.join(dir_with_callback, 'callback_read')
    file_callback_write = os.path.join(dir_with_callback, 'callback_write')
    file_order_sector = os.path.join(dir_with_callback, 'order_sector')

    old_sector_list, list_seats = _get_data_from_file(
        file_callback_read,
        file_callback_write,
        file_order_sector
    )
    list_sector = []

    count_sector_id = 0
    for sector_name, sector_path in sectors_data.items():
        # print(sector_name, 'sector_name###')
        # ('Ложа 4, стол 36'  sector_name
        # ' M149.0 675.0 L207.0 675.0 C213.6274185180664...' ) sector_path
        sector_data = _get_sector(sector_name, sector_path, all_sector)
        list_sector.append(sector_data)
        if sector_name.replace('-', ' ') in old_sector_list:
            count_sector_id += 1
            continue

        list_seats_in_this_sector = {}
        points = points_from_sector_path(sector_path)
        # print('points', points)  [(288.0, 644.0), (289.0175438596491, 644.0), (290.03508771929825, 644.0),....]
        bbPath = mplPath.Path(np.array(points))# Этот объект позволяет легко проверить,
                                                # находятся ли заданные точки внутри этой фигуры.
        for coordinate in coordinates_seats:
            # coordinate = (39.0, 479.0)
            if bbPath.contains_point(coordinate):#проверить, находится ли заданная точка внутри созданной фигуры.
                str_coordinate = f'{coordinate[0]} {coordinate[1]}'
                data_seat = str(
                    [coordinate[0], coordinate[1], 0, count_sector_id, 0]
                )
                list_seats_in_this_sector[str_coordinate] = data_seat

        if not list_seats_in_this_sector or \
                len(list_seats_in_this_sector) == 0:
            continue

        if correct_all_sectors:#Запуск ручного выбора нужных секторов
            list_seats_in_this_sector = eel.update_seats_in_sector(
                list_seats_in_this_sector,
                sector_name
            )()

            list_seats_in_this_sector = _create_http_server(
                list_seats_in_this_sector
            )
            for final_seat in list_seats_in_this_sector:
                if len(final_seat) > 7:
                    final_seat.extend([0, 1])
                else:
                    final_seat.extend([0, 0])
                list_seats.append(final_seat)
            count_sector_id += 1
        else:
            def update_seats_in_sector(list_seats_in_this_sector: dict, sector_name: str) -> dict:
                # В этой функции можно реализовать любую необходимую логику обновления данных о местах.
                # Для примера, можно просто вернуть те же данные без изменений.
                return list_seats_in_this_sector
            list_seats_in_this_sector = update_seats_in_sector(
                list_seats_in_this_sector,
                sector_name
            )
            for str_coordinate, data_seat in list_seats_in_this_sector.items():
                final_seat = eval(data_seat)
                if len(final_seat) > 7:
                    final_seat.extend([0, 1])
                else:
                    final_seat.extend([0, 0])
                list_seats.append(final_seat)
            count_sector_id += 1



        _create_data_in_file(
            file_callback_write,
            file_order_sector,
            sector_name,
            list_seats_in_this_sector
        )

    return list_sector, list_seats


def points_from_sector_path(svg_path: str) -> list:
    # ' M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0 219.0 680.3725829124451 219.0 687.0 L219.0 753.0
    # C219.0 759.6274185180664 213.6274185180664 765.0 207.0 765.0 L149.0 765.0 C142.37258291244507 765.0 137.0
    # 759.6274185180664 137.0 753.0 L137.0 687.0 C137.0 680.3725829124451 142.37258291244507 675.0 149.0 675.0 Z'
    points = []
    for path in parse_path(svg_path):
        # print(path, 'path_')
        # Line(start=(440+796j), end=(440+738j)) path_
        # CubicBezier(start=(440+738j), control1=(440+731.3725829124451j), control2=(445.37258291244507+726j), end=(452+726j), smooth=False) path_
        # Close(start=(452+726j), end=(452+726j)) path_
        # Move(to=(616+726j)) path_
        step = int(path.length())
        last_step = step - 1

        if last_step == 0:
            pos = path.point(0)
            points.append((pos.real, pos.imag, ))
        else:
            for distance in range(step):
                pos = path.point(distance / last_step)
                points.append((pos.real, pos.imag, ))
    # points [(288.0, 644.0), (289.0175438596491, 644.0), (290.03508771929825, 644.0), (291.05263157894734, 644.0),
    # (292.0701754385965, 644.0), (293.0877192982456, 644.0), (294.10526315789474, 644.0), (295.12280701754383, 644.0),
    # (296.140350877193, 644.0), (297.1578947368421, 644.0), (298.17543859649123, 644.0), (299.1929824561403, 644.0),
    # (300.2105263157895, 644.0), (301.2280701754386, 644.0), (302.2456140350877, 644.0), (303.2631578947368, 644.0),
    # (304.280701754386, 644.0), (305.29824561403507, 644.0), (306.3157894736842, 644.0), (307.3333333333333, 644.0),
    # (308.35087719298247, 644.0), (309.36842105263156, 644.0), (310.3859649122807, 644.0), (311.4035087719298, 644.0),
    # (312.42105263157896, 644.0), (313.43859649122805, 644.0), (314.4561403508772, 644.0), (315.4736842105263, 644.0),
    # (316.49122807017545, 644.0), (317.50877192982455, 644.0), (318.5263157894737, 644.0), (319.5438596491228, 644.0),
    # (320.56140350877195, 644.0), (321.57894736842104, 644.0), (322.5964912280702, 644.0), (323.6140350877193, 644.0),
    # (324.63157894736844, 644.0), (325.64912280701753, 644.0), (326.6666666666667, 644.0), (327.6842105263158, 644.0),
    # (328.70175438596493, 644.0), (329.719298245614, 644.0), (330.7368421052632, 644.0), (331.7543859649123, 644.0),
    # (332.7719298245614, 644.0), (333.7894736842105, 644.0), (334.8070175438596, 644.0), (335.82456140350877, 644.0),
    # (336.8421052631579, 644.0), (337.859649122807, 644.0), (338.8771929824561, 644.0), (339.89473684210526, 644.0),
    # (340.9122807017544, 644.0), (341.9298245614035, 644.0), (342.9473684210526, 644.0), (343.96491228070175, 644.0),
    # (344.9824561403509, 644.0), (346.0, 644.0), (346.0, 644.0), (347.15568032197734, 644.0549326236103),
    # (348.2802798696091, 644.2163779613759), (349.3687698485384, 644.4793072136993), (350.4161214644083, 644.8386915809821),
    # (351.41730592286245, 645.2895022636271), (352.36729442954373, 645.8267104620362), (353.2610581900956, 646.445287376612),...]
    return points


def _get_sector(
    sector_name: str,#'Ложа 4, стол 36'
    sector_path: str,#'  M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0 219.....'
    all_sector: ResultSet[Tag]# soup_svg.find_all('tspan')
        # [<tspan x="104" y="31">Сцена</tspan>, <tspan x="739.551" y="800">26</tspan>,...]
) -> dict[str]:
    for sector in all_sector:
        # <tspan x="104" y="31">Сцена</tspan>
        sector_name_in_svg = sector.text#Сцена
        sector_name = sector_name.replace('-', ' ')
        if_sector_name_is_okay = [
            not sector_name_in_svg.isdigit(),
            sector_name_in_svg.replace('-', ' ') in sector_name
        ]
        if all(if_sector_name_is_okay):
            x = float(sector.get('x'))
            y = float(sector.get('y'))
            return {
                'name': sector_name,
                'x': x,
                'y': y,
                'outline': sector_path
            }
    else:
        return {'name': sector_name, 'x': 1, 'y': 1, 'outline': sector_path}


def _create_http_server(list_seats_in_this_sector: list) -> list:
    class HandlerPost(BaseHTTPRequestHandler):
        def do_POST(self):
            def kill_me_please(server):
                server.shutdown()
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            nonlocal list_seats_in_this_sector
            list_seats_in_this_sector = eval(body)
            _thread.start_new_thread(kill_me_please, (httpd,))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = BytesIO()
            response.write(body)
            self.wfile.write(response.getvalue())

    class MyHTTPSServer(HTTPServer):
        def server_bind(self):
            import socket
            self.socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR, 1
            )
            self.socket.bind(self.server_address)

    httpd = MyHTTPSServer(('', 8040), HandlerPost)
    try:
        httpd.serve_forever()
    except Exception:
        pass
    httpd.server_close()
    return list_seats_in_this_sector


def _get_data_from_file(
    file_callback_read: str,
    file_callback_write: str,
    file_order_sector: str
) -> tuple[list]:
    with open(file_order_sector, 'w') as f:
        f.write('')
    list_sector = []
    list_seats = []
    with open(file_callback_read, 'r', encoding='utf-8') as f:
        callback_text = f.read()
        callback_list_text = eval(f'[{callback_text}]')
        for dict_data in callback_list_text:
            for sector_name, seats in dict_data.items():
                list_sector.append(sector_name)
                list_seats.extend(seats)
                with open(file_order_sector, 'a', encoding='utf-8') as f:
                    f.write(f'{sector_name}: {len(seats)}\n')

    with open(file_callback_write, 'w', encoding='utf-8') as f:
        f.write(callback_text)

    return list_sector, list_seats


def _create_data_in_file(
    file_callback_write: str,
    file_order_sector: str,
    sector_name: str,
    list_seats_in_this_sector: list
) -> None:
    with open(file_callback_write, 'a', encoding='utf-8') as f:
        data_to_write = {sector_name: list_seats_in_this_sector}
        f.write(
            json.dumps(
                data_to_write,
                indent=4,
                sort_keys=True,
                ensure_ascii=False
            ) + ','
        )
    with open(file_order_sector, 'a', encoding='utf-8') as f:
        f.write(f'{sector_name}: {len(list_seats_in_this_sector)}\n')
