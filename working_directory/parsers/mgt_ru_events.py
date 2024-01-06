import json
from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession

from datetime import datetime
import re



headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru,en;q=0.9',
    'Connection': 'keep-alive',
    'Origin': 'https://m-g-t.ru',
    'Referer': 'https://m-g-t.ru/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.962 YaBrowser/23.9.1.962 Yowser/2.5 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "YaBrowser";v="23"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
}

class MosGubern(EventParser):
    
    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.url = 'https://m-g-t.ru/'        
        
    def before_body(self):
        self.session = ProxySession(self)

    def get_dates_list(self) -> list[str]:
        now = datetime.now()
        formatted_date = f"{now.month}.{now.year}"
        
        req = self.session.get(f"https://api.m-g-t.ru/api/get_poster.php", params={"date": formatted_date}, headers=headers)
        data = req.json()
        months = data['FILTER_MONTH']
        
        month_dates = []
        for month in months:
            month_date = month['ID']
            month_dates.append(month_date)

        return month_dates

    def extract_link_from_js(self, js_string):
        match = re.search(r"'(https://.*?)'", js_string)
        if match:
            return match.group(1)
        return None

    def parse_json(self, data: json) -> list[tuple]:
        a_events = []
        
        events = data['CONTENT']
        for event_id, event_data in events.items():
            
            performances = event_data['PERFORMANCES']
            for performance_id, performance_data in performances.items():
                
                name = performance_data["NAME"]
                variants = performance_data["POSTER"]
                for variant_id, variant_data in variants.items():
                    
                    date = variant_data["DATE"]     
                    date_object = datetime.strptime(date, "%d.%m.%Y %H:%M:%S")
                    link = variant_data["BUTTON_LINK"]
                    
                    if link.startswith("javaScript:TLCallWidget"):
                        extracted_link = self.extract_link_from_js(link)
                        if extracted_link:
                            link = extracted_link
                            a_events.append((name, link, date_object))
                    else:
                        a_events.append((name, link, date_object))
    
    def get_json(self, date) -> json:
        
        req = self.session.get(f"https://api.m-g-t.ru/api/get_poster.php", params={"date": date}, headers=headers)
        req.raise_for_status()  # Добавляем обработку ошибок
        data = req.json()
        
    def body(self):
        dates = self.get_dates_list()
        
        for date in dates:
            data = self.get_json()
            
            a_events = self.parse_json(data)
            
            for event in a_events:
                self.register_event(event[0], event[1], date=event[2])