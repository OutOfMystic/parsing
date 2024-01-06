from parse_module.models.parser import SeatsParser
from parse_module.coroutines import AsyncSeatsParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession


class CircusKislovodsk(AsyncSeatsParser):
    url_filter = lambda url: 'ticket-place.ru' in url and '|kislovodsk' in url

    def __init__(self, *args, **extra) -> None:
        super().__init__(*args, **extra)
        self.delay = 1200
        self.driver_source = None
        self.url = self.url.split('|')[0]
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "sec-ch-ua": "\"Not/A)Brand\";v=\"99\", \"Google Chrome\";v=\"115\", \"Chromium\";v=\"115\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "user-agent": self.user_agent
        }

    def work_with_json(self, r_json :dict):
        places = r_json.get("data").get("seats").get("data")

        reformat = {
            'Сектор 1': '1',
            'Сектор 2': '2',
            'Сектор 3': '3',
            'Сектор 4': '4',
            'Сектор 5': '5',
            'Сектор 6': '6',
            'Сектор 7': '7',
            'Сектор 8': '8',
        }

        a_sectors = {}
        for place in places:
            if place.get("status") == "free":
                sector = place.get("sector_name")
                if sector in reformat:
                    sector = reformat[sector]
                a_sectors.setdefault(sector, {}).update({
                    (str(place["row_sector"]), str(place["seat_number"])): int(place["price"])
                })

        return a_sectors

    async def before_body(self):
        self.session = AsyncProxySession(self)

    async def body(self):
        r = await self.session.get_json(self.url, headers=self.headers)

        a_sectors = self.work_with_json(r.json())

        for sector, tickets in a_sectors.items():
            self.register_sector(sector, tickets)
        #self.check_sectors()