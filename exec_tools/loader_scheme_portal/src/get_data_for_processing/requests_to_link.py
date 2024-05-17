import json
import time

from ..logging_to_project import logger_to_project
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def get_urls_from_main_url(main_url: str, time_sleep: int) -> dict[str, str]:
    '''
    Получение ссылок для скачивания
    :param main_url: 'https://portalbilet.ru/events/vecherinka-comedy-club-tab/2024-07-26'
    :param time_sleep: 10
    :return:
        [all_seats, svg_scheme, all_sector_with_svg_path]
        dict_values(['https://event-api.pbilet.net/api/v1/hall_layouts/3518',
        'https://cdn.pbilet.com/origin/bba5eb1b-334e-497c-b39e-385878220fb6.svg',
         'https://api.pbilet.net/public/v1/tickets?currency_code=RUB&lang=ru&event_source_id=7460&event_date_id=248372'])

    '''
    url_to_data = {}

    options = Options()
    options.add_argument('--no-sandbox')
    # options.add_argument('--disable-gpu')
    # options.add_argument('--headless')

    # Настройка логирования
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(url=main_url)
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(.5)
        driver.execute_script("window.scrollTo(300, 500);")
        time.sleep(time_sleep)

        def process_browser_log_entry(entry):
            response = json.loads(entry['message'])['message']
            return response

        browser_log = driver.get_log('performance')
        events = [process_browser_log_entry(entry) for entry in browser_log]

        for event in events:
            # print(event, 'event###')
            if event.get('params') is not None and \
                    'Network.response' in event['method'] and \
                    event['params'].get('response') is not None and \
                    event['params']['response'].get('url') is not None:
                get_url = event['params']['response']['url']
                if 'https://event-api' in get_url:
                    url_to_data['all_seats'] = get_url
                if 'ticket' in get_url.split('/')[-1]:
                    url_to_data['all_sector_with_svg_path'] = get_url
                if 'cdn.pbilet.com' in get_url:
                    url_to_data['svg_scheme'] = get_url
    except Exception as e:
        logger_to_project.error(f"Возникла ошибка {e}")
    finally:
        driver.quit()
    return url_to_data
