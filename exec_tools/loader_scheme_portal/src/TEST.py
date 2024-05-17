from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

import time
import json
import requests

def selenium():
    main_url='https://portalbilet.ru/events/vecherinka-comedy-club-tab/2024-07-26'

    options = Options()
    options.add_argument('--no-sandbox')
    #options.add_argument('--disable-gpu')
    #options.add_argument('--headless')

    # Настройка логирования
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url=main_url)
    time.sleep(5)
    driver.execute_script("window.scrollTo(0, 300);")

    #print(driver.get_log('performance'))
    # logs = driver.get_log('performance')
    # formatted_logs = [json.loads(log['message']) for log in logs]
    # Запись логов в JSON файл
    # with open('performance_logs.json', 'w', encoding='utf-8') as log_file:
    #     json.dump(formatted_logs, log_file, indent=4)

    time.sleep(.5)
    driver.execute_script("window.scrollTo(300, 500);")
    time.sleep(10)

    def process_browser_log_entry(entry):
        response = json.loads(entry['message'])['message']
        return response

    browser_log = driver.get_log('performance')
    events = [process_browser_log_entry(entry) for entry in browser_log]

    url_to_data = {}

    # network_logs = [entry for entry in formatted_logs if 'Network.requestWillBeSent' in entry['message']['method']]
    # # Пример вывода URL запросов
    # for log in network_logs:
    #     try:
    #         request = log['message']['params']['request']
    #         url = request.get('url')
    #     except KeyError:
    #         ...
    #     else:
    #         print(f"URL: {url}")

    for event in events:
        #print(event, 'event###')
        if event.get('params') is not None and \
                'Network.response' in event['method'] and \
                event['params'].get('response') is not None and \
                event['params']['response'].get('url') is not None:
            get_url = event['params']['response']['url']
            #print(get_url, 'get_url###')
            # if_url_is_correct = [
            #     'https://event-api' in get_url,
            #     #'/api/widget' in get_url
            # ]
            # if all(if_url_is_correct):
            #     if 'schema' in get_url:
            if 'https://event-api' in get_url:
                    url_to_data['all_seats'] = get_url
            if 'ticket' in get_url.split('/')[-1]:
                url_to_data['all_sector_with_svg_path'] = get_url
            if 'cdn.pbilet.com' in get_url:
                url_to_data['svg_scheme'] = get_url

    print(len(url_to_data), url_to_data.keys(), 'should be-> all_seats, svg_scheme, all_sector_with_svg_path')
    print(url_to_data.values())

selenium() #Получение ссылок для скачивания файлов
#dict_values(['https://event-api.pbilet.net/api/v1/hall_layouts/3518', 'https://cdn.pbilet.com/origin/bba5eb1b-334e-497c-b39e-385878220fb6.svg', 'https://api.pbilet.net/public/v1/tickets?currency_code=RUB&lang=ru&event_source_id=7460&event_date_id=248372'])

def requests_():
    def requests_to_json_or_svg(
        url: str,
        request_to_json: bool = True
    ):
        try:
            response = requests.get(url)
            #print(response.json())
            if response.status_code >= 400 and response.status_code <= 500:
                print.error(
                    f"{url}Возникла ошибка клиента {response.status_code}"
                )
            elif response.status_code >= 500:
                print(
                    f"{url}Возникла ошибка сервера {response.status_code}"
                )
            else:
                if request_to_json:
                    return response.json()
                else:
                    return response.text
            return None
        except requests.Timeout as e:
            print(f"Возникла ошибка(Timeout) {e}")
            return None
        except Exception as e:
            print(f"{url}Возникла ошибка {e}")
            return None

    urls = ['https://event-api.pbilet.net/api/v1/hall_layouts/3518',
            'https://cdn.pbilet.com/origin/bba5eb1b-334e-497c-b39e-385878220fb6.svg',
            'https://api.pbilet.net/public/v1/tickets?currency_code=RUB&lang=ru&event_source_id=7460&event_date_id=248372']
    url_to_all_seats, url_to_svg_scheme, url_to_sector_with_svg_path = urls

    get_all_sector_with_svg_path = requests_to_json_or_svg(url_to_sector_with_svg_path)
    with open('test/get_all_sector_with_svg_path.json', 'w', encoding='utf-8') as log_file:
        json.dump(get_all_sector_with_svg_path, log_file, indent=4)
    get_all_seats = requests_to_json_or_svg(url_to_all_seats)
    with open('test/get_all_seats.json', 'w', encoding='utf-8') as log_file:
        json.dump(get_all_seats, log_file, indent=4)
    get_svg_scheme = requests_to_json_or_svg(url_to_svg_scheme, False)
    with open('test/get_svg_scheme.svg', 'w', encoding='utf-8') as log_file:
        log_file.write(get_svg_scheme)

#requests_() Скачивание файлов


with open('test/get_all_sector_with_svg_path.json', 'r', encoding='utf-8') as file:
    get_all_sector_with_svg_path = json.load(file)
# Чтение JSON файла get_all_seats.json
with open('test/get_all_seats.json', 'r', encoding='utf-8') as file:
    get_all_seats = json.load(file)
# Чтение SVG файла get_svg_scheme.svg
with open('test/get_svg_scheme.svg', 'r', encoding='utf-8') as file:
    get_svg_scheme = file.read()

def _get_sector_data(get_all_sector_with_svg_path: json) -> dict[str, str]:
    sectors_data = {}
    all_sector = get_all_sector_with_svg_path['sectors']
    for sector in all_sector:
        sector_name = sector.get('i')
        sector_path_in_svg = sector.get('o')
        if sector_path_in_svg:
            sectors_data[sector_name] = sector_path_in_svg
    return sectors_data

sectors_data = _get_sector_data(get_all_sector_with_svg_path)
print('sectors_data', sectors_data)

def _get_coordinates_seats_generator(
    get_all_seats: json
) -> list[tuple[int, ...]]:
    coordinates_seats = []
    all_seats = get_all_seats['coordinates']
    for seat in all_seats:
        x = seat['x']
        y = seat['y']
        coordinates_seats.append((x, y))
    return coordinates_seats

coordinates_seats = _get_coordinates_seats_generator(get_all_seats)
print('coordinates_seats', coordinates_seats)


#------------------------------------------------------------------------------------------------

import _thread
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

import eel
import matplotlib.path as mplPath
import numpy as np
from bs4 import BeautifulSoup, ResultSet, Tag
from settings import BASE_DIR
from svg.path import parse_path


def update_seats_in_sector(list_seats_in_this_sector: dict, sector_name: str) -> dict:
    # В этой функции можно реализовать любую необходимую логику обновления данных о местах.
    # Для примера, можно просто вернуть те же данные без изменений.
    return list_seats_in_this_sector

def _conversion_data_seats_and_sectors(
    svg_sceme: str,#get_svg_scheme.svg
    sectors_data: dict[str, str],# {'Ложа 4, стол 36': ' M149.0 675.0 L207.0 675.0 C213.6274185180664...' , }
    coordinates_seats: list[tuple[int, ...]]# [(39.0, 479.0), (59.0, 479.0), (39.0, 610.0), (59.0, 610.0),...]
) -> tuple[list]:
    print('!!')
    soup_svg = BeautifulSoup(svg_sceme, 'xml')
    all_sector = soup_svg.find_all('tspan')#[<tspan x="104" y="31">Сцена</tspan>, <tspan x="739.551" y="800">26</tspan>,...]
    print(all_sector)

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
        #print(sector_name, 'sector_name###')
        # ('Ложа 4, стол 36'  sector_name
        # ' M149.0 675.0 L207.0 675.0 C213.6274185180664...' ) sector_path
        sector_data = _get_sector(sector_name, sector_path, all_sector)
        # sector_data {
        #     'name': sector_name,
        #     'x': x,
        #     'y': y,
        #     'outline': sector_path
        # }
        list_sector.append(sector_data)
        if sector_name.replace('-', ' ') in old_sector_list:
            count_sector_id += 1
            continue

        list_seats_in_this_sector = {}
        points = points_from_sector_path(sector_path)
        #print('points', points)  [(288.0, 644.0), (289.0175438596491, 644.0), (290.03508771929825, 644.0),....]
        bbPath = mplPath.Path(np.array(points))# Этот объект позволяет легко проверить,
                                                # находятся ли заданные точки внутри этой фигуры.
        for coordinate in coordinates_seats:
            #coordinate = (39.0, 479.0)
            if bbPath.contains_point(coordinate):#проверить, находится ли заданная точка внутри созданной фигуры.
                str_coordinate = f'{coordinate[0]} {coordinate[1]}'
                data_seat = str(
                    [coordinate[0], coordinate[1], 0, count_sector_id, 0]
                )
                list_seats_in_this_sector[str_coordinate] = data_seat

        if not list_seats_in_this_sector or \
                len(list_seats_in_this_sector) == 0:
            continue

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

        # list_seats_in_this_sector = eel.update_seats_in_sector(
        #     list_seats_in_this_sector,
        #     sector_name
        # )()
        #
        # list_seats_in_this_sector = _create_http_server(
        #     list_seats_in_this_sector
        # )

        # for final_seat in list_seats_in_this_sector:
        #     if len(final_seat) > 7:
        #         final_seat.extend([0, 1])
        #     else:
        #         final_seat.extend([0, 0])
        #     list_seats.append(final_seat)
        # count_sector_id += 1

        _create_data_in_file(
            file_callback_write,
            file_order_sector,
            sector_name,
            list_seats_in_this_sector
        )

    return list_sector, list_seats


def points_from_sector_path(svg_path: str) -> list:
    #' M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0 219.0 680.3725829124451 219.0 687.0 L219.0 753.0
    # C219.0 759.6274185180664 213.6274185180664 765.0 207.0 765.0 L149.0 765.0 C142.37258291244507 765.0 137.0
    # 759.6274185180664 137.0 753.0 L137.0 687.0 C137.0 680.3725829124451 142.37258291244507 675.0 149.0 675.0 Z'
    points = []
    for path in parse_path(svg_path):
        #print(path, 'path_')
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
    #points [(288.0, 644.0), (289.0175438596491, 644.0), (290.03508771929825, 644.0), (291.05263157894734, 644.0),
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
    # (351.41730592286245, 645.2895022636271), (352.36729442954373, 645.8267104620362), (353.2610581900956, 646.445287376612), (354.093568410161, 647.1402042077559), (354.85979629538343, 647.9064321558708), (355.554713051406, 648.7389424213585), (356.1732898838719, 649.6327062046214), (356.71049799842456, 650.5826947060617), (357.161308600707, 651.5838791260816), (357.52069289636256, 652.6312306650831), (357.7836220910344, 653.7197205234685), (357.9450673903658, 654.8443199016401), (358.0, 656.0), (358.0, 656.0), (358.0, 657.0175438596491), (358.0, 658.0350877192982), (358.0, 659.0526315789474), (358.0, 660.0701754385965), (358.0, 661.0877192982456), (358.0, 662.1052631578947), (358.0, 663.1228070175439), (358.0, 664.140350877193), (358.0, 665.1578947368421), (358.0, 666.1754385964912), (358.0, 667.1929824561404), (358.0, 668.2105263157895), (358.0, 669.2280701754386), (358.0, 670.2456140350877), (358.0, 671.2631578947369), (358.0, 672.280701754386), (358.0, 673.2982456140351), (358.0, 674.3157894736842), (358.0, 675.3333333333334), (358.0, 676.3508771929825), (358.0, 677.3684210526316), (358.0, 678.3859649122807), (358.0, 679.4035087719299), (358.0, 680.421052631579), (358.0, 681.438596491228), (358.0, 682.4561403508771), (358.0, 683.4736842105264), (358.0, 684.4912280701755), (358.0, 685.5087719298245), (358.0, 686.5263157894736), (358.0, 687.5438596491229), (358.0, 688.561403508772), (358.0, 689.578947368421), (358.0, 690.5964912280701), (358.0, 691.6140350877193), (358.0, 692.6315789473684), (358.0, 693.6491228070175), (358.0, 694.6666666666666), (358.0, 695.6842105263158), (358.0, 696.7017543859649), (358.0, 697.719298245614), (358.0, 698.7368421052631), (358.0, 699.7543859649123), (358.0, 700.7719298245614), (358.0, 701.7894736842105), (358.0, 702.8070175438596), (358.0, 703.8245614035088), (358.0, 704.8421052631579), (358.0, 705.859649122807), (358.0, 706.8771929824561), (358.0, 707.8947368421052), (358.0, 708.9122807017544), (358.0, 709.9298245614035), (358.0, 710.9473684210526), (358.0, 711.9649122807018), (358.0, 712.9824561403509), (358.0, 714.0), (358.0, 714.0), (357.9450673903658, 715.1556803219775), (357.7836220910343, 716.2802798696091), (357.52069289636256, 717.3687698485384), (357.16130860070695, 718.4161214644083), (356.7104979984245, 719.4173059228624), (356.1732898838719, 720.3672944295437), (355.55471305140605, 721.2610581900956), (354.85979629538343, 722.093568410161), (354.09356841016097, 722.8597962953834), (353.2610581900956, 723.5547130514061), (352.3672944295438, 724.1732898838719), (351.4173059228625, 724.7104979984247), (350.41612146440843, 725.161308600707), (349.3687698485384, 725.5206928963626), (348.2802798696091, 725.7836220910344), (347.1556803219774, 725.9450673903659), (346.0, 726.0), (346.0, 726.0), (344.9824561403509, 726.0), (343.96491228070175, 726.0), (342.94736842105266, 726.0), (341.9298245614035, 726.0), (340.9122807017544, 726.0), (339.89473684210526, 726.0), (338.87719298245617, 726.0), (337.859649122807, 726.0), (336.8421052631579, 726.0), (335.82456140350877, 726.0), (334.8070175438597, 726.0), (333.7894736842105, 726.0), (332.7719298245614, 726.0), (331.7543859649123, 726.0), (330.7368421052632, 726.0), (329.719298245614, 726.0), (328.70175438596493, 726.0), (327.6842105263158, 726.0), (326.6666666666667, 726.0), (325.64912280701753, 726.0), (324.63157894736844, 726.0), (323.6140350877193, 726.0), (322.5964912280702, 726.0), (321.57894736842104, 726.0), (320.56140350877195, 726.0), (319.5438596491228, 726.0), (318.5263157894737, 726.0), (317.50877192982455, 726.0), (316.49122807017545, 726.0), (315.4736842105263, 726.0), (314.4561403508772, 726.0), (313.43859649122805, 726.0), (312.42105263157896, 726.0), (311.4035087719298, 726.0), (310.3859649122807, 726.0), (309.36842105263156, 726.0), (308.35087719298247, 726.0), (307.3333333333333, 726.0), (306.3157894736842, 726.0), (305.29824561403507, 726.0), (304.280701754386, 726.0), (303.2631578947368, 726.0), (302.2456140350877, 726.0), (301.2280701754386, 726.0), (300.2105263157895, 726.0), (299.1929824561404, 726.0), (298.17543859649123, 726.0), (297.1578947368421, 726.0), (296.140350877193, 726.0), (295.1228070175439, 726.0), (294.10526315789474, 726.0), (293.0877192982456, 726.0), (292.0701754385965, 726.0), (291.0526315789474, 726.0), (290.03508771929825, 726.0), (289.0175438596491, 726.0), (288.0, 726.0), (288.0, 726.0), (286.8443199016401, 725.9450673903659), (285.7197205234684, 725.7836220910343), (284.6312306650831, 725.5206928963626), (283.58387912608146, 725.161308600707), (282.58269470606166, 724.7104979984243), (281.63270620462146, 724.1732898838717), (280.73894242135856, 723.554713051406), (279.9064321558708, 722.8597962953835), (279.14020420775597, 722.093568410161), (278.44528737661193, 721.2610581900956), (277.8267104620364, 720.3672944295437), (277.28950226362724, 719.4173059228626), (276.83869158098224, 718.4161214644084), (276.4793072136992, 717.3687698485385), (276.21637796137594, 716.2802798696091), (276.0549326236103, 715.1556803219775), (276.0, 714.0), (276.0, 714.0), (276.0, 712.9824561403509), (276.0, 711.9649122807018), (276.0, 710.9473684210526), (276.0, 709.9298245614035), (276.0, 708.9122807017544), (276.0, 707.8947368421053), (276.0, 706.8771929824561), (276.0, 705.859649122807), (276.0, 704.8421052631579), (276.0, 703.8245614035088), (276.0, 702.8070175438596), (276.0, 701.7894736842105), (276.0, 700.7719298245614), (276.0, 699.7543859649123), (276.0, 698.7368421052631), (276.0, 697.719298245614), (276.0, 696.7017543859649), (276.0, 695.6842105263158), (276.0, 694.6666666666666), (276.0, 693.6491228070175), (276.0, 692.6315789473684), (276.0, 691.6140350877193), (276.0, 690.5964912280701), (276.0, 689.578947368421), (276.0, 688.561403508772), (276.0, 687.5438596491229), (276.0, 686.5263157894736), (276.0, 685.5087719298245), (276.0, 684.4912280701755), (276.0, 683.4736842105264), (276.0, 682.4561403508771), (276.0, 681.438596491228), (276.0, 680.421052631579), (276.0, 679.4035087719299), (276.0, 678.3859649122807), (276.0, 677.3684210526316), (276.0, 676.3508771929825), (276.0, 675.3333333333334), (276.0, 674.3157894736842), (276.0, 673.2982456140351), (276.0, 672.280701754386), (276.0, 671.2631578947369), (276.0, 670.2456140350877), (276.0, 669.2280701754386), (276.0, 668.2105263157895), (276.0, 667.1929824561404), (276.0, 666.1754385964912), (276.0, 665.1578947368421), (276.0, 664.140350877193), (276.0, 663.1228070175439), (276.0, 662.1052631578948), (276.0, 661.0877192982456), (276.0, 660.0701754385965), (276.0, 659.0526315789474), (276.0, 658.0350877192982), (276.0, 657.0175438596491), (276.0, 656.0), (276.0, 656.0), (276.0549326236103, 654.84431990164), (276.21637796137594, 653.7197205234684), (276.4793072136992, 652.6312306650831), (276.8386915809822, 651.5838791260813), (277.2895022636272, 650.5826947060616), (277.8267104620363, 649.6327062046214), (278.4452873766119, 648.7389424213586), (279.14020420775597, 647.9064321558708), (279.9064321558708, 647.1402042077559), (280.7389424213586, 646.445287376612), (281.6327062046215, 645.8267104620363), (282.5826947060618, 645.2895022636272), (283.58387912608157, 644.8386915809823), (284.6312306650831, 644.4793072136993), (285.7197205234685, 644.2163779613759), (286.8443199016401, 644.0549326236103), (288.0, 644.0)]
    return points


def _get_sector(
    sector_name: str,#'Ложа 4, стол 36'
    sector_path: str,#'  M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0 219.....'
    all_sector: ResultSet[Tag]# soup_svg.find_all('tspan')
    # [<tspan x="104" y="31">Сцена</tspan>, <tspan x="739.551" y="800">26</tspan>,...]
) -> dict[str]:
    for sector in all_sector:
        # <tspan x="104" y="31">Сцена</tspan>
        sector_name_in_svg = sector.text #Сцена
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

# eel.init("web")
# eel.start('main.html', host='127.0.0.1', port=8010, block=False)
# #eel.start("main.html", host='127.0.0.1', port=8010, size=(600, 600))
sectors_for_json, seats_for_json = _conversion_data_seats_and_sectors(
        get_svg_scheme,
        sectors_data,
        coordinates_seats
    )
print(sectors_for_json, seats_for_json, '!!!', sep='\n')
#sectors_for_json {'name': 'Ложа 4, стол 36', 'x': 129.308, 'y': 564.0, 'outline': ' M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0
# 219.0 680.3725829124451 219.0 687.0 L219.0 753.0 C219.0 759.6274185180664 213.6274185180664
# 765.0 207.0 765.0 L149.0 765.0 C142.37258291244507 765.0 137.0 759.6274185180664 137.0 753.0
# L137.0 687.0 C137.0 680.3725829124451 142.37258291244507 675.0 149.0 675.0 Z', ...}
#seats_for_json[[158.0, 710.0, 0, 0, 0, 0, 0], [158.0, 730.0, 0, 0, 0, 0, 0], [178.0, 744.0, 0, 0, 0, 0, 0], [198.0, 744.0, 0, 0, 0, 0, 0]

name_scheme = 'TEST_only'

def formatting_json_data_and_write_in_file(
    name_scheme: str,
    get_svg_scheme: str,
    sectors_for_json: dict,
    seats_for_json: dict
) -> json:
    output_json_data = {
        "name": name_scheme,
        "schema": get_svg_scheme,
        "data": {
            "sectors": sectors_for_json,
            "seats": seats_for_json
        }
    }
    name_scheme_for_frite = name_scheme
    if '"' in name_scheme_for_frite or "'" in name_scheme_for_frite:
        name_scheme_for_frite = name_scheme_for_frite.replace('"', '')
        name_scheme_for_frite = name_scheme_for_frite.replace("'", '')

    file_to_write = os.path.join(BASE_DIR, 'json_schemes')
    file_to_write = os.path.join(
        file_to_write,
        f'{name_scheme_for_frite}.json'
    )
    with open(file_to_write, 'w', encoding='utf-8') as f:
        f.write(json.dumps(output_json_data, indent=4, ensure_ascii=False))

    return output_json_data

output_json_data = formatting_json_data_and_write_in_file(name_scheme,
                                        get_svg_scheme,
                                        sectors_for_json,
                                        seats_for_json)

def send_json_data_on_server(
    output_json_data: dict,
    name_scheme: str,
    venue_scheme: str
) -> str:
    print('send_json_data_on_server')
    r_add = requests.post(
        f'http://localhost:9000/api/add_scheme/',
        json=output_json_data
    )
    r_set_venue = requests.post(
        f'http://localhost:9000/api/set-venue/',
        json={
            "name": name_scheme,
            "venue": venue_scheme
            }
    )
    print(r_add.status_code)
    if r_add.status_code == 200 and r_set_venue.status_code == 200:
        return 'Схема отпрвленна'
    elif r_add.status_code != 200 and r_set_venue.status_code != 200:
        return 'Возникла ошибка с добавлением схемы и с изменением venue'
    elif r_add.status_code != 200:
        return 'Возникла ошибка с добавлением схемы'
    elif r_set_venue.status_code != 200:
        return 'Возникла ошибка с изменением venue'

# res = send_json_data_on_server(output_json_data, 'test_scheme', 'test_venue')
# print(res)