from src.loading.loading_files import (get_all_SEATS,
                                       get_reformat_SVG,
                                       get_list,
                                       write_to_export)
from .work_with_data import make_row_and_seats
from ..svg.reformat_svg import scale_path_data

def get_data_with_all_sectors(SCALE_X,SCALE_Y,
                              need_reformat=True):
    segments = get_all_SEATS()
    data_with_all_sectors = {}
    for sector in segments:
        #print(sector)
        sector_name = sector.get('name')
        segmentCategory = {} #sector.get('segmentCategory')  #TODO тип сектора
        totalPlaces = sector.get('totalPlaces')
        sector_path = sector.get("shapes")[0].get('path')#координаты для svg
        all_rows_and_seats_in_sector : list = make_row_and_seats(sector.get('segments'),
                                                                SCALE_X,
                                                                SCALE_Y,
                                                                need_reformat)
        sector_coordinates = sector.get("shapes")[0].get('labels')[0]#координаты x, y

        data_with_all_sectors.setdefault(sector_name, {}).update({
            'path': sector_path,
            'all_rows_and_seats_in_sector': all_rows_and_seats_in_sector,
            'segmentCategory': segmentCategory,
            'sector_coordinates': sector_coordinates or {}
        })
    return data_with_all_sectors

def make_structure_with_all_sectors_and_seats(data_with_all_sectors,
                                              SCALE_X,
                                              SCALE_Y,
                                              need_reformat=True):
    count_sector_id = 0
    list_sector = []
    list_seats = []
    for sector_name, sector_info in data_with_all_sectors.items():
        #print(sector_name, sector_info)
        path = sector_info.get('path')
        admission = sector_info.get('segmentCategory')
        x = sector_info.get('sector_coordinates')['x']
        y = sector_info.get('sector_coordinates')['y']
        sector_data = {
            'name': sector_name,
            'outline': scale_path_data(path, SCALE_X, SCALE_Y),
            'x': x * SCALE_X if need_reformat else x,
            'y': y * SCALE_Y if need_reformat else y
        }
        if admission:# если танцпол то добавим вот это к информации о секторе
            sector_data.update({"count": 1})

        list_sector.append(sector_data)

        for place in sector_info['all_rows_and_seats_in_sector']:
            x_coord = place.get('x')
            y_coord = place.get('y')
            row_number = place.get('row')
            place_number = place.get('place_number')

            data_seat = [x_coord, y_coord, 0, count_sector_id, 0, row_number, place_number, 0]
            if admission:
                data_seat.append(1)
            if not admission:
                data_seat.append(0)
            list_seats.append(data_seat)
        count_sector_id += 1

    return list_sector, list_seats

def formatting_json_data_and_write_in_file(name_scheme: str):
    '''
    создаем json файл для отправки на сервер
    '''
    sectors_for_json = get_list('list_sector')
    seats_for_json = get_list('list_seats')

    get_svg_scheme = get_reformat_SVG()
    output_json_data = {"name": name_scheme,
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
    name_scheme_for_frite = name_scheme_for_frite.replace(" ", '_')
    write_to_export(name_scheme_for_frite,
                    output_json_data)

    return output_json_data
