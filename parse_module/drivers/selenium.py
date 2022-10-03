import json
import os
import sys
import zipfile
from importlib.resources import files

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .hrenium import default_user_agent
from ..utils import parse_utils
from . import extension


class ProxyWebDriver(webdriver.Chrome):
    def __init__(self, **kwargs):
        # Unpacking initial keyword arguments
        self.proxy = kwargs.get('proxy', None)
        self.tab = kwargs.get('tab', 0)
        self.user_agent = kwargs.get('user_agent', default_user_agent)
        self.listen_requests = kwargs.get('listen_requests', False)
        self.listen_responses = kwargs.get('listen_responses', False)
        self.listen_request_headers = kwargs.get('listen_request_headers', False)
        self.headers_to_add = kwargs.get('headers_to_add', {})
        self.blocked_hosts = kwargs.get('blocked_hosts', default_blocked_hosts)

        # Formatting scripts for an extension
        background_js = ''
        if self.proxy is not None:
            background_js += _bg_proxy % self.proxy.args
        if self.listen_responses:
            background_js += _bg_listen_requests
        if self.listen_request_headers:
            background_js += _bg_listen_headers
        if self.headers_to_add:
            headers = [{'name': key, 'value': value} for key, value
                       in self.headers_to_add.items()]
            background_js += _bg_headers % json.dumps(headers)
        manifest_json = _manifest_listen if self.listen_responses else _manifest

        # Defining chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f'--user-agent={self.user_agent}')
        if self.blocked_hosts:
            stringed_rules = [f'MAP {host} 127.0.0.1' for host in self.blocked_hosts]
            to_args = ', '.join(stringed_rules)
            chrome_options.add_argument(f'--host-rules={to_args}')

        # Packing an extension
        if background_js:
            ext_file = f'ext_{self.proxy.host}.zip'
            with zipfile.ZipFile(ext_file, 'w') as zp:
                zp.writestr('manifest.json', manifest_json)
                zp.writestr('bg_proxy.js', background_js)
                if self.listen_responses:
                    zp.writestr('jquery.js', _jquery)
                    zp.writestr('content.js', _content)
                    zp.writestr('listen_response.js', _listen_response)
                chrome_options.add_extension(ext_file)

        if alternative_win_bin is not None:
            chrome_options.binary_location = alternative_win_bin
        super().__init__(chrome_options=chrome_options)

    def expl_wait(self, by_what, value, condition='presence', wait_time=15):
        """
        Simplified construction that implements explicit
        expectation of a DOM object.
        ``condition`` can be of three formats:
        'presence', 'visibility', 'clickable'
        """
        conditions = {
            'visibility': EC.visibility_of_element_located,
            'presence': EC.presence_of_element_located,
            'clickable': EC.element_to_be_clickable
        }
        assert condition in conditions, f'Condition can not be {condition}'
        wait_function = conditions[condition]
        valued_condition = wait_function((by_what, value))
        WebDriverWait(self, wait_time).until(valued_condition)

    def find_element_by_class_names(self, value):
        xpath = parse_utils.class_names_to_xpath(value)
        return self.find_element('xpath', xpath)

    def find_elements_by_class_names(self, value):
        xpath = parse_utils.class_names_to_xpath(value)
        return self.find_elements('xpath', xpath)


def extension_path(filename):
    return files(extension).joinpath(filename).read_text()


_manifest = extension_path('manifest.json')
_manifest_listen = extension_path('manifest_listen.json')
_bg_headers = extension_path('bg_headers.js')
_bg_listen_requests = extension_path('bg_listen_requests.js')
_bg_listen_headers = extension_path('bg_listen_headers.js')
_bg_proxy = extension_path('bg_proxy.js')
_content = extension_path('content.js')
_listen_response = extension_path('listen_response.js')
_jquery = extension_path('jquery.js')

if os.path.exists("C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"):
    alternative_win_bin = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
elif os.path.exists("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"):
    alternative_win_bin = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
else:
    alternative_win_bin = None

default_blocked_hosts = [
    '*.facebook.net',
    '*.facebook.com',
    '*.google-analytics.com',
    'mc.yandex.ru',
    'vk.com'
]
