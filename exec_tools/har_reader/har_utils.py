import json
import codecs


def pretty_print(obj, recursive=False, rec_val=0):
    space_init = ' ' * 2
    space = space_init * rec_val

    if isinstance(obj, list):
        print(f'{space}[')
        for item in obj:
            if recursive:
                pretty_print(item, True, rec_val + 1)
            else:
                print(f'{space_init}{item}')
        print(f'{space}]')
    elif isinstance(obj, dict):
        print(f'{space}{{')
        for key, val in obj.items():
            print(f'{space}{key}:')
            if recursive:
                pretty_print(val, True, rec_val + 1)
            else:
                print(f'{space_init }{val}')
        print(f'{space}}}')
    else:
        print(f'{space}{obj}')


def find_start_end(string, substring):
    start = string.find(substring)
    end = start + len(substring)

    return start, end


def read_json(path=''):
    path = path if path else 'har.json'

    with open(path, encoding='utf-8') as json_file:
        data = json.load(json_file)

    return data


def write_json(data, path=''):
    path = path if path else 'har_out.json'

    with open(path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file)


def write(data, path=''):
    path = path if path else 'requests_code.py'

    with open(path, 'w', encoding='utf-8') as file:
        file.write(data)


def format_filters(filters_str):
    filters = filters_str.split()
    allowed_filters = []
    disallowed_filters = []
    for filter_ in filters:
        if filter_.startswith('-'):
            disallowed_filters.append(filter_[1:])
        else:
            allowed_filters.append(filter_)

    formatted_filters = {
        'allowed': allowed_filters,
        'disallowed': disallowed_filters
    }
    intersections = list(set(formatted_filters['allowed']).intersection(set(formatted_filters['disallowed'])))
    if intersections:
        print('[WARNING (intersections in filters)] -', intersections)

    return formatted_filters


def filter_value(val, filters):
    if filters['allowed']:
        return check_value(val, filters['allowed'], type_='allow')
    return check_value(val, filters['disallowed'], type_='disallow')


def check_value(val, filters, type_='allow'):
    return_val = True if type_ == 'allow' else False

    for filter_ in filters:
        if filter_.lower() in val.lower():
            return return_val

    return not return_val


def format_headers(headers):
    headers_f = {}
    for header in headers:
        name, value = header['name'], header['value']
        if name.lower() in [':authority', ':method', ':path', ':scheme', 'cookie']:
            continue
        if name.lower() == 'user-agent':
            value = '[no_quote]self.user_agent[no_quote]'

        if not isinstance(value, str):
            value = f'[no_quote]{value}[no_quote]'

        headers_f[name] = value

    return headers_f


def format_query_string(query_string):
    return {qs['name']: qs['value'] for qs in query_string}


def format_cookies(cookies):
    if cookies:
        return {cookie['name']: cookie['value'] for cookie in cookies}
    else:
        return {}


def format_params(params):
    params_f = {}
    for param in params:
        name, value = param['name'], param['value']

        if not isinstance(value, str):
            value = f'[no_quote]{value}[no_quote]'

        params_f[name] = value

    return params_f


def decode_response(text, encoding):
    if text:
        if encoding:
            return codecs.decode(text.encode('UTF-8'), 'unicode-escape')
        else:
            return text
    else:
        return text


def dict_to_code(some_dict, dict_name):
    key_value_list = [f"   '{key}': '{value}'," for key, value in some_dict]
    key_value_text = '\n'.join(key_value_list).replace("[no_quote]'", '').replace("'[no_quote]", '')
    dict_code = f'{dict_name} = {{\n{key_value_text}\n}}\n'

    return dict_code


def params_sources_to_code(params, params_info):
    indent = ' ' * 4
    param_sources_output = '\n'
    for name, value in params.items():
        for param_info in params_info:
            if name == param_info['name'] and value == param_info['value']:
                param_sources_output += f'# {name}: {value}\n'
                param_sources_output += f'# sources: [\n'
                for source in param_info['sources']:
                    param_sources_output += f'# {indent}url: [{source["request_method"]}] {source["request_url"]}\n'
                    param_sources_output += f'# {indent}place: {source["place"]}\n'
                    param_sources_output += f'# {indent}repr: {source["repr"]}\n'
                    param_sources_output += f'# {indent}\n'
                param_sources_output += f'# ]\n'

                break
    param_sources_output += '\n'

    return param_sources_output


def request_to_code(request, params_info):
    url = f"url = '{request['url']}'\n"

    headers = dict_to_code(request["headers_f"].items(), 'headers')

    params = []
    if 'params' in request:
        params = dict_to_code(request["params"].items(), 'data')
        params_sources = params_sources_to_code(request["params"], params_info)
        params += params_sources

    make_request_params = ', data=data' if params else ''
    make_request = f'r = self.session.{request["method"].lower()}(url, headers=headers{make_request_params})\n'

    output = url + headers + params + make_request if params else url + headers + make_request

    return output


