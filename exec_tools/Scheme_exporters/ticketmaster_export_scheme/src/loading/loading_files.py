import os
import requests
import json

# Получаем текущий рабочий каталог
current_dir = os.getcwd()

#Создаем пути для всех нужных файлов!
relative_path_for_seats = 'data/download_from_ticketmaster/all_seats_ticketmaster.json'
file_path_for_seats = os.path.join(current_dir, relative_path_for_seats)

relative_path_for_svg = 'data/download_from_ticketmaster/ticketmaster_svg.svg'
file_path_for_svg = os.path.join(current_dir, relative_path_for_svg)

relative_path_for_REFORMAT_svg = 'data/final_data/ticketmaster_svg_FINISH.svg'
file_path_for_REFORMAT_svg = os.path.join(current_dir, relative_path_for_REFORMAT_svg)

def loading_all_data_from_ticketmaster(url_with_all_places=None,
                                       svg_url=None):
    """
    На сайте ticketmaster нужно найти 2 ссылки
        :param url_with_all_places: пример содержимого смотри
            в data/download_from_ticketmaster/all_seats_ticketmaster.json
        :param svg_url: svg со схемой
        пример urls в example_with_urls.txt
    """
    headers = {
        "sec-ch-ua": "\"Google Chrome\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Linux\"",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    r1 = requests.get(url_with_all_places, headers=headers)
    print('LOADING ALL INFORMATION ABOUT PLACE STATUS CODE: ', r1.status_code)
    with open(file_path_for_seats, 'w', encoding='utf-8') as log_file:
        json.dump(r1.json(), log_file, indent=4, ensure_ascii=False)

    r2 = requests.get(svg_url, headers=headers)
    print('LOADING svg STATUS CODE: ', r1.status_code)
    with open(file_path_for_svg, 'w', encoding='utf-8') as f:
        f.write(r2.text)

def get_all_SEATS():
    with open(file_path_for_seats, 'r', encoding='utf-8') as file:
        ticketmaster_json_data = json.load(file)
        segments = ticketmaster_json_data.get('pages')[0].get('segments')  # Список со всеми секторами
    return segments

def get_reformat_SVG():
    with open(file_path_for_REFORMAT_svg, 'r') as file:
        ticketmaster_svg_data = file.read()
    return ticketmaster_svg_data

def get_file_to_export(name_scheme_for_frite):
    if '"' in name_scheme_for_frite or "'" in name_scheme_for_frite:
        name_scheme_for_frite = name_scheme_for_frite.replace('"', '')
        name_scheme_for_frite = name_scheme_for_frite.replace("'", '')
    name_scheme_for_frite = name_scheme_for_frite.replace(" ", '_')
    path = f'data/export/{name_scheme_for_frite}.json'
    path_to_write = os.path.join(current_dir, path)
    print(path_to_write)
    if os.path.exists(path_to_write):
        with open(path_to_write, 'r', encoding='utf-8') as file:
            content = json.load(file)
        return content
    else:
        return None

def get_list(filename):
    path = f'data/final_data/{filename}.json'
    path_to_write = os.path.join(current_dir, path)
    with open(path_to_write, 'r', encoding='utf-8') as file:
        content = json.load(file)
    return content

def write_to_export(name_scheme_for_frite,
                    output_json_data):
    path = f'data/export/{name_scheme_for_frite}.json'
    path_to_write = os.path.join(current_dir, path)
    with open(path_to_write, 'w', encoding='utf-8') as f:
        f.write(json.dumps(output_json_data, indent=4, ensure_ascii=False))


def write_list_to_json(data, filename):
    path = f'data/final_data/{filename}.json'
    path_to_write = os.path.join(current_dir, path)
    with open(path_to_write, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

