import json
import os
import sys
import time
from parse_module.utils import utils
import zipfile
from pathlib import Path
from importlib.resources import files
from selenium.common.exceptions import SessionNotCreatedException
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


from .hrenium import default_user_agent
from ..utils import parse_utils
from . import extension


class ProxyWebDriver(webdriver.Chrome):
    def __init__(self, options=None, **kwargs):
        script_directory = os.path.dirname(os.path.abspath(__file__))
        main_directory = os.path.dirname(script_directory)
        # Создаем относительный путь к chromedriver.exe
        chromedriver_path = os.path.join(main_directory, 'working_directory', 'chromedriver.exe')
        # Unpacking initial keyword arguments
        self.proxy = kwargs.get('proxy', None)
        self.tab = kwargs.get('tab', 0)
        self.user_agent = kwargs.get('user_agent', default_user_agent)
        self.listen_requests = kwargs.get('listen_requests', False)
        self.listen_responses = kwargs.get('listen_responses', False)
        self.listen_request_headers = kwargs.get('listen_request_headers', False)
        self.headers_to_add = kwargs.get('headers_to_add', {})
        self.blocked_hosts = kwargs.get('blocked_hosts', default_blocked_hosts)
        big_theatre_id = kwargs.get('id_profile', None)
        self.service = Service(executable_path=chromedriver_path)
        # Formatting scripts for an extension
        background_js = ''
        if self.proxy is not None:
            background_js += _bg_proxy % (
                self.proxy.schema,
                self.proxy.ip,
                self.proxy.port,
                self.proxy.login,
                self.proxy.password
            )
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
        if options is None:
            chrome_options = webdriver.ChromeOptions()
        elif options:
            chrome_options = options
        chrome_options.add_argument(f'--user-agent={self.user_agent}')
        chrome_options.binary_location = chromedriver_path
        if self.blocked_hosts:
            stringed_rules = [f'MAP {host} 127.0.0.1' for host in self.blocked_hosts]
            to_args = ', '.join(stringed_rules)
            chrome_options.add_argument(f'--host-rules={to_args}')

        # Packing an extension
        if background_js and False:
            if big_theatre_id:
                base_dir = Path(__file__).resolve().parent.joinpath('data_to_big_theatre')
                ext_file = base_dir.joinpath(f'ext_{self.proxy.schema}{big_theatre_id}.zip')
            else:
                ext_file = f'ext_{self.proxy.schema}.zip'
            with zipfile.ZipFile(ext_file, 'w') as zp:
                zp.writestr('manifest.json', manifest_json)
                zp.writestr('background.js', background_js)
                if self.listen_responses:
                    zp.writestr('jquery.js', _jquery)
                    zp.writestr('content.js', _content)
                    zp.writestr('listen_response.js', _listen_response)
                chrome_options.add_extension(ext_file)

        if alternative_win_bin is not None:
            chrome_options.binary_location = alternative_win_bin

        if big_theatre_id:
            error = None
            count_error = 0
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
            caps = DesiredCapabilities.CHROME
            caps['goog:loggingPrefs'] = {'performance': 'ALL'}
            chrome_options.add_argument('--enable-logging')
            chrome_options.add_argument('--v=1')
            while error is not False:
                try:
                    super().__init__(service=self.service,options=chrome_options)
                    if error is True and count_error >= 10:
                        mes = f'error SessionNotCreatedException: id_profile №{kwargs.get("id_profile")} is complite'
                        print(f'{utils.colorize(mes, utils.Fore.GREEN)}\n', end='')
                    error = False
                except SessionNotCreatedException:
                    error = True
                    if count_error >= 10:
                        mes = f'error SessionNotCreatedException: id_profile №{kwargs.get("id_profile")}'
                        print(f'{utils.colorize(mes, utils.Fore.RED)}\n', end='')
                    count_error += 1
                    time.sleep(3)
        else:
            super().__init__(service=self.service, options=chrome_options)

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


def extension_content(filename):
    return files(extension).joinpath(filename).read_text()


_manifest = extension_content('manifest.json')
_manifest_listen = extension_content('manifest_listen.json')
_bg_headers = extension_content('bg_headers.js')
_bg_listen_requests = extension_content('bg_listen_requests.js')
_bg_listen_headers = extension_content('bg_listen_headers.js')
_bg_proxy = extension_content('bg_proxy.js')
_content = extension_content('content.js')
_listen_response = extension_content('listen_response.js')
_jquery = extension_content('jquery.js')

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