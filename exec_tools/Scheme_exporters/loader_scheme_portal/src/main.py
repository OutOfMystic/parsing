import json
import os
import sys

import eel
import requests
from src.data_processing_after_receipt.main_data_processing_after_receipt import processing_data_to_json_data
from src.get_data_for_processing.main_get_data_for_processing import main_get_data
from src.logging_to_project import logger_to_project
from src.settings import BASE_DIR, settings_project


def main(main_url: str, name_scheme: str, venue: str, time_sleep: int,
         correct_all_sectors: bool = False):
    data_from_request = main_get_data(main_url, time_sleep)
    if isinstance(data_from_request, str):
        return data_from_request
    get_all_sector_with_svg_path, get_all_seats, get_svg_scheme = data_from_request
    #Запись в файл для тестов
    # with open('test/get_all_sector_with_svg_path.json', 'w', encoding='utf-8') as log_file:
    #     json.dump(get_all_sector_with_svg_path, log_file, indent=4)
    # with open('test/get_all_seats.json', 'w', encoding='utf-8') as log_file:
    #     json.dump(get_all_seats, log_file, indent=4)
    # with open('test/get_svg_scheme.svg', 'w', encoding='utf-8') as log_file:
    #     log_file.write(get_svg_scheme)

    sectors_for_json, seats_for_json = processing_data_to_json_data(
            get_svg_scheme,
            get_all_sector_with_svg_path,
            get_all_seats,
            correct_all_sectors
        )
    # sectors_for_json {'name': 'Ложа 4, стол 36', 'x': 129.308, 'y': 564.0, 'outline': ' M149.0 675.0 L207.0 675.0 C213.6274185180664 675.0
    # 219.0 680.3725829124451 219.0 687.0 L219.0 753.0 C219.0 759.6274185180664 213.6274185180664
    # 765.0 207.0 765.0 L149.0 765.0 C142.37258291244507 765.0 137.0 759.6274185180664 137.0 753.0
    # L137.0 687.0 C137.0 680.3725829124451 142.37258291244507 675.0 149.0 675.0 Z', ...}
    # seats_for_json[[158.0, 710.0, 0, 0, 0, 0, 0], [158.0, 730.0, 0, 0, 0, 0, 0], [178.0, 744.0, 0, 0, 0, 0, 0], [198.0, 744.0, 0, 0, 0, 0, 0], ...]

    output_json_data = formatting_json_data_and_write_in_file(
        name_scheme,
        get_svg_scheme,
        sectors_for_json,
        seats_for_json
    )
    #print('ok!', output_json_data)
    result = send_json_data_on_server(output_json_data, name_scheme, venue)

    return result


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


def send_json_data_on_server(
    output_json_data: dict,
    name_scheme: str,
    venue_scheme: str
) -> str:
    r_add = requests.post(
        f'http://{settings_project.DOMAIN}/api/add_scheme/',
        json=output_json_data
    )
    r_set_venue = requests.post(
        f'http://{settings_project.DOMAIN}/api/set-venue/',
        json={
            "name": name_scheme,
            "venue": venue_scheme
            }
    )
    if r_add.status_code == 200 and r_set_venue.status_code == 200:
        return 'Схема отправлена'
    elif r_add.status_code != 200 and r_set_venue.status_code != 200:
        return 'Возникла ошибка с добавлением схемы и с изменением venue'
    elif r_add.status_code != 200:
        return 'Возникла ошибка с добавлением схемы'
    elif r_set_venue.status_code != 200:
        return 'Возникла ошибка с изменением venue'


@eel.expose
def post_inform(url: str, name: str, venue: str, time_sleep: str,
                correct_all_sectors: bool = False) -> str:
    if not url:
        return 'Заполните url'
    if not name:
        return 'Заполните name'
    if not venue:
        return 'Заполните venue'
    time_sleep = int(time_sleep)
    try:
        result = main(url, name, venue, time_sleep, correct_all_sectors)
    except Exception as error:
        result = 'Возникла непредвиденная ошибка'
        logger_to_project.exception(error)
    return result


if __name__ == '__main__':
    eel.init("web")
    eel.start("main.html", host='127.0.0.1', port=8010, size=(600, 600))
