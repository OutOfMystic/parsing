import os
import time
import random
import weakref
from abc import abstractmethod

import requests
import threading
import statistics

from . import user_agent
from ..utils import utils, parse_utils, provision
from ..drivers.hrenium import HrenDriver
from ..drivers.proxelenium import ProxyWebDriver
from ..utils.logger import logger


class BotCore(threading.Thread):

    def __init__(self, proxy=None):
        super().__init__()
        self.delay = 30
        self.name = 'unnamed'
        self.proxy = proxy
        self.driver_source = None
        self.step_counter = 1
        self.max_waste_time = 600
        self.max_tries = 3
        self.url = ''

        self.user_agent = user_agent.random()
        self.error_timer = float('inf')
        self.step = 0
        self.driver = None
        self._terminator = weakref.finalize(self, self._finalize)

    def __str__(self):
        proxy_str = f'with proxy {self.proxy}' if self.proxy else 'without proxy'
        return f'Bot "{self.name}" {proxy_str}'

    def bprint(self, mes, color=utils.Fore.LIGHTGREEN_EX):
        """DEPRECATED. USE self.info, self.warning, etc."""
        logger.bprint_compatible(mes, self.name, color)

    def screen(self, text, addition=''):
        now = time.asctime()
        if addition:
            addition = '_' + addition
        self.name = self.name.replace(':', '') \
                             .replace(',', '') \
                             .replace(' ', '_')
        filename = os.path.join('screen', self.name, f'{now}{addition}.html')
        filename = filename.replace(':', '') \
                           .replace(',', '') \
                           .replace(' ', '_')
        pre_path = os.path.join('screen', self.name)
        if not os.path.exists(pre_path):
            os.mkdir(pre_path)
        with open(filename, 'w+', encoding='utf-8') as f:
            f.write(text)

    def slide_tab(self):
        self.bprint('Max waste time elapsed, but nothing '
                    'has been changed. Configure slide_tab method', color=utils.Fore.YELLOW)

    def except_on_main(self):
        if self.driver:
            self.driver.get('http://httpbin.org/ip')
            self.driver.get(self.url)

    def except_on_wait(self):
        self.driver.get(self.driver.current_url)

    def on_many_exceptions(self):
        pass

    def hrenium(self):
        return HrenDriver(proxy=self.proxy)

    def selenium(self):
        return ProxyWebDriver(proxy=self.proxy)

    def before_body(self):
        pass

    @abstractmethod
    def body(self, *args, **kwargs):
        pass

    def run_try(self):
        if not self._terminator.alive:
            return False
        if self.driver and self.url:
            self.driver.get(self.url)
        self.body()
        # logger.debug(f'Step ({self.name}) done')
        if not self._terminator.alive:
            return False

    def run_except(self):
        try:
            time_string = f'{time.time() - self.error_timer} sec'
            print(utils.colorize(time_string, utils.Fore.YELLOW))
            if (time.time() - self.error_timer) >= self.max_waste_time:
                mes = ('--max_waste_time elapsed '
                       f'({self.max_waste_time} сек)--')
                self.error(mes)
                self.error_timer = time.time()
                self.slide_tab()
            self.except_on_main()
        except Exception as error:
            printing_error = str(error).split('\n')[0] if '\n' in str(error) else str(error)
            self.error('Except on exception: ' + str(error))
        time.sleep(1)

    def run(self):
        self.step = 0
        if self.driver_source:
            self.driver = self.driver_source()
        self.before_body()
        while True:
            if not self._terminator.alive:
                self._process_termination()
                break
            if self.step % self.step_counter == 0:
                self.bprint('Проход номер ' + str(self.step))
            result = provision.multi_try(self.run_try, to_except=self.run_except,
                                         name=self.name, tries=self.max_tries, raise_exc=False)
            self.step += 1
            if result == provision.TryError and self._terminator.alive:
                self.on_many_exceptions()
            delay = get_delay(self.delay)
            time.sleep(delay)

    def _process_termination(self):
        if self.driver:
            self.driver.quit()
        self.bprint(f'Thread {self.name} has been {terminated}')

    def stop(self):
        return self._terminator()

    def _finalize(self):
        self.bprint(f'Thread {self.name} '
                    f'{utils.red("termination")} '
                    f'{utils.green("started")}')

    @staticmethod
    def error(message):
        logger.error(message, name='Controller')


def download(url, filename=None, session=None, save=True, **kwargs):
    get_func = session.get if session else requests.get
    r = get_func(url, **kwargs)
    if not filename:
        if 'content-disposition' in r.headers:
            disposition = r.headers['content-disposition']
            filename = parse_utils.double_split(disposition, 'filename="', '"')
        else:
            filename = url.split('/')[-1]

    name_parts = filename.split('.')
    if len(name_parts) > 1:
        format_ = '.' + name_parts.pop()
        filename = '.'.join(name_parts)
    else:
        filename = name_parts.pop()
        format_ = ''

    addition = ''
    filepath = os.path.join('downloads', f'{addition}{filename}{format_}')
    while os.path.exists(filepath):
        addition += '#'
    if save:
        with open(filepath, 'wb+') as f:
            f.write(r.content)
    else:
        return r.content


def get_delay(delay, l_range=0.723, r_range=1.26):
    hour_activity = [hour / hours_mean for hour in activity_on_h]
    hour = time.strftime('%H')
    hour = int(hour)
    delay /= hour_activity[hour]

    spread_x = random.random() * (r_range - l_range) + l_range
    spread_y = spread_x ** 4
    delay *= spread_y
    return delay


activity_on_h = (8, 4, 2, 1.5, 0.8, 0.8, 1.0, 2, 4, 8, 8, 10, 13, 15, 15, 15, 17, 19, 19, 18, 13, 11, 9, 8)
hours_mean = statistics.mean(activity_on_h)
terminated = utils.red("terminated")
