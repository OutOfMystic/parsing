from parse_module.models.parser import SeatsParser
from parse_module.manager.proxy.instances import ProxySession


class DynamoParser(SeatsParser):
    event = 'tickets.dynamo.ru'
    url_filter = lambda url: 'widget.afisha.yandex.ru' in url

    def __init__(self, *args, **extra):
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None

    def before_body(self):
        self.session = ProxySession(self)

    def reformat(self, a_sectors):
        tribune_1 = 'Трибуна Давыдова. '
        tribune_2 = 'Трибуна Васильева. '
        tribune_3 = 'Трибуна Юрзинова. '
        tribune_4 = 'Трибуна Мальцева. '

        for sector in a_sectors:
            sector_name = sector.get('name').strip()
            if 'A305' in sector_name:
                sector['name'] = "Трибуна Васильева. Сектор A305"
            if 'Ресторан' in sector_name:
                sector['name'] = tribune_3 + sector_name
            if 'Press' in sector_name or 'VVIP' in sector_name:
                sector['name'] = tribune_1 + sector_name
            if 'Сектор' in sector_name:
                try:
                    number_sector = int(sector_name.split('.')[0][-3:])
                except ValueError:
                    continue
                # if sector_name[-4] == 'A' and 100 < number_sector <= 110:
                #     sector['name'] = tribune_1 + sector_name
                #     continue
                if 300 < number_sector <= 303 or 200 < number_sector <= 203 or 100 < number_sector <= 103:
                    tribune = tribune_1 if 'A' in sector_name else tribune_3
                    sector['name'] = tribune + sector_name
                elif 304 <= number_sector <= 309 or 204 <= number_sector <= 211 or 104 <= number_sector <= 108:
                    tribune = tribune_2 if 'A' in sector_name else tribune_4
                    sector['name'] = tribune + sector_name
                elif 310 <= number_sector < 315 or 212 <= number_sector < 215 or 109 <= number_sector < 115:
                    tribune = tribune_3 if 'A' in sector_name else tribune_1
                    sector['name'] = tribune + sector_name
            if 'Ложа' in sector_name:
                number_sector = int(sector_name[-2:])
                if sector_name[-4] == 'A':
                    if 1 < number_sector <= 4:
                        sector['name'] = tribune_1 + sector_name
                    elif 5 <= number_sector <= 17:
                        sector['name'] = tribune_2 + sector_name
                    elif 18 <= number_sector < 2:
                        sector['name'] = tribune_3 + sector_name
                else:
                    if 1 < number_sector <= 5:
                        sector['name'] = tribune_3 + sector_name
                    elif 6 <= number_sector <= 18:
                        sector['name'] = tribune_4 + sector_name
                    elif 19 <= number_sector < 2:
                        sector['name'] = tribune_1 + sector_name

    def parse_seats(self):
        get_parameter = self.request_json_data(url=self.url)

        parameter_for_url = get_parameter.get('result').get('session').get('key')
        second_parameter_for_url = self.url[self.url.index('=')+1:]

        url_to_data = f'https://widget.afisha.yandex.ru/api/tickets/v1/sessions/{parameter_for_url}/hallplan/async?clientKey={second_parameter_for_url}'
        json_data = self.last_request_json_data(url=url_to_data)

        total_sector = []
        for sector in json_data:
            sector_name = sector.get('name')

            for ticket in sector.get('seats'):
                row = str(ticket.get('seat').get('row'))
                seat = str(ticket.get('seat').get('place'))
                price = int(float(ticket.get('priceInfo').get('total').get('value')) / 100)

                for sector in total_sector:
                    if sector_name == sector.get('name'):
                        sector['tickets'][row, seat] = price
                        break
                else:
                    total_sector.append({
                        'name': sector_name,
                        'tickets': {(row, seat): price}
                    })
        return total_sector

    def last_request_json_data(self, url, req=0):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'widget.afisha.yandex.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)

        if 'result' not in r.text:
            new_url = url + '&req_number=' + str(req)
            return self.last_request_json_data(url=new_url, req=req+1)
        if r.json()['status'] != 'success':
            new_url = url + '&req_number=' + str(req)
            return self.last_request_json_data(url=new_url, req=req+1)
        if 'hallplan' not in r.json()['result']:
            new_url = url + '&req_number=' + str(req)
            return self.last_request_json_data(url=new_url, req=req+1)

        return r.json()['result']['hallplan']['levels']

    def request_json_data(self, url):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru,en;q=0.9',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'host': 'widget.afisha.yandex.ru',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(url, headers=headers)

        return r.json()

    def body(self):
        a_sectors = self.parse_seats()

        self.reformat(a_sectors)

        for sector in a_sectors:
            self.register_sector(sector['name'], sector['tickets'])
