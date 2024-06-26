import socket
import json
import os
import subprocess
import time

from parse_module.drivers.chrome_selenium_driver import ChromeProxyWebDriver

from parse_module.utils import utils

class ChromeDriverPuppeteer(ChromeProxyWebDriver):
    '''
        selenium работатет в связке с puppeteer node js

    Для перехвата response ответов на xhr/ajax запросов
        js_script_name: str -> для скриптов puppeteer
        search_phrases: list -> искомые строки в url,если пуст вернет все responses url
        debug: bool -> отладочная печать в консоль
        file_to_write_path: bool|str -> путь для файла куда запишутся перехваченные puppeteer
        time_sleep: int -> время сна после загрузки Chrome
        проверь установлены ли
                                node -v
                                npm -v
                                yarn -v

    в папке parse_module/drivers/selenium_with_puppeteer:
                                yarn init
    '''
    def __init__(self, js_script_name='intercept.js',
                 search_phrases=None,
                 debug_puppeteer=False,
                 file_to_write_path=None,
                 time_sleep=5, **kwargs):
        self.js_script_name = js_script_name
        self.search_phrases = search_phrases if search_phrases else []
        self.debug = debug_puppeteer
        self.file_to_write_path = file_to_write_path
        self.port = self.get_free_port()#на этом порту запустится chrome к нему подключится процесс puppeteer
        self.puppeteer_process = None
        self.time_sleep = time_sleep
        self.responses = None
        super().__init__(chrome_options_list=('--disable-dev-shm-usage', f'--remote-debugging-port={self.port}'), **kwargs)

    @staticmethod
    def get_free_port():
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('', 0))
            port = s.getsockname()[1]
            s.close()
            # Проверяем, что порт не занят
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port

    def check_chrome_processes(self):
        os.system("ps aux | grep '[c]hrome'")

    def wait_for_port(self, port, timeout=30):
        start_time = time.time()
        if self.debug:
            print(self.port)
            self.check_chrome_processes()
        while time.time() - start_time < timeout:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) == 0:
                    return True
            time.sleep(0.5)
        return False
    def get(self, url):
        try:
            super().get('about:blank')
            time.sleep(self.time_sleep)
            if not self.wait_for_port(self.port):
                raise RuntimeError(f"Port {self.port} did not become available in time")
            stdout, stderr = self.run_puppeteer(url)
            if stderr:
                print(utils.colorize(f"STDERR:!!!!{stderr}", color=utils.Fore.RED))
            try:
                self.responses = json.loads(stdout)
                if self.file_to_write_path:
                    print(utils.colorize(f"Captured responses saved to {self.file_to_write_path}",
                                         color=utils.Fore.GREEN))
                    with open(self.file_to_write_path, 'w') as f:
                        json.dump(self.responses, f, indent=2)
            except json.JSONDecodeError as e:
                print(utils.colorize(f"Error decoding JSON: {e}", color=utils.Fore.RED))
                print(utils.colorize(f"Raw output: {stdout}", color=utils.Fore.RED))
        finally:
            self.quit()
            if self.puppeteer_process:
                self.puppeteer_process.terminate()

    def run_puppeteer(self, target_url):
        # Запуск Node.js скрипта и передача URL и искомых фраз
        node_script_path = os.path.join(os.path.dirname(__file__), self.js_script_name)
        if not os.path.exists(node_script_path):
            print(utils.colorize(f"Node.js script not found at {node_script_path}",
                                 color=utils.Fore.RED))
        else:
            print(utils.colorize(f"Running Node.js script at {node_script_path} with URL {target_url}",
                                 color=utils.Fore.GREEN))
        self.puppeteer_process = subprocess.Popen(
            ["node", node_script_path, target_url,
             json.dumps(self.search_phrases), str(self.port),
             str(self.debug).lower()],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True
        )
        stdout, stderr = self.puppeteer_process.communicate()
        return stdout, stderr

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()
        if self.puppeteer_process:
            self.puppeteer_process.terminate()

if __name__ == '__main__':
    import threading
    def browse_with_puppeteer(url, search_phrases, file_to_write_path):
        with ChromeDriverPuppeteer(search_phrases=search_phrases, debug=True,
                                   file_to_write_path=file_to_write_path) as driver:
            driver.get(url)
            time.sleep(10)
            print(driver.responses)# здесь дожны быть ответы. пример смотри в responses_example.json
    urls = [
        'https://afisha.yandex.ru/almaty/',
        'https://afisha.yandex.ru/almaty/',
        'https://afisha.yandex.ru/almaty/'
    ]
    # Создание и запуск потоков
    threads = []
    for i, url in enumerate(urls):
        thread = threading.Thread(target=browse_with_puppeteer, args=(url,
                                                                      ['yandex', 'almaty'],
                                                                      f'responses_{i}.json'))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

