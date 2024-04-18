import json
import os
import warnings

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests

from ..logger import logger

warnings.filterwarnings("ignore", category=UserWarning, module="bs4")

class CBRcurrentCourses:
    '''ЦЕНТРАЛЬНЫЙ БАНК РОССИИ'''
    def __init__(self):
        self.module_path = os.path.dirname(__file__)
        self.timestamp = os.path.join(self.module_path, 'timestamp.json')
        self.data = self._load_data()

    def _load_data(self):
        """Загружает данные о последнем обнолении
           из JSON-файла или инициализирует новый файл, если он не существует."""
        if os.path.exists(self.timestamp):
            with open(self.timestamp, 'r') as file:
                return json.load(file)
        else:
            return {}

    def _update_timestamp(self):
        """Обновляет временную отметку в данных."""
        self.data['timestamp'] = datetime.now().isoformat()
        with open(self.timestamp, 'w') as file:
            json.dump(self.data, file, ensure_ascii=False, indent=4)

    def _check_timestamp(self):
        """Проверяет временную отметку и вернет True, если отметка старше 2 часов.
           Если 2 часа не прошли вернет False"""
        if 'timestamp' in self.data:
            last_update_time = datetime.fromisoformat(self.data['timestamp'])
            if datetime.now() - last_update_time > timedelta(hours=2):
                logger.info("Временная отметка устарела, обновляем данные.", name='CBRcurrentCourses')
                return True
            else:
                logger.info("Данные курсов валют актуальны.", name='CBRcurrentCourses')
                return False
        else:
            logger.info("Временная отметка отсутствует, создаем новую.", name='CBRcurrentCourses')
            self._update_timestamp()
            return True

    def _request(self):
        # Форматирование даты для запроса
        date_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        # Тело SOAP запроса
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
        <soap12:Body>
            <GetCursOnDate xmlns="http://web.cbr.ru/">
            <On_date>{date_str}</On_date>
            </GetCursOnDate>
        </soap12:Body>
        </soap12:Envelope>'''
        # Заголовки запроса
        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'Host': 'www.cbr.ru'
        }
        # URL веб-сервиса ЦБР
        url = 'http://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx'
        # Отправка POST запроса
        response = requests.post(url, data=soap_request, headers=headers)
        if response.ok:
            return response.text
        response.raise_for_status()

    def _make_json_from_xml(self, xmlText):
        '''
            [
                {
                    "name": "Австралийский доллар",
                    "nominal": 1,
                    "rate": 60.7206,
                    "code": 36,
                    "char_code": "AUD",
                    "unit_rate": 60.7206
                } ,...
            ]
        '''
        soup = BeautifulSoup(xmlText, features="lxml")
        # Находим все элементы ValuteCursOnDate
        valute_elements = soup.find_all('valutecursondate')
        # Создаем список для хранения данных
        currencies = []
        # Перебираем найденные элементы и извлекаем информацию
        for valute in valute_elements:
            currency_data = {
                'name': valute.find('vname').text.strip(),
                'nominal': int(valute.find('vnom').text),
                'rate': float(valute.find('vcurs').text),
                'code': int(valute.find('vcode').text),
                'char_code': valute.find('vchcode').text.strip(),
                'unit_rate': float(valute.find('vunitrate').text)
            }
            currencies.append(currency_data)
        return currencies

    def _convert_json(self, json_start):
        '''
        {
            "AUD": {
                "name": "Австралийский доллар",
                "nominal": 1,
                "rate": 60.7206,
                "code": 36,
                "unit_rate": 60.7206
            },...
        }
        '''
        json_finish = {
            currency["char_code"]: {key: value for key, value in currency.items() if key != "char_code"}
            for currency in json_start
        }
        return json_finish

    def main(self):
        if self._check_timestamp():
            getcurs_xmltext = self._request()
            getcurs_json = self._make_json_from_xml(getcurs_xmltext)
            getcurs = self._convert_json(getcurs_json)

            file_path = os.path.join(self.module_path, 'get_curs.json')
            # Сохраняем данные в файл
            with open(file_path, 'w') as file:
                json.dump(getcurs, file, ensure_ascii=False, indent=4)


class ConverterManager(CBRcurrentCourses):
    def __init__(self):
        super().__init__()
        self._last_update()
        self.currency_rates = self._load_current_corses()

    def _last_update(self):
        if 'timestamp' in self.data:
            last_update_time = datetime.fromisoformat(self.data['timestamp'])
            current_time = datetime.now()
            if current_time - last_update_time > timedelta(hours=2):
                logger.warning(f"Курсы валют устарели!{last_update_time}")
            else:
                logger.info(f"Последнее обновление курсов валют {last_update_time}")
        else:
            logger.warning("Временная отметка курсов валют отсутствует")
            self.main()

    def _load_current_corses(self):
        get_cours = os.path.join(self.module_path, 'get_curs.json')
        with open(get_cours, "r") as json_file:
            currency_rates = json.load(json_file)
            return currency_rates

    def convert_to_rub(self, amount, currency_code):
        """
        Конвертирует заданную сумму из указанной валюты в российские рубли.

        :param amount: Сумма в исходной валюте.
        :param currency_code: Код валюты, например 'USD'.
        :param currency_rates: Словарь с данными о валютах.
        :return: Сумма в российских рублях.
        :raises ValueError: Если валюта не найдена в словаре.
        """
        if currency_code in self.currency_rates:
            currency_info = self.currency_rates[currency_code]
            # Конвертируем введенную сумму в рубли
            result_in_rub = amount * (currency_info['rate'] / currency_info['nominal'])
            rounded_result_in_rub = round(result_in_rub)
            result_in_rub = int(rounded_result_in_rub)
            return result_in_rub
        else:
            raise ValueError(f"Валюта {currency_code} не найдена в словаре курсов.")


def convert_to_rub(amount, currency_code):
    """
    Конвертирует заданную сумму из указанной валюты в российские рубли.

    :param amount: Сумма в исходной валюте.
    :param currency_code: Код валюты, например 'USD'.
    :param currency_rates: Словарь с данными о валютах.
    :return: Сумма в российских рублях.
    :raises ValueError: Если валюта не найдена в словаре.
    """
    module_path = os.path.dirname(__file__)
    filename = os.path.join(module_path, 'get_curs.json')
    with open(filename, "r") as json_file:
        currency_rates = json.load(json_file)
    if currency_code in currency_rates:
        currency_info = currency_rates[currency_code]
        # Конвертируем введенную сумму в рубли
        result_in_rub = amount * (currency_info['rate'] / currency_info['nominal'])
        return result_in_rub
    else:
        raise ValueError(f"Валюта {currency_code} не найдена в словаре курсов.")