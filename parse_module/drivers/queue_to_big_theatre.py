import time
import itertools
from pathlib import Path
from parse_module.drivers.selemiun_tickets_bolshoi import WebdriverChrome
from selenium.common.exceptions import TimeoutException
import shutil
from parse_module.utils import utils
from queue import Queue
from parse_module.utils.provision import threading_try


OPEN_BROWSER = 3
queue_big_theatre = Queue(maxsize=3)
result_json = {}

BASE_DIR = Path(__file__).resolve().parent.joinpath('data_to_big_theatre')

list_account = []
file_accounts = BASE_DIR.joinpath('accounts')
with open(file_accounts, 'r') as f:
    for line in f.readlines():
        list_account.append(eval(str(line)))

for id_profile in range(1, OPEN_BROWSER+1):
    dir_with_profile = BASE_DIR.joinpath(f'profile{id_profile}')
    try:
        shutil.rmtree(dir_with_profile)
    except OSError:
        pass

generate_accounts = itertools.cycle(list_account)
generate_id_session = itertools.cycle(range(1, OPEN_BROWSER+1))


def get_json_from_selenium():
    proxy_to_this_session = None
    account = next(generate_accounts)
    id_profile = next(generate_id_session)
    new_webdriver_chrome = None

    while True:
        task = queue_big_theatre.get()
        proxy, url = task

        count_error = 1
        ready_json = None
        while ready_json is None:
            if proxy_to_this_session is None:
                proxy_to_this_session = proxy
            else:
                proxy = proxy_to_this_session

            try:
                if new_webdriver_chrome is None:
                    new_webdriver_chrome = WebdriverChrome(proxy=proxy, account=account, id_profile=id_profile)

                url_to_parse = f'https://ticket.bolshoi.ru/api/v1/client/shows/{url.split("/")[-1]}/tariffs/17/seats'
                ready_json = new_webdriver_chrome.parse_seats(url_to_parse=url_to_parse)
            except TimeoutException as error:
                if count_error >= 5:
                    new_webdriver_chrome.quit()
                    new_webdriver_chrome = None
                    mes = (f'Big_theatre have {error = } with data: {id_profile=}, '
                           f'{account.get("username")=}, {proxy=}, {url=}')
                    print(f'{utils.colorize(mes, utils.Fore.RED)}\n', end='')
                    break

                if count_error >= 3:
                    new_webdriver_chrome.quit()
                    new_webdriver_chrome = None
                    dir_with_profile = BASE_DIR.joinpath(f'profile{id_profile}')

                    start_time_to_delete = time.time()
                    while True:
                        if time.time() - start_time_to_delete > 50:
                            break
                        try:
                            shutil.rmtree(dir_with_profile)
                            break
                        except OSError as error:
                            time.sleep(2)
                            print(f'{utils.colorize(error, utils.Fore.RED)}\n', end='')
                count_error += 1

        result_json[url] = ready_json
        queue_big_theatre.task_done()


for _ in range(1, OPEN_BROWSER+1):
    start_thread = threading_try(get_json_from_selenium)
