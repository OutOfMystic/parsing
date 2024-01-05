from bs4 import BeautifulSoup
from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
from requests import get
from bs4 import BeautifulSoup
from json import loads
from parse_module.utils.exceptions import InternalError


class HcTractorSeatsParser(SeatsParser):
    url_filter = lambda url: "tractor-arena.com" in url
    
    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1800
        self.driver_source = None
        self.url_format = ("https://widget-api.tractor-arena.com/api/widget/{widget_id}/ticket?"
                           "lang=ru&currency=RUB&event={id}&is_landing=true")
        self.url_format_event = f'https://tractor-arena.com/events/{self.parent_id}'
        self._id = self.url.split("/")[-1]
        
    def before_body(self):
        self.session = ProxySession(self)
    
    def parse_widget_id(self):
        resp = get(self.url_format_event, headers={'user-agent': self.user_agent})
        soup = BeautifulSoup(resp.text, 'lxml')
        try:
            return loads(soup.select_one("#__NEXT_DATA__").text)['props']['pageProps']['event']['widget_detail']['id']
        except KeyError:
            raise InternalError("Cant get widget_id")

    def get_sectors(self, widget_id):
        resp = get(self.url_format.format(widget_id=widget_id, id=self._id),
                   headers={'user-agent': self.user_agent})
        self.debug(resp)
        json_ = loads(resp.text)
        return json_

    def parse_sectors(self):
        reformat_dict = {
            'Места МГН': 'Спецтрибуна для МГН',
            'B5. Гостевой сектор': 'B5',
            'Сектор C5. Ресторан': 'C5. Ресторан'
        }
        reform = lambda name: reformat_dict.get(name, name)
        resp = self.get_sectors(self.parse_widget_id())
        sectors = {}
        for sector in resp['sectors']:
            name = reform(sector['i'])
            sectors[name] = dict()
            for row in sector['r']:
                r_name = str(row['i'])
                for seat in row['s']:
                    s_name = str(seat['i'])
                    sectors[name][(r_name, s_name)] = int(seat['p'])
        return sectors

    def body(self):
        try:
            sectors = self.parse_sectors()
        except KeyError:
            raise InternalError("No seats to parse")
        for s_name, vals in sectors.items():
            self.register_sector(s_name, vals)
        #self.check_sectors()