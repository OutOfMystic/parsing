from har_utils import *


class HarReader:
    url_filters = '-.js -.svg -css -woff -gif -ttf -.cur -mc.yandex.ru -maps.yandex -bitrix -.ico -.png -.jpeg -.jpg ' \
                  '-/tracking -cdn.retailrocket.ru -api.retailrocket.ru -gum.criteo.com -google -analytics -vk.com ' \
                  '-youtube -googleads -googleapis -googletagmanager -mc.webvisor -unisender -amplitude -hotjar ' \
                  '-gstatic -stats.g -.mail.ru -flocktory -wf.frontend.weborama -tag.rutarget -google.com/recaptcha '

    resource_filters = '-script -image -font -stylesheet -ping'

    def __init__(self, path=''):
        self.url_filters = format_filters(self.url_filters)
        self.resource_filters = format_filters(self.resource_filters)
        self.har_data = read_json(path)['log']
        self.browser = self.har_data['creator']['name']
        self.params_info = []
        self.raw_requests = self.har_data['entries']
        self.har_data_filtered = self.filter_har_data()
        self.prepare_requests()
        self.raw_requests_filtered = self.har_data_filtered['entries']
        self.pages = self.get_pages()
        self.requests = self.get_requests()

    def __str__(self):
        return f'{self.pages["urls_ids"]}'

    def prepare_requests(self):
        for req in self.raw_requests:
            req['id'] = f"{req['request']['url']} - {str(req['time'])[:6]}"
            req['request']['cookies'] = format_cookies(req['request']['cookies'])
            req['response']['cookies'] = format_cookies(req['response']['cookies'])

    def filter_har_data(self):
        filtered_entries = []
        if self.browser in ['WebInspector']:
            for req in self.raw_requests:
                if filter_value(req['_resourceType'], self.resource_filters)\
                        and filter_value(req['request']['url'], self.url_filters):
                    filtered_entries.append(req)
        else:
            for req in self.raw_requests:
                if filter_value(req['request']['url'], self.url_filters):
                    filtered_entries.append(req)

        filtered_har_data = self.har_data.copy()
        filtered_har_data['entries'] = filtered_entries

        return filtered_har_data

    def get_pages(self):
        pages_list = self.har_data['pages']
        pages_ids_urls = {page['id']: page['title'] for page in pages_list}
        pages = {
            'full_list': pages_list,
            'urls_ids': pages_ids_urls
        }

        return pages

    def get_requests(self):
        requests = []
        for i, req in enumerate(self.raw_requests_filtered):
            e_req = req['request']
            request = {
                'url': e_req['url'],
                'method': e_req['method'],
                'headers': e_req['headers'],
                'headers_f': format_headers(e_req['headers']),
                'queryString': format_query_string(e_req['queryString']),
                'cookies': e_req['cookies']
            }

            try:
                e_req_params = req['request']['postData']['params']
                params = {
                    'params': format_params(e_req_params)
                }

                for key, value in params['params'].items():
                    sources = self.find_param_source(value, req['id'])
                    param = {
                        'name': key,
                        'value': value,
                        'origin_request': req['id'],
                        'sources': sources
                    }
                    self.params_info.append(param)

                request.update(params)
            except KeyError:
                pass

            e_req_resp = req['request'].get('response', None)
            if e_req_resp:
                resp_info = {
                    'response': decode_response(e_req_resp['content'].get('text', ''),
                                                e_req_resp['content'].get('encoding', '')),
                    'response_headers': e_req_resp['headers'],
                    'response_headers_f': format_headers(e_req_resp['headers']),
                    'response_cookies': e_req_resp['cookies'],
                }

                request.update(resp_info)

            requests.append(request)

        return requests

    def export_requests(self):
        export_list = []
        for request in self.requests:
            export_list.append(request_to_code(request, self.params_info))

        to_export = '\n\n'.join(export_list)

        return to_export

    def find_param_source(self, param_value, req_id):
        indent = 30

        sources = []
        for req in self.raw_requests_filtered:
            if req['id'] == req_id:
                break

            if param_value in req['request']['url']:
                source = {
                    'request_id': req['id'],
                    'request_url': req['request']['url'],
                    'request_method': req['request']['method'],
                    'place': 'url',
                    'repr': ''
                }
                sources.append(source)

            for cookie_name, cookie_value in req['request']['cookies'].items():
                if param_value in cookie_value or param_value == cookie_value:
                    source = {
                        'request_id': req['id'],
                        'request_url': req['request']['url'],
                        'request_method': req['request']['method'],
                        'place': 'request_cookies',
                        'repr': f'{cookie_name}: {cookie_value}'
                    }
                    sources.append(source)
                    break

            for cookie_name, cookie_value in req['response']['cookies'].items():
                if param_value in cookie_value or param_value == cookie_value:
                    source = {
                        'request_id': req['id'],
                        'request_url': req['request']['url'],
                        'request_method': req['request']['method'],
                        'place': 'response_cookies',
                        'repr': f'{cookie_name}: {cookie_value}'
                    }
                    sources.append(source)
                    break

            try:
                r_text = req['response']['content']['text']
                if param_value in r_text:
                    start, end = find_start_end(r_text, param_value)
                    repr_ = r_text[start - indent:end + indent].replace('\n', '')
                    source = {
                        'request_id': req['id'],
                        'request_url': req['request']['url'],
                        'request_method': req['request']['method'],
                        'place': 'r_text',
                        'repr': repr_
                    }
                    sources.append(source)
            except KeyError:
                pass

        return sources


if __name__ == '__main__':
    har_reader = HarReader()

    export = har_reader.export_requests()
    write(export)
    for request in har_reader.requests:
        print(request)




