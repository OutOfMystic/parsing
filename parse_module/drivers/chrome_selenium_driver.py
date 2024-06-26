import json
import time
import os
import zipfile
from importlib.resources import files

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.proxy import Proxy, ProxyType

from parse_module.utils import utils, parse_utils
from parse_module.drivers import extension

class ResponseReceivedeReadError(Exception):
    pass
class ChromeProxyWebDriver(webdriver.Chrome):
    '''
    chromedriver_path: bool|str -> если False -> грузим  chromedriver автоматически
                                   если True -> берем из папки parse_module/drivers/chromedrivers
                                   если str -> делаем поптыку загрузить этот chromedriver
    chrome_options_list: tuple(str,) -> передаем необходмые значения для chrome_options
    extention_background: bool -> Создания расширения для браузера в виде js скрипта
    headless: bool -> безголовый режим
    capability: bool -> режим DevTools Chrome, в котором возможно логирование входящих/исходщих requests
    proxy_controller: bool|UniProxy -> можно передать прокси выбранные controller
                                       у классов наследуемых от EventsParser и SeatsParser
                                       передавай вот так -> self.proxy
    proxy_custom: bool|dict ->  dict(schema='str', login='str', password='str', ip='str|int', port='str|int')
    user_agent: None|str -> просто User-Agent

    METHODS
        get_capabilites_logs -> вернет list(dict,) логи бразерных запросов/ответов
        find_data_in_responseReceived -> поиск url responses и их headers/body
    '''
    def __init__(self, chromedriver_path=False,
                 chrome_options_list: tuple = (),
                 extension_background=False,
                 headless=False,
                 capability=False,
                 proxy_controller=False,
                 proxy_custom=False,
                 user_agent=None,
                 **kwargs):

        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument("--no-sandbox")
        self._load_custom_chrome_options(chrome_options_list)
        self.proxy_ = proxy_controller or proxy_custom

        if chromedriver_path:
            chromedriver_path = self.choose_chromedriver(chromedriver_path)
            self.service = Service(executable_path=chromedriver_path)
        else:
            self.service = Service(ChromeDriverManager().install())

        if extension_background:
            self.make_background_extension(**kwargs)
        if headless:
            self._headless_mode_on()
        if capability:
            self.chrome_options.add_argument('--enable-logging')
            self.chrome_options.add_argument('--v=1')
            self.chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        if proxy_controller or proxy_custom:
            proxy = self.choose_proxy(proxy_controller, proxy_custom)
            if proxy:
                self.chrome_options.proxy = proxy
        if user_agent:
            self.chrome_options.add_argument(f'--user-agent={user_agent}')

        super().__init__(service=self.service, options=self.chrome_options)
        if capability:
            self.execute_cdp_cmd('Network.enable', {})
            self.execute_cdp_cmd('Network.setCacheDisabled', {"cacheDisabled": True})

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()
    @staticmethod
    def choose_proxy(proxy_controller, proxy_custom):
        prxy = None
        if proxy_controller:
            prxy = proxy_controller
        elif proxy_custom:
            prxy = proxy_custom
        if prxy:
            proxy_ = f'{prxy.login}:{prxy.password}@{prxy.ip}:{prxy.port}'
            proxy = Proxy({
                'proxyType': ProxyType.MANUAL,
                'httpProxy': proxy_,
                'ftpProxy': proxy_,
                'sslProxy': proxy_,
                'noProxy': ''  # set this value as desired
            })
            return proxy
    @staticmethod
    def choose_chromedriver(chromedriver_path):
        if isinstance(chromedriver_path, str) and check_path:
            return chromedriver_path
        chromedriver_path = get_path_chromedriver()
        return chromedriver_path

    def _headless_mode_on(self):
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument("--disable-gpu")  # Если используется Windows, это может быть необходимо
        self.chrome_options.add_argument("--window-size=1920,1080")
        #self.chrome_options.add_argument('--disable-dev-shm-usage')
    def _load_custom_chrome_options(self, chrome_options:tuple):
        for option in chrome_options:
            try:
                self.chrome_options.add_argument(option)
            except Exception as ex:
                print(option, ex)
    def make_background_extension(self, **kwargs):
        '''
        Создания расширения для браузера в виде js скрипта
        '''
        tab = kwargs.get('tab', 0)
        self.listen_requests = kwargs.get('listen_requests', False)
        self.listen_responses = kwargs.get('listen_responses', False)
        self.listen_request_headers = kwargs.get('listen_request_headers', False)
        headers_to_add = kwargs.get('headers_to_add', {})
        blocked_hosts = kwargs.get('blocked_hosts', default_blocked_hosts)
        background_js = ''
        if self.proxy_:
            background_js += extension_content(_bg_proxy) % (
                self.proxy_.schema,
                self.proxy_.ip,
                self.proxy_.port,
                self.proxy_.login,
                self.proxy_.password
            )
        if self.listen_responses:
            background_js += extension_content(_bg_listen_requests)
        if self.listen_request_headers:
            background_js += extension_content(_bg_listen_headers)
        if headers_to_add:
            headers = [{'name': key, 'value': value} for key, value
                       in headers_to_add.items()]
            background_js += _bg_headers % json.dumps(headers)
        manifest_json = extension_content(_manifest_listen)

        if blocked_hosts:
            stringed_rules = [f'MAP {host} 127.0.0.1' for host in blocked_hosts]
            to_args = ', '.join(stringed_rules)
            self.chrome_options.add_argument(f'--host-rules={to_args}')
        self._pack_extension(manifest_json, background_js)

    def _pack_extension(self, manifest_json, background_js):
        '''
        Запаковываем расширение и добавляем
        '''
        ext_file = f'extension/ext_{self.proxy_.schema}.zip'
        with zipfile.ZipFile(ext_file, 'w') as zp:
            zp.writestr('manifest.json', manifest_json)
            zp.writestr('background.js', background_js)
            if self.listen_responses:
                zp.writestr('jquery.js', extension_content(_jquery))
                zp.writestr('content.js', extension_content(_content))
                zp.writestr('listen_response.js', extension_content(_listen_response))
            self.chrome_options.add_extension(ext_file)

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
    def get_capabilites_logs(self) -> list[dict]:
        # Сбор логов производительности
        logs = self.get_log("performance")
        parsed_logs = [self._make_json(log) for log in logs]
        return parsed_logs
    def _make_json(self, obj) -> dict:
        if isinstance(obj, str):
            try:
                return json.loads(obj)
            except ValueError:
                return obj
        elif isinstance(obj, dict):
            return {key: self._make_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json(element) for element in obj]
        else:
            return obj

    def find_data_in_responseReceived(self, chrome_logs=None, find_patterns=(),
                                      print_all_urls=False):
        '''
            chrome_logs: -> performance логи браузера, если нет берем логи текущего экземряра
            find_patterns: (str,) -> искомые паттерны в url
            print_all_urls: -> отладочная печать
        '''
        if not chrome_logs:
            chrome_logs = self.get_capabilites_logs()
        for log in chrome_logs:
            message = log["message"]
            message = message["message"]
            if message["method"] == "Network.responseReceived":
                try:
                    request_id = message["params"]["requestId"]
                    url = message["params"]["response"]["url"]
                    if print_all_urls:
                        print(utils.colorize(f"URl:{url},\nID{request_id}\n", color=utils.Fore.GREEN))
                    if all(pattern in url for pattern in find_patterns):
                        message = f"FIND PATTERN\nURl:{url},\n ID{request_id}"
                        print(utils.colorize(message, color=utils.Fore.GREEN))

                        response = self._wait_for_response(request_id)
                        body = response.get('body')
                        body_dict = json.loads(body)
                        return body_dict
                except Exception:
                    raise ResponseReceivedeReadError(f'cannot read responseReceived body')

    def _wait_for_response(self, request_id, timeout=20, poll_frequency=2):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                if response.get('body'):
                    return response
            except Exception:
                time.sleep(poll_frequency)
        raise TimeoutError(f"Timeout waiting for response body for request {request_id}")

def get_path_chromedriver():
    # Создаем относительный путь к chromedriver.exe
    script_directory = os.path.dirname(os.path.abspath(__file__))
    main_directory = os.path.join(script_directory, 'chromedrivers')
    platform = os.name
    if platform == "posix":  # Для Linux/Unix
        chromedriver_path = os.path.join(main_directory, 'chromedriver')
    elif platform == "nt":  # Для Windows
        chromedriver_path = os.path.join(main_directory, 'chromedriver.exe')
    else:
        chromedriver_path = None
    return chromedriver_path

def extension_content(filename):
    return files(extension).joinpath(filename).read_text()

def check_path(path):
    if os.path.isfile(path):
        print(utils.colorize(f"path is valid: {path}", color=utils.Fore.GREEN))
        return True
    else:
        print(utils.colorize(f"path is not valid: {path}", color=utils.Fore.RED))
        return False

_manifest = 'manifest.json'
_manifest_listen = 'manifest_listen.json'
_bg_headers = 'bg_headers.js'
_bg_listen_requests = 'bg_listen_requests.js'
_bg_listen_headers = 'bg_listen_headers.js'
_bg_proxy = 'bg_proxy.js'
_content = 'content.js'
_listen_response = 'listen_response.js'
_jquery = 'jquery.js'

default_blocked_hosts = [
    '*.facebook.net',
    '*.facebook.com',
    '*.google-analytics.com',
    'mc.yandex.ru',
    'vk.com'
]

if __name__ == '__main__':
    with ChromeProxyWebDriver(capability=True) as driver:
        driver.get('https://ticket.bolshoi.ru')
        time.sleep(7)
        json_seats = driver.find_data_in_responseReceived(print_all_urls=False,
                                                          find_patterns=(
                                                          'https://ticket.bolshoi.ru/api/v1/client/shows',
                                                          'tariffs'))
        print(json_seats)