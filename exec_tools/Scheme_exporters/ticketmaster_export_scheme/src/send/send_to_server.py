import requests
def send_json_data_on_server(
    output_json_data: dict,
    name_scheme: str,
    venue_scheme: str,
    url_to_send='http://193.178.170.180'
) -> str:
    print('TRYING TO CONNECT TO: ', url_to_send)
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
