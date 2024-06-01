from typing import Optional, Union

from .requests_to_json_or_svg import requests_to_json_or_svg
from .requests_to_link import get_urls_from_main_url


def main_get_data(main_url: str,time_sleep: int) -> Optional[Union[None]]:
    '''
    Загрузка файлов и преобразование их Структуру Данных

    :param main_url: 'https://portalbilet.ru/events/vecherinka-comedy-club-tab/2024-07-26'
    :param time_sleep: 10
    :return:
        get_all_sector_with_svg_path: dict
                                    {
                                    "is_table": false,
                                    "leftover_threshold": 0,
                                    "sectors": [
                                        {
                                            "all": 5,
                                            "d": "e9d5f456-183b-46a2-acd6-e758d75c9322",
                                            "i": "OLD-35",
                                            "o": "",
                                            "r": []
                                        },...
                                    }
        get_all_seats: dict
                            {
                                "height": 892,
                                "id": "3518",
                                "bg": "https://cdn.pbilet.com/origin/bba5eb1b-334e-497c-b39e-385878220fb6.svg",
                                "categories": [],
                                "width": 960,
                                "coordinates": [
                                    {
                                        "x": 39.0,
                                        "y": 479.0
                                    },
                                    {
                                        "x": 59.0,
                                        "y": 479.0
                                    },...
                            }

        get_svg_scheme:svg file
                        <svg xmlns="http://www.w3.org/2000/svg" width="960" height="892"> ... </svg>
    '''
    url_to_data = get_urls_from_main_url(main_url, time_sleep)
    # [all_seats, svg_scheme, all_sector_with_svg_path]
    # url_to_data ilike ['https://event-api.pbilet.net/api/v1/hall_layouts/3518',
    #        'https://cdn.pbilet.com/origin/bba5eb1b-334e-497c-b39e-385878220fb6.svg',
    #        'https://api.pbilet.net/public/v1/tickets?currency_code=RUB&lang=ru&event_source_id=7460&event_date_id=248372']

    url_to_sector_with_svg_path = url_to_data.get('all_sector_with_svg_path')
    if url_to_sector_with_svg_path is None:
        return ("Возникла ошибка: нету ссылки для получения всех секторов из svg схемы")

    url_to_all_seats = url_to_data.get('all_seats')
    if url_to_all_seats is None:
        return "Возникла ошибка: нету ссылки для получения всех мест на схеме"

    url_to_svg_scheme = url_to_data.get('svg_scheme')
    if url_to_svg_scheme is None:
        return "Возникла ошибка: нету ссылки для получения svg схемы"

    get_all_sector_with_svg_path = requests_to_json_or_svg(
        url_to_sector_with_svg_path
    )
    get_all_seats = requests_to_json_or_svg(url_to_all_seats)

    get_svg_scheme = requests_to_json_or_svg(url_to_svg_scheme, False)
    if_request_is_error = [
        get_all_sector_with_svg_path is None,
        get_all_seats is None,
        get_svg_scheme is None
    ]
    if any(if_request_is_error):
        return 'Возникла ошибка запроса'

    return get_all_sector_with_svg_path, get_all_seats, get_svg_scheme
