import requests
import json


def read_file(filename, is_json=False):
    with open(filename, 'r', encoding='utf-8') as file:
        if is_json:
            data = json.load(file)
        else:
            data = file.read()

    return data

name = 'Ростовский цирк'
venue = 'Ростовский цирк'
schema = read_file('../../../parsing/exec_tools/add_scheme/schema_example.svg')
seats = read_file('../../../parsing/exec_tools/add_scheme/seats_example.json', is_json=True)
a_json = {
    'name': name,
    'schema': schema,
    'data': seats
}

r = requests.post('http://193.178.170.180/api/add_scheme/', json=a_json)
print(r.text)
r = requests.post('http://193.178.170.180/api/set-venue/', json={"name": name, "venue": venue})
print(r.text)