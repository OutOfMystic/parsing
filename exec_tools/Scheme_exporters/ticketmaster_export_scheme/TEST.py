import requests
import json

from bs4 import BeautifulSoup

from src.svg.reformat_svg import SVG, scale_path_data
#from JUPYTER import scale_path_data

def loading_all_data_from_ticketmaster(url_with_all_places=None,
                                       svg_url=None):
    headers = {
        "sec-ch-ua": "\"Google Chrome\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Linux\"",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    url_with_all_places = 'https://mapsapi.tmol.co/maps/geometry/3/event/10661/placeDetailNoKeys?systemId=MFX&useHostGrids=true&domain=UnitedArabEmirates&app=PRD1741_ICCP-FE'
    r1 = requests.get(url_with_all_places, headers=headers)
    print('LOADING ALLINFORMATION ABOUT PLACE STATUS CODE: ', r1.status_code)
    with open('data/download_from_ticketmaster/all_seats_ticketmaster.json', 'w', encoding='utf-8') as log_file:
        json.dump(r1.json(), log_file, indent=4, ensure_ascii=False)

    svg_url = 'https://mapsapi.tmol.co/maps/geometry/image/33/47/334779?removeFilters=ISM_Shadow&tmSansFonts=true&app=PRD1741_ICCP-FE'
    ##'https://mapsapi.tmol.co/maps/geometry/image/33/39/333922?removeFilters=ISM_Shadow&tmSansFonts=true&app=PRD1741_ICCP-FE'
    r2 = requests.get(svg_url, headers=headers)
    print('LOADING svg STATUS CODE: ', r1.status_code)
    with open('data/download_from_ticketmaster/ticketmaster_svg.svg', 'w', encoding='utf-8') as f:
        f.write(r2.text)

#loading_all_data_from_ticketmaster()

def work_with_svg():
    svg = SVG(
            viewBox_width_new=7785,
            viewBox_height_new=5447,
            svg_width_new=7785,
            svg_height_new=5447)
    print((svg.viewBox_width_original,
             svg.viewBox_height_original,
             svg.svg_width_original,
             svg.svg_height_original), 'SEE COORDINATES HAVE USED IN MAIN.SVG')

    SCALE_X = svg.SCALE_X
    SCALE_Y = svg.SCALE_Y
    print(SCALE_X, SCALE_Y, 'scale_x, scale_y POSITIONS CONSTANT')
    #svg.make_new_svg() # создание свг по новым параметрам
    return SCALE_X, SCALE_Y, svg
SCALE_X, SCALE_Y, svg = work_with_svg()
# *********************************************************************************************************
# *********************************************************************************************************
# *********************************************************************************************************
# *********************************************************************************************************
from src.data_parse.work_with_data import make_row_and_seats

with open('data/final_data/ticketmaster_svg_FINISH.svg', 'r') as file:
    ticketmaster_svg_data = file.read()

with open('data/download_from_ticketmaster/all_seats_ticketmaster.json', 'r', encoding='utf-8') as file:
    ticketmaster_json_data = json.load(file)
    segments = ticketmaster_json_data.get('pages')[0].get('segments')#Список со всеми секторами

data_with_all_sectors = {}
for sector in segments:
    #print(sector)
    sector_name = sector.get('name')
    segmentCategory = {} #sector.get('segmentCategory')  #TODO тип сектора
    totalPlaces = sector.get('totalPlaces')
    sector_path = sector.get("shapes")[0].get('path')#координаты для svg
    all_rows_and_seats_in_sector : list = make_row_and_seats(sector.get('segments'),
                                                            SCALE_X,
                                                            SCALE_Y)
    sector_coordinates = sector.get("shapes")[0].get('labels')[0]#координаты x, y

    data_with_all_sectors.setdefault(sector_name, {}).update({
        'path': sector_path,
        'all_rows_and_seats_in_sector': all_rows_and_seats_in_sector,
        'segmentCategory': segmentCategory,
        'sector_coordinates': sector_coordinates or {}
    })
#print(data_with_all_sectors)
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
        'x': x * SCALE_X,
        'y': y * SCALE_Y
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


print('len(data_with_sector_info)', len(data_with_all_sectors))
print(data_with_all_sectors.keys())
print('list_sector', len(list_sector))
print('list_seats', len(list_seats))
print(list_sector[0])

def make_data_to_fill_svg(list_sector,
                          fill_sectors_with_seats=(
                                  ('fill', '#f0f8ff'),
                                  ('stroke', '#003153')
                          )):
    '''
    fill="#ffffff" Определяет цвет заливки элемента
    fill-opacity="1.0" Определяет прозрачность заливки элемента.
    stroke="#dddddd" Определяет цвет обводки (границы) элемента
    stroke-opacity="1.0" Определяет прозрачность обводки элемента
    stroke-width="7.0" Определяет ширину обводки элемента.
    '''
    dict_with_all_sectors_and_their_coordinates = {}
    for sector in list_sector:
        dict_with_all_sectors_and_their_coordinates.setdefault(sector['name'], {}).update({
            'x': sector['x'],
            'y': sector['y'],
            'fill_rules': fill_sectors_with_seats,
            'text_about_sector': {
                'font-family': 'ArialMT, Arial',
                'font-size': '80',
                'fill-rule': 'nonzero',
                'fill': '#666',
                'font-weight': 'normal'
            }
        })
    return dict_with_all_sectors_and_their_coordinates
dict_with_all_sectors_and_their_coordinates = make_data_to_fill_svg(list_sector)
svg.make_new_svg(dict_with_all_sectors_and_their_coordinates) # создание свг по новым параметрам

# # *********************************************************************************************************
def formatting_json_data_and_write_in_file(
    name_scheme: str,
    get_svg_scheme: str,
    sectors_for_json: list,
    seats_for_json: list
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

    with open(f'data/export/{name_scheme_for_frite}.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(output_json_data, indent=4, ensure_ascii=False))

    return output_json_data

scheme_name = 'test_B'
# output_json_data = formatting_json_data_and_write_in_file(scheme_name,
#                                         ticketmaster_svg_data,
#                                         list_sector,
#                                         list_seats)

def send_json_data_on_server(
    output_json_data: dict,
    name_scheme: str,
    venue_scheme: str,
    url_to_send='http://193.178.170.180'
) -> str:
    print('send_json_data_on_server')
    r_add = requests.post(
        f'{url_to_send}/api/add_scheme/',
        json=output_json_data
    )
    r_set_venue = requests.post(
        f'{url_to_send}/api/set-venue/',
        json={
            "name": name_scheme,
            "venue": venue_scheme
            }
    )
    print(f'SEND {name_scheme} TO {url_to_send} STATUS CODE:',r_add.status_code)
    if r_add.status_code == 200 and r_set_venue.status_code == 200:
        return 'Схема отпрвленна'
    elif r_add.status_code != 200 and r_set_venue.status_code != 200:
        return 'Возникла ошибка с добавлением схемы и с изменением venue'
    elif r_add.status_code != 200:
        return 'Возникла ошибка с добавлением схемы'
    elif r_set_venue.status_code != 200:
        return 'Возникла ошибка с изменением venue'
# with open('data/export/test_A.json', 'r', encoding='utf-8') as file:
#     output_json_data = json.load(file)
# res = send_json_data_on_server(output_json_data,
#                                'test_A',
#                                'test_A')
# print(res)