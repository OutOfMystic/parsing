import secrets
import string
from bs4 import BeautifulSoup

from parse_module.coroutines import AsyncEventParser
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession, AsyncProxySession
import re


class Parser(AsyncEventParser):

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 3600
        self.driver_source = None
        self.url = 'https://www.tickets-star.com/cat/176/CategoryId/2/'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    def r_str(self):
        letters_and_digits = string.ascii_letters + string.digits
        crypt_rand_string = ''.join(secrets.choice(
            letters_and_digits) for i in range(16))
        return (crypt_rand_string)

    def get_edate(self, soup):
        mydate = soup.find('div', class_='date_an_s').get_text()
        mydate = mydate.split(',')[0] + mydate.split(',')[2]
        day, month, y, t = mydate.strip().split(' ')
        if len(day) == 1:
            day = '0' + day
        month = month[:3].capitalize()
        f_d = f'{day} {month} {y} {t}'
        return (f_d)

    def get_uri(self, soup):
        teg_script = soup.find_all('script')
        uri = teg_script[18]
        pattern = re.compile("(\w+): '(.*?)'")
        fields = dict(re.findall(pattern, uri.text))
        p_id = fields['data'].split('=')[1]
        return p_id

    async def get_links_events(self):
        response = await self.session.get(self.url, headers={'user-agent': self.user_agent})
        soup = BeautifulSoup(response.text, 'lxml')
        afishes = [afisha.get('href') for afisha in soup.find_all('a', class_='btn')]
        venues = [venue.text for venue in soup.find_all('h2')]
        links = []
        url = 'https://www.tickets-star.com'

        for circus_url in circus_urls:
            resp_bt = await self.session.get(url + circus_url)
            soup = BeautifulSoup(resp_bt.text, 'lxml')
            name = soup.find('h1').get_text()
            edate = self.get_edate(soup)
            scene = soup.find('a', {'id': 'StageMapImage55'}).get('title')
            link = [
                name,
                url + circus_url,
                edate,
                scene,
                "Цирк на Вернадского"
            ]
            links.append(link)

        for afisha, venue in zip(afishes, venues):
            response_a = await self.session.get(url + afisha)
            soup_a = BeautifulSoup(response_a.text, 'lxml')
            bt_area = soup_a.find_all('div', class_='bt_area')
            if not bt_area:
                continue
            resp_pr = 0
            PHPID = self.get_uri(soup_a)
            headers = {'cookie': 'PHPSESSID='f'{self.r_str()}'}
            payload = {'RequestUri': PHPID}
            while bt_area[-1].text == 'Показать еще события' or resp_pr > 0:
                for bt in bt_area[:-1]:
                    resp_bt = await self.session.get(url + bt.find('a', class_='btn').get('href'))
                    soup = BeautifulSoup(resp_bt.text, 'lxml')
                    name = soup.find('h1').get_text()
                    edate = self.get_edate(soup)
                    scene = soup.find('a', {'id': 'StageMapImage55'}).get('title')
                    link = [
                        name,
                        url + bt.find('a', class_='btn').get('href'),
                        edate,
                        scene,
                        venue
                    ]
                    links.append(link)
                url_p = 'https://www.tickets-star.com/Scripts/LoadMoreRepertoire.script.php'
                url_pr = 'https://www.tickets-star.com/Scripts/LoadMoreRepertoireNextCount.script.php'
                resp_p = await self.session.post(url_p, data=payload, headers=headers)
                resp_pr = await self.session.post(url_pr, data=payload, headers=headers).text
                resp_pr = int(resp_pr)
                soup_p = BeautifulSoup(resp_p.text, 'lxml')
                bt_area = soup_p.find_all('div', class_='bt_area')
                if not bt_area:
                    break

            for bt in bt_area:
                resp_bt2 = await self.session.get(url + bt.find('a', class_='btn').get('href'))
                soup2 = BeautifulSoup(resp_bt2.text, 'lxml')
                name2 = soup2.find('h1').get_text()
                edate2 = self.get_edate(soup2)
                scene2 = soup2.find('a', {'id': 'StageMapImage55'}).get('title')
                link = [
                    name2,
                    url + bt.find('a', class_='btn').get('href'),
                    edate2,
                    scene2,
                    venue
                ]
                links.append(link)
        return links

    async def body(self):
        for link in await self.get_links_events():
            self.register_event(link[0], link[1], date=link[2], scene=link[3], venue=link[4])


circus_urls = [
    '/cat/245/EventId/226454632/',
    '/cat/245/EventId/226450304/',
    '/cat/245/EventId/229446385/',
    '/cat/245/EventId/226557963/',
    '/cat/245/EventId/228720926/',
    '/cat/245/EventId/226557958/',
    '/cat/245/EventId/226557960/',
    '/cat/245/EventId/226450307/',
    '/cat/245/EventId/226975299/',
    '/cat/245/EventId/226022169/',
    '/cat/245/EventId/226454631/',
    '/cat/245/EventId/226557965/',
    '/cat/245/EventId/229367267/',
    '/cat/245/EventId/226441696/',
    '/cat/245/EventId/228178529/',
    '/cat/245/EventId/228145795/',
    '/cat/245/EventId/226355233/',
    '/cat/245/EventId/226022170/',
    '/cat/245/EventId/226026351/',
    '/cat/245/EventId/226355237/',
    '/cat/245/EventId/226355238/',
    '/cat/245/EventId/226359512/',
    '/cat/245/EventId/230564392/',
    '/cat/245/EventId/226022155/',
    '/cat/245/EventId/226022157/',
    '/cat/245/EventId/226359516/',
    '/cat/245/EventId/226022171/',
    '/cat/245/EventId/226022158/',
    '/cat/245/EventId/226022174/',
    '/cat/245/EventId/226359520/',
    '/cat/245/EventId/226022176/',
    '/cat/245/EventId/226022159/',
    '/cat/245/EventId/226022161/',
    '/cat/245/EventId/226359525/',
    '/cat/245/EventId/226026352/',
    '/cat/245/EventId/226022177/',
    '/cat/245/EventId/226022179/',
    '/cat/245/EventId/226359530/',
    '/cat/245/EventId/229969210/',
    '/cat/245/EventId/226022163/',
    '/cat/245/EventId/226022166/',
    '/cat/245/EventId/226359534/',
    '/cat/245/EventId/230564389/',
    '/cat/245/EventId/226026347/',
    '/cat/245/EventId/226026349/',
    '/cat/245/EventId/226359539/',
    '/cat/245/EventId/230564382/',
    '/cat/245/EventId/226359540/',
    '/cat/245/EventId/226359542/',
    '/cat/245/EventId/230564381/',
    '/cat/245/EventId/231388671/',
    '/cat/245/EventId/231781598/',
    '/cat/245/EventId/231781601/',
    '/cat/245/EventId/231781603/'
]
