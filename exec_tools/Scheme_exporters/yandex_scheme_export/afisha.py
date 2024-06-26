import json
import logging
from pathlib import Path
from bs4 import BeautifulSoup
import requests

from parse_module.drivers.selenium_with_puppeteer.chrome_driver_puppeteer import ChromeDriverPuppeteer

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent

def get_data(start_url):
    with ChromeDriverPuppeteer(search_phrases=['api/mds?key'],
                               debug_puppeteer=False,
                               file_to_write_path='test/performance/browser_log.json') as driver:
        driver.get(start_url)
        return driver.responses


def save_data_to_files(list_responses):
    for response in list_responses:
        url = response.get('url')
        print(url)
        if url[-1] == '3':
            body_str = response.get('body')
            with open('svg.json', 'w', encoding='utf-8') as f:
                f.write(body_str)
        else:
            body_str = response.get('body')
            decoded_body = json.loads(body_str)
            decoded_result = json.loads(decoded_body["result"])
            with open('seats.json', 'w', encoding='utf-8') as f:
                json.dump(decoded_result, f, indent=4, ensure_ascii=False)


def make_test_logs():
    with open('seats.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    with open('test/logs/formatted_seats.json', 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)

    with open('svg.json', 'r', encoding='utf-8') as infile, \
            open('test/logs/formatted_svg.json', 'w', encoding='utf-8') as outfile:
        data_svg = json.load(infile)
        result_content = data_svg['result']
        data_svg['result'] = result_content
        json.dump(data_svg, outfile, ensure_ascii=False, indent=4)
    print('make data structure is successful')


def _get_sector(
        sector_name: str,  # 'Ложа 4, стол 36'
        sector_path: str,  # '  M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0 219.....'
        all_sector,  # soup_svg.find_all('tspan')
        # [<tspan x="104" y="31">Сцена</tspan>, <tspan x="739.551" y="800">26</tspan>,...]
        admission
):
    for sector in all_sector:
        # <tspan x="104" y="31">Сцена</tspan>
        sector_name_in_svg = sector.text  # Сцена
        sector_name = sector_name.replace('-', ' ')
        # print(sector_name_in_svg, sector.get('x').replace('\\"', '').replace('"', ''),
        #     sector.get('y').replace('\\"', '').replace('"', ''), sector_name)
        if_sector_name_is_okay = [
            not sector_name_in_svg.isdigit(),
            sector_name_in_svg.replace('-', ' ') in sector_name
        ]
        # print(admission, sector_name)
        if all(if_sector_name_is_okay):
            x = sector.get('x').replace('\\"', '').replace('"', '')
            y = sector.get('y').replace('\\"', '').replace('"', '')
            res = {
                'name': sector_name,
                'x': float(x),
                'y': float(y),
                'outline': sector_path
            }
            if admission:
                res.update({"count": 1})
        else:
            res = {'name': sector_name, 'x': 1, 'y': 1, 'outline': sector_path}
            if admission:
                res.update({"count": 1})
        return res


def make_sectors_and_seats():
    with open('seats.json', 'r', encoding='utf-8') as file:
        seats = json.load(file)
    with open('svg.json', 'r', encoding='utf-8') as file:
        svg_scheme = json.load(file)
        svg_scheme = svg_scheme.get('result')
    soup_svg = BeautifulSoup(svg_scheme, 'lxml')
    all_sector = soup_svg.find_all(
        'tspan')  # [<tspan x="104" y="31">Сцена</tspan>, <tspan x="739.551" y="800">26</tspan>,...]
    # print('all_sector', len(all_sector), all_sector)

    count_sector_id = 0

    all_levels_sector = seats.get('levels')
    data_with_sector_info = {}
    for sector in all_levels_sector:
        # print(sector)
        sector_name = sector.get('name')
        sector_path = sector.get('outline')
        all_seats = sector.get('seats')
        admission = sector.get('admission')

        data_with_sector_info.setdefault(sector_name, {}).update({
            'path': sector_path,
            'all_seats': all_seats,
            'admission': admission
        })

    # print(data_with_sector_info)
    # print('len(data_with_sector_info)', len(data_with_sector_info))
    # print('len(all_sector)', len(all_sector))
    list_sector = []
    list_seats = []
    for sector_name, sector_info in data_with_sector_info.items():
        sector_data = _get_sector(sector_name, sector_info.get('path'),
                                  all_sector, sector_info.get('admission'))
        # print('sector_data', sector_data)
        list_sector.append(sector_data)

        list_seats_in_this_sector = {}
        for place in sector_info['all_seats']:
            x_coord = place.get('x_coord')
            y_coord = place.get('y_coord')
            row_number = place.get('row')
            place_number = place.get('place')
            admission = sector_info.get('admission')
            if x_coord and y_coord:
                data_seat = [x_coord, y_coord, 0, count_sector_id, 0, row_number, place_number, 0]
                if admission:
                    data_seat.append(1)
                if not admission:
                    data_seat.append(0)
                list_seats.append(data_seat)
        count_sector_id += 1
    return svg_scheme, list_sector, list_seats


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

    # file_to_write = os.path.join(BASE_DIR, 'export')
    # file_to_write = os.path.join(
    #     file_to_write,
    #     f'{name_scheme_for_frite}.json'
    # )
    with open(f'export/{name_scheme_for_frite}.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(output_json_data, indent=4, ensure_ascii=False))
    return output_json_data


if __name__ == '__main__':
    responses = get_data(str(input("Введите url: "))) or ()
    assert len(responses) == 2, f"Expected 2 responses, but got {len(responses)}"
    save_data_to_files(responses)
    print('downloading svg.json and seats.json is success')
    #make_test_logs()
    venue_scheme = str(input("Введите venue: "))
    name_scheme = str(input("Введите название схемы: "))

    svg_scheme, list_sector, list_seats = make_sectors_and_seats()
    output_json_data = formatting_json_data_and_write_in_file(name_scheme,
                                                              svg_scheme,
                                                              list_sector,
                                                              list_seats)

    r_add = requests.post(
        'http://193.178.170.180/api/add_scheme/',
        json=output_json_data
    )
    r_set_venue = requests.post(
        'http://193.178.170.180/api/set-venue/',
        json={
            "name": name_scheme,
            "venue": venue_scheme
        }
    )
    if (r_add.status_code == 200) and (r_set_venue.status_code == 200):
        print('Схема отпрвленна')
    if r_add.status_code != 200:
        print('Возникла ошибка с добавлением схемы', r_add.status_code )
    if r_set_venue.status_code != 200:
        print('Возникла ошибка с изменением venue', r_add.status_code )