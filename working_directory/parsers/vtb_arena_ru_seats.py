from requests.exceptions import ProxyError, JSONDecodeError
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.check import SpecialConditions
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.utils.parse_utils import double_split


class VtbArena(AsyncSeatsParser):
    event = 'newticket.vtb-arena.com'
    url_filter = lambda url: 'newticket.vtb-arena.com' in url or 'schematr.kassir.ru/widget' in url
    proxy_check = SpecialConditions(url='https://schematr.kassir.ru/')

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.scene = None
        self.widget_key = double_split(self.url, '?key=', '&eventId=')
        self.event_id_ = self.url[self.url.index('&eventId=')+len('&eventId='):]
        self.get_configuration_id = None
        self.count_error = 0

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def reformat(self, all_sectors):
        if 'динамо' in self.name.lower():
            vtb_hockey_reformat_dict = {
                'Ресторан Platinum': 'Трибуна Юрзинова. Ресторан Platinum',
                'Press 3': 'Трибуна Давыдова. Press 3',
                'Press 2': 'Трибуна Давыдова. Press 2',
                'Ложа A1': 'Трибуна Давыдова. Ложа A1',
                'Ложа A2': 'Трибуна Давыдова. Ложа A2',
                'Ложа A3': 'Трибуна Давыдова. Ложа A3',
                'Ложа A4': 'Трибуна Давыдова. Ложа A4',
                'Ложа A18': 'Трибуна Юрзинова. Ложа A18',
                'Ложа A17': 'Трибуна Васильева. Ложа A17',
                'Ложа A16': 'Трибуна Васильева. Ложа A16',
                'Ложа A15': 'Трибуна Васильева. Ложа A15',
                'Ложа A14': 'Трибуна Васильева. Ложа A14',
                'Ложа A13': 'Трибуна Васильева. Ложа A13',
                'Ложа A12': 'Трибуна Васильева. Ложа A12',
                'Ложа A11': 'Трибуна Васильева. Ложа A11',
                'Ложа A10': 'Трибуна Васильева. Ложа A10',
                'Ложа A9': 'Трибуна Васильева. Ложа A9',
                'Ложа A8': 'Трибуна Васильева. Ложа A8',
                'Ложа A7': 'Трибуна Васильева. Ложа A7',
                'Ложа A6': 'Трибуна Васильева. Ложа A6',
                'Ложа A19': 'Трибуна Юрзинова. Ложа A19/20',
                'Ложа A20': 'Трибуна Юрзинова. Ложа A19/20',
                'Press 1': 'Трибуна Давыдова. Press 1',
                'Ложа A21': 'Трибуна Юрзинова. Ложа A21',
                'Ложа A22': 'Трибуна Юрзинова. Ложа A22',
                'Ложа B1': 'Трибуна Юрзинова. Ложа B1',
                'Ложа B2': 'Трибуна Юрзинова. Ложа B2',
                'Ложа B3': 'Трибуна Юрзинова. Ложа B3',
                'Ложа B4': 'Трибуна Юрзинова. Ложа B4',
                'Ложа B5': 'Трибуна Юрзинова. Ложа B5',
                'Ложа B6': 'Трибуна Мальцева. Ложа B6',
                'Ложа B7': 'Трибуна Мальцева. Ложа B7',
                'Ложа B8': 'Трибуна Мальцева. Ложа B8',
                'Ложа B9': 'Трибуна Мальцева. Ложа B9',
                'Ложа B10': 'Трибуна Мальцева. Ложа B10',
                'Ложа B11': 'Трибуна Мальцева. Ложа B11',
                'Ложа B12': 'Трибуна Мальцева. Ложа B12',
                'Ложа B13': 'Трибуна Мальцева. Ложа B13',
                'Ложа B14': 'Трибуна Мальцева. Ложа B14',
                'Ложа B15': 'Трибуна Мальцева. Ложа B15',
                'Ложа B16': 'Трибуна Мальцева. Ложа B16',
                'Ложа B17': 'Трибуна Мальцева. Ложа B17',
                'Ложа B18': 'Трибуна Мальцева. Ложа B18',
                'Ложа B19': 'Трибуна Давыдова. Ложа B19',
                'Ложа B20': 'Трибуна Давыдова. Ложа B20',
                'Ложа B21': 'Трибуна Давыдова. Ложа B21',
                'Ложа B22': 'Трибуна Давыдова. Ложа B22',
                'A212. Лаунж': 'Трибуна Юрзинова. Сектор A212. Лаунж',
                'Сектор A210': 'Трибуна Васильева. Сектор A210',
                'Сектор A211': 'Трибуна Васильева. Сектор A211',
                'Сектор A212': 'Трибуна Юрзинова. Сектор A212',
                'Сектор B203': 'Трибуна Юрзинова. Сектор B203',
                'B203. Лаунж': 'Трибуна Юрзинова. Сектор B203. Лаунж',
                'Сектор B204': 'Трибуна Мальцева. Сектор B204',
                'VVIP': 'Трибуна Давыдова. VVIP',
                'Ложа A5': 'Трибуна Васильева. Ложа A5',
                'Сектор B312': 'Трибуна Давыдова. Сектор B312',
                'Сектор B311': 'Трибуна Давыдова. Сектор B311',
                'Сектор B310': 'Трибуна Давыдова. Сектор B310',
                'Сектор B309': 'Трибуна Мальцева. Сектор B309',
                'Сектор B308': 'Трибуна Мальцева. Сектор B308',
                'Сектор B307': 'Трибуна Мальцева. Сектор B307',
                'Сектор B306': 'Трибуна Мальцева. Сектор B306',
                'Сектор B305': 'Трибуна Мальцева. Сектор B305',
                'Сектор B304': 'Трибуна Мальцева. Сектор B304',
                'Сектор B303': 'Трибуна Юрзинова. Сектор B303',
                'Сектор B302': 'Трибуна Юрзинова. Сектор B302',
                'Сектор B301': 'Трибуна Юрзинова. Сектор B301',
                'Сектор B213': 'Трибуна Давыдова. Сектор B213',
                'Сектор B212': 'Трибуна Давыдова. Сектор B212',
                'Сектор B211': 'Трибуна Мальцева. Сектор B211',
                'Сектор B210': 'Трибуна Мальцева. Сектор B210',
                'Сектор B209': 'Трибуна Мальцева. Сектор B209',
                'Сектор B208': 'Трибуна Мальцева. Сектор B208',
                'Сектор B207': 'Трибуна Мальцева. Сектор B207',
                'Сектор B206': 'Трибуна Мальцева. Сектор B206',
                'Сектор B205': 'Трибуна Мальцева. Сектор B205',
                'Сектор B202': 'Трибуна Юрзинова. Сектор B202',
                'Сектор B201': 'Трибуна Юрзинова. Сектор B201',
                'Сектор B110': 'Трибуна Давыдова. Сектор B110',
                'Сектор B109': 'Трибуна Давыдова. Сектор B109',
                'Сектор B108': 'Трибуна Мальцева. Сектор B108',
                'Сектор B107': 'Трибуна Мальцева. Сектор B107',
                'Сектор B106': 'Трибуна Мальцева. Сектор B106',
                'Сектор B105': 'Трибуна Мальцева. Сектор B105',
                'Сектор B104': 'Трибуна Мальцева. Сектор B104',
                'Сектор B103': 'Трибуна Юрзинова. Сектор B103',
                'Сектор B102': 'Трибуна Юрзинова. Сектор B102',
                'Сектор B101': 'Трибуна Юрзинова. Сектор B101',
                'Сектор A312': 'Трибуна Юрзинова. Сектор A312',
                'Сектор A311': 'Трибуна Юрзинова. Сектор A311',
                'Сектор A310': 'Трибуна Юрзинова. Сектор A310',
                'Сектор A309': 'Трибуна Васильева. Сектор A309',
                'Сектор A308': 'Трибуна Васильева. Сектор A308',
                'Сектор A307': 'Трибуна Васильева. Сектор A307',
                'Сектор A306': 'Трибуна Васильева. Сектор A306',
                'Сектор A305': 'Трибуна Васильева. Сектор A305',
                'Сектор A304': 'Трибуна Васильева. Сектор A304',
                'Сектор A303': 'Трибуна Давыдова. Сектор A303',
                'Сектор A302': 'Трибуна Давыдова. Сектор A302',
                'Сектор A301': 'Трибуна Давыдова. Сектор A301',
                'Сектор A213': 'Трибуна Юрзинова. Сектор A213',
                'Сектор A209': 'Трибуна Васильева. Сектор A209',
                'Сектор A208': 'Трибуна Васильева. Сектор A208',
                'Сектор A207': 'Трибуна Васильева. Сектор A207',
                'Сектор A206': 'Трибуна Васильева. Сектор A206',
                'Сектор A205': 'Трибуна Васильева. Сектор A205',
                'Сектор A204': 'Трибуна Васильева. Сектор A204',
                'Сектор A203': 'Трибуна Давыдова. Сектор A203',
                'Сектор A202': 'Трибуна Давыдова. Сектор A202',
                'Сектор A201': 'Трибуна Давыдова. Сектор A201',
                'Сектор A110': 'Трибуна Юрзинова. Сектор A110',
                'Сектор A109': 'Трибуна Юрзинова. Сектор A109',
                'Сектор A108': 'Трибуна Васильева. Сектор A108',
                'Сектор A107': 'Трибуна Васильева. Сектор A107',
                'Сектор A106': 'Трибуна Васильева. Сектор A106',
                'Сектор A105': 'Трибуна Васильева. Сектор A105',
                'Сектор A104': 'Трибуна Васильева. Сектор A104',
                'Сектор A103': 'Трибуна Давыдова. Сектор A103',
                'Сектор A102': 'Трибуна Давыдова. Сектор A102',
                'Сектор A101': 'Трибуна Давыдова. Сектор A101',
                    }
            a_sectors_new = {}
            for sector in all_sectors:
                if sector.get('name') in vtb_hockey_reformat_dict:
                    a_sectors_new.setdefault(vtb_hockey_reformat_dict.get(sector.get('name')), {}).update(sector.get('tickets'))
                else:
                     a_sectors_new.setdefault(sector.get('name'), {}).update(sector.get('tickets'))
        
        else:
            vtb_reformat_dict = {
                'Press 3': 'Press 3',
                'Press 2': 'Press 2',
                'Press 1': 'Press 1',
                'Ложа A1': 'Ложа A1',
                'Ложа A2': 'Ложа A2',
                'Ложа A3': 'Ложа A3',
                'Ложа A4': 'Ложа A4',
                'Ложа A18': 'Ложа A18',
                'Ложа A17': 'Ложа A17',
                'Ложа A16': 'Ложа A16',
                'Ложа A15': 'Ложа A15',
                'Ложа A14': 'Ложа A14',
                'Ложа A13': 'Ложа A13',
                # 'Ложа A12': 'VIP A12',
                'Ложа A12': 'Ложа A12',
                'Ложа A11': 'Ложа A11',
                'Ложа A10': 'Ложа A10',
                'Ложа A10 (9 персон)': 'Ложа A10',
                'Ложа A9': 'Ложа A9',
                'Ложа A8': 'Ложа A8',
                'Ложа A7': 'Ложа A7',
                'Ложа A7 (6 персон)': 'Ложа A7',
                'Ложа A6': 'Ложа A6',
                'Ложа A19/20': 'Ложа A19/20',
                'Ложа A21': 'Ложа A21',
                'Ложа A22': 'Ложа A22',
                'Ложа B1': 'Ложа B1',
                'Ложа B2': 'Ложа B2',
                'Ложа B3': 'Ложа B3',
                'Ложа B4': 'Ложа B4',
                'Ложа B5': 'Ложа B5',
                'Ложа B6': 'Ложа B6',
                'Ложа B7': 'Ложа B7',
                'Ложа B8': 'Ложа B8',
                'Ложа B9': 'Ложа B9',
                'Ложа B10': 'Ложа B10',
                'Ложа B11': 'Ложа B11',
                'Ложа B12': 'Ложа B12',
                'Ложа B13': 'Ложа B13',
                'Ложа B14': 'Ложа B14',
                'Ложа B15': 'Ложа B15',
                'Ложа B16': 'Ложа B16',
                'Ложа B17': 'Ложа B17',
                'Ложа B18': 'Ложа B18',
                'Ложа B19': 'Ложа B19',
                'Ложа B20': 'Ложа B20',
                'Ложа B21': 'Ложа B21',
                'Ложа B22': 'Ложа B22',
                'Сектор A212. Лаунж': 'Сектор A212. Лаунж',
                'Сектор A210': 'Сектор A210',
                'Сектор A211': 'Сектор A211',
                'Сектор A212': 'Сектор A212',
                'Сектор B203. Лаунж': 'Сектор B203. Лаунж',
                'VVIP': 'VVIP',
                'Ложа A5': 'Ложа A5',
                'Сектор B312': 'Сектор B312',
                'Сектор B311': 'Сектор B311',
                'Сектор B310': 'Сектор B310',
                'Сектор B309': 'Сектор B309',
                'Сектор B308': 'Сектор B308',
                'Сектор B307': 'Сектор B307',
                'Сектор B306': 'Сектор B306',
                'Сектор B305': 'Сектор B305',
                'Сектор B304': 'Сектор B304',
                'Сектор B303': 'Сектор B303',
                'Сектор B302': 'Сектор B302',
                'Сектор B301': 'Сектор B301',
                'Сектор B213': 'Сектор B213',
                'Сектор B212': 'Сектор B212',
                'Сектор B211': 'Сектор B211',
                'Сектор B210': 'Сектор B210',
                'Сектор B209': 'Сектор B209',
                'Сектор B208': 'Сектор B208',
                'Сектор B207': 'Сектор B207',
                'Сектор B206': 'Сектор B206',
                'Сектор B205': 'Сектор B205',
                'Сектор B204': 'Сектор B204',
                'Сектор B203': 'Сектор B203',
                'Сектор B202': 'Сектор B202',
                'Сектор B201': 'Сектор B201',
                'Сектор B110': 'Сектор B110',
                'Сектор B109': 'Сектор B109',
                'Сектор B108': 'Сектор B108',
                'Сектор B107': 'Сектор B107',
                'Сектор B106': 'Сектор B106',
                'Сектор B105': 'Сектор B105',
                'Сектор B104': 'Сектор B104',
                'Сектор B103': 'Сектор B103',
                'Сектор B102': 'Сектор B102',
                'Сектор B101': 'Сектор B101',
                'Сектор A312': 'Сектор A312',
                'Сектор A311': 'Сектор A311',
                'Сектор A310': 'Сектор A310',
                'Сектор A309': 'Сектор A309',
                'Сектор A308': 'Сектор A308',
                'Сектор A307': 'Сектор A307',
                'Сектор A306': 'Сектор A306',
                'Сектор A305': 'Сектор A305',
                'Сектор A304': 'Сектор A304',
                'Сектор A303': 'Сектор A303',
                'Сектор A302': 'Сектор A302',
                'Сектор A301': 'Сектор A301',
                'Сектор A213': 'Сектор A213',
                'Сектор A209': 'Сектор A209',
                'Сектор A208': 'Сектор A208',
                'Сектор A207': 'Сектор A207',
                'Сектор A206': 'Сектор A206',
                'Сектор A205': 'Сектор A205',
                'Сектор A204': 'Сектор A204',
                'Сектор A203': 'Сектор A203',
                'Сектор A202': 'Сектор A202',
                'Сектор A201': 'Сектор A201',
                'Сектор A110': 'Сектор A110',
                'Сектор A109': 'Сектор A109',
                'Сектор A108': 'Сектор A108',
                'Сектор A107': 'Сектор A107',
                'Сектор A106': 'Сектор A106',
                'Сектор A105': 'Сектор A105',
                'Сектор A104': 'Сектор A104',
                'Сектор A103': 'Сектор A103',
                'Сектор A102': 'Сектор A102',
                'Сектор A101': 'Сектор A101',
                'A101 VIP пакет (фирменная футболка и ранний вход на чек)': 'Сектор A101',
                'VIP Партер - Левая сторона': 'Партер, левая сторона',
                'Партер, левая сторона': 'Партер, левая сторона',
                'Партер, правая сторона': 'Партер, правая сторона',
                'Фан зона': 'Фан-зона',
                'ФАНЗОНА': 'Фан-зона',
                'Танцевальный партер': 'Танцпол',
                'ТАНЦПОЛ': 'Танцпол',
                'Ложа B22 (11 персон)': 'Ложа B22',
                'Ложа A6 (6 персон)': 'Ложа A6',
                'Ложа A5 (6 персон)': 'Ложа A5',
                'Ложа C6 (на 12 персон)': 'VIP C6 (целиком)',
                'Ложа С1 (на 13 персон)': 'VIP С1 (целиком)',
                'Ложа А10 (на 13 персон)': 'VIP A10 (целиком)',
                'B 312': 'Сектор B312',
                'B 311': 'Сектор B311',
                'B 310': 'Сектор B310',
                'B 309': 'Сектор B309',
                'B 308': 'Сектор B308',
                'B 307': 'Сектор B307',
                'B 306': 'Сектор B306',
                'B 305': 'Сектор B305',
                'B 304': 'Сектор B304',
                'B 303': 'Сектор B303',
                'B 302': 'Сектор B302',
                'B 301': 'Сектор B301',
                'B 213': 'Сектор B213',
                'B 212': 'Сектор B212',
                'B 211': 'Сектор B211',
                'B 210': 'Сектор B210',
                'B 209': 'Сектор B209',
                'B 208': 'Сектор B208',
                'B 207': 'Сектор B207',
                'B 206': 'Сектор B206',
                'B 205': 'Сектор B205',
                'B 204': 'Сектор B204',
                'B 203': 'Сектор B203',
                'B203 (ограниченная видимость)': 'Сектор B203',
                'B 202': 'Сектор B202',
                'B 201': 'Сектор B201',
                'B 110': 'Сектор B110',
                'B 109': 'Сектор B109',
                'B 108': 'Сектор B108',
                'B 107': 'Сектор B107',
                'B 106': 'Сектор B106',
                'B 105': 'Сектор B105',
                'B 104': 'Сектор B104',
                'B 103': 'Сектор B103',
                'B103 (ограниченная видимость)': 'Сектор B103',
                'B 102': 'Сектор B102',
                'B 101': 'Сектор B101',
                'A 312': 'Сектор A312',
                'A 311': 'Сектор A311',
                'A 310': 'Сектор A310',
                'A 309': 'Сектор A309',
                'A 308': 'Сектор A308',
                'A 307': 'Сектор A307',
                'A 306': 'Сектор A306',
                'A 305': 'Сектор A305',
                'A 304': 'Сектор A304',
                'A 303': 'Сектор A303',
                'A 302': 'Сектор A302',
                'A 301': 'Сектор A301',
                'A 213': 'Сектор A213',
                'A 212': 'Сектор A212',
                'A 211': 'Сектор A211',
                'A 210': 'Сектор A210',
                'A 209': 'Сектор A209',
                'A 208': 'Сектор A208',
                'A 207': 'Сектор A207',
                'A 206': 'Сектор A206',
                'A 205': 'Сектор A205',
                'A 204': 'Сектор A204',
                'A 203': 'Сектор A203',
                'A 202': 'Сектор A202',
                'A 201': 'Сектор A201',
                'A 110': 'Сектор A110',
                'A 109': 'Сектор A109',
                'A 108': 'Сектор A108',
                'A 107': 'Сектор A107',
                'A 106': 'Сектор A106',
                'A 105': 'Сектор A105',
                'A 104': 'Сектор A104',
                'A 103': 'Сектор A103',
                'A 102': 'Сектор A102',
                'A 101': 'Сектор A101',
                'B312': 'Сектор B312',
                'B311': 'Сектор B311',
                'B310': 'Сектор B310',
                'B309': 'Сектор B309',
                'B308': 'Сектор B308',
                'B307': 'Сектор B307',
                'B306': 'Сектор B306',
                'B305': 'Сектор B305',
                'B304': 'Сектор B304',
                'B303': 'Сектор B303',
                'B302': 'Сектор B302',
                'B301': 'Сектор B301',
                'B213': 'Сектор B213',
                'B212': 'Сектор B212',
                'B211': 'Сектор B211',
                'B210': 'Сектор B210',
                'B209': 'Сектор B209',
                'B208': 'Сектор B208',
                'B207': 'Сектор B207',
                'B206': 'Сектор B206',
                'B205': 'Сектор B205',
                'B204': 'Сектор B204',
                'B203': 'Сектор B203',
                'B202': 'Сектор B202',
                'B201': 'Сектор B201',
                'B110': 'Сектор B110',
                'B109': 'Сектор B109',
                'B108': 'Сектор B108',
                'B107': 'Сектор B107',
                'B106': 'Сектор B106',
                'B105': 'Сектор B105',
                'B104': 'Сектор B104',
                'B103': 'Сектор B103',
                'B102': 'Сектор B102',
                'B101': 'Сектор B101',
                'A312': 'Сектор A312',
                'A311': 'Сектор A311',
                'A310': 'Сектор A310',
                'A309': 'Сектор A309',
                'A308': 'Сектор A308',
                'A307': 'Сектор A307',
                'A306': 'Сектор A306',
                'A305': 'Сектор A305',
                'A304': 'Сектор A304',
                'A303': 'Сектор A303',
                'A302': 'Сектор A302',
                'A301': 'Сектор A301',
                'A213': 'Сектор A213',
                'A212': 'Сектор A212',
                'A211': 'Сектор A211',
                'A210': 'Сектор A210',
                'A209': 'Сектор A209',
                'A208': 'Сектор A208',
                'A207': 'Сектор A207',
                'A206': 'Сектор A206',
                'A205': 'Сектор A205',
                'A204': 'Сектор A204',
                'A203': 'Сектор A203',
                'A202': 'Сектор A202',
                'A201': 'Сектор A201',
                'A110': 'Сектор A110',
                'A109': 'Сектор A109',
                'A108': 'Сектор A108',
                'A107': 'Сектор A107',
                'A106': 'Сектор A106',
                'A105': 'Сектор A105',
                'A104': 'Сектор A104',
                'A103': 'Сектор A103',
                'A102': 'Сектор A102',
                'A101': 'Сектор A101',
            }
            a_sectors_new = {}
            for sector in all_sectors:
                if sector.get('name') in vtb_reformat_dict:
                    a_sectors_new.setdefault(vtb_reformat_dict.get(sector.get('name')), {}).update(sector.get('tickets'))
                else:
                     a_sectors_new.setdefault(sector.get('name'), {}).update(sector.get('tickets'))
        
        return a_sectors_new


    def parse_seats(self, json_data):
        total_sector = []

        json_data = json_data.get('response')

        price_list = {}

        all_price = json_data.get('priceList')
        for price in all_price:
            price_name = price.get('zonename')
            price_count = int(price.get('price'))
            price_list[price_name] = price_count

        svg_data = json_data.get('blob')
        svg_data = BeautifulSoup(svg_data, 'xml')

        sector_with_seats_dict = {}

        if svg_data.find_all('ellipse'):
            self.scene = 'hokey'

        all_sector = svg_data.select('g[sector]')
        for g in all_sector:
            sector_name = g.get('data-sector')
            rows = g.find_all('g')
            for row in rows:
                seats_in_row = row.find_all('circle')
                row = row.get('data-row')
                for seat in seats_in_row:
                    price = seat.get('class')
                    if price != 'cat_1':
                        seat_in_row = seat.get('data-seat')
                        price = price_list[price]
                        if sector_with_seats_dict.get(sector_name):
                            dict_sector = sector_with_seats_dict[sector_name]
                            dict_sector[(row, seat_in_row,)] = price
                        else:
                            sector_with_seats_dict[sector_name] = {(row, seat_in_row,): price}

        for sector, total_seats_row_prices in sector_with_seats_dict.items():
            total_sector.append(
                {
                    "name": sector,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    async def request_parser(self, url, data):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'connection': 'keep-alive',
            'content-type': 'application/json;charset=UTF-8',
            'host': 'newticket.vtb-arena.com',
            'origin': 'https://newticket.vtb-arena.com',
            'referer': 'https://newticket.vtb-arena.com/',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent
        }
        r = await self.session.post(url, headers=headers, json=data, ssl=False)
        return r.json()

    async def get_seats(self):
        url = 'https://newticket.vtb-arena.com/api/scheme'
        data = {
            "id": self.url.split('/')[-1],
            "lang": "ru"
        }
        json_data = await self.request_parser(url=url, data=data)

        a_events = self.parse_seats(json_data)

        return a_events

    async def parse_seats_kassir(self, json_data):
        total_sector = []

        sectors_data = []
        all_sectors = json_data.get('sectors')
        for sector in all_sectors:
            sectors_tariffs_id = list(sector.get('availableQuantityByTariffs').keys())
            [sectors_data.append(tariff_id) for tariff_id in sectors_tariffs_id]

        tariffs_data = {}
        all_tariffs = json_data.get('tariffs')
        for tariff in all_tariffs:
            tariff_id = str(tariff.get('id'))
            tariff_available_seats = tariff.get('availableSeats')
            if len(tariff_available_seats) == 0:
                tariff_available_seats = [tariff.get('id')]
            tariff_price = tariff.get('price')
            tariffs_data[tariff_id] = (tariff_price, tariff_available_seats,)

        url = f'https://schematr.kassir.ru/api/v1/halls/configurations/{self.get_configuration_id}?language=ru&phpEventId={self.event_id_}'
        get_all_seats = await self.request_parser_kassir(url)
        if get_all_seats is None:
            return []

        all_id_seat = {}
        all_seats_in_sector = get_all_seats.get('data').get('sectors')
        for seats_in_sector in all_seats_in_sector:
            sector_name = seats_in_sector.get('name')
            rows = seats_in_sector.get('rows')
            if rows is None:
                continue
            for row in rows:
                row_number = row.get('name')
                seats_in_row = row.get('seats')
                for seat in seats_in_row:
                    seat_id = seat.get('id')
                    seat_number = seat.get('number')
                    all_id_seat[seat_id] = {sector_name: (str(row_number), str(seat_number),)}

        final_data = {}
        for tariff_id in sectors_data:
            price, seats_list_is_real = tariffs_data.get(tariff_id)
            for seat_id in seats_list_is_real:
                this_seat_data = all_id_seat.get(seat_id)
                if this_seat_data is None:
                    continue
                sector_name = list(this_seat_data.keys())[0]
                row_and_seat = tuple(this_seat_data.values())[0]
                real_place_in_sector = {row_and_seat: int(price)}
                if final_data.get(sector_name):
                    this_sector = final_data[sector_name]
                    this_sector[row_and_seat] = int(price)
                    final_data[sector_name] = this_sector
                else:
                    final_data[sector_name] = real_place_in_sector

        for sector_name, total_seats_row_prices in final_data.items():
            total_sector.append(
                {
                    "name": sector_name,
                    "tickets": total_seats_row_prices
                }
            )

        return total_sector

    async def request_parser_kassir(self, url):
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'referer': self.url,
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'Host': 'crocus2.kassir.ru',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-widget-key': self.widget_key
        }
        r = await self.session.get(url, headers=headers, ssl=False)
        if r.status_code == 500:
            return None
        try:
            return r.json()
        except JSONDecodeError:
            message = f"<b>vtb_seats json_error {r.status_code} {self.url = }</b>"
            self.send_message_to_telegram(message)
            return None

    async def get_seats_from_kassir(self):
        url = f'https://schematr.kassir.ru/api/v1/events/{self.event_id_}?language=ru'
        get_configuration_id = await self.request_parser_kassir(url)
        if get_configuration_id is None:
            return []
        self.get_configuration_id = get_configuration_id.get('meta')
        if self.get_configuration_id is None:
            return []
        self.get_configuration_id = self.get_configuration_id.get('trHallConfigurationId')

        url = f'https://schematr.kassir.ru/api/v1/events/{self.event_id_}/seats?language=ru&phpEventId={self.event_id_}'
        json_data = await self.request_parser_kassir(url)
        if json_data is None:
            return []

        json_data = json_data.get('data')
        if json_data is None and self.count_error < 10:
            self.count_error += 1
            raise ProxyError('crocus_seats error: json_data is None')
        elif json_data is None and self.count_error == 10:
            self.count_error = 0
            raise Exception('crocus_seats error: json_data is None')
        self.count_error = 0

        all_sectors = await self.parse_seats_kassir(json_data)

        return all_sectors

    async def body(self):
        if 'newticket' in self.url:
            all_sectors = await self.get_seats()
        else:
            all_sectors = await self.get_seats_from_kassir()

        all_sectors = self.reformat(all_sectors)

        for sector, tickets in all_sectors.items():
            self.register_sector(sector, tickets)
        #self.check_sectors()
