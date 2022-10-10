import json
import requests
from bs4 import BeautifulSoup
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils
from itertools import groupby


class Parser(EventParser):

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 1200
        self.driver_source = None
        self.url = 'https://www.ticketland.ru/teatry/'

    def before_body(self):
        self.session = ProxySession(self)
        self.our_threaters = [
            'lenkom',
            'mkht-im-chekhova',
            'malyy-teatr',
            'teatr-operetty',
            'teatr-imeni-evgeniya-vakhtangova',
            'teatr-naciy'
        ]

    def get_events(self, link):
        l = 0
        achtung = None
        while achtung == None:
            add_link = link + f'LoadBuildingPopularJS/?page={l}&dateStart=0&dateEnd=0&dateRangeCode=default'
            r = self.session.get(add_link, headers={'user-agent': self.user_agent})
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.find_all('div', class_='col')
            utils.blueprint(len(cards))
            achtung = soup.find('p', class_='mb-2')
            for card in cards:
                href = card.find('a', class_='card__image-link').get('href')
                link_ = link.split('w')[0] + self.url.split('/')[2] + href
                for event in self.get_cards(link_):
                    yield event
            l += 1

    def get_cards(self, url):
        response = self.session.get(url, headers={'User-Agent': 'Custom'})
        soup = BeautifulSoup(response.text, 'lxml')
        cards = soup.find_all('article', class_='show-card--active')
        for card in cards:
            dm, year = card.find_all(class_='show-card__dm')
            event_name = card.find('meta')['content']
            day, month = dm.get_text().strip().split(' ')
            year = year.get_text().strip()
            month = month[:3].capitalize()
            time_ = card.find(class_='show-card__t').get_text().strip()
            formatted_date = f'{day} {month} {year} {time_}'
            url = card.find(class_='btn btn--primary')['href']
            url = 'https://www.ticketland.ru' + url
            yield event_name, url, formatted_date

    def get_links_teatrs(self, pagecount):
        links = []
        for p in range(1, int(pagecount) + 1):
            api = self.url + f"?page={p}&tab=all"
            r = self.session.get(api, headers={'user-agent': self.user_agent})
            soup = BeautifulSoup(r.text, 'lxml')
            items = soup.find_all('div', class_='card-search')
            for item in items:
                link_src = item.find('a', class_='card-search__name')
                url_parts = self.url.split('/')
                link = url_parts[0] + '//' + url_parts[2] + link_src.get('href')
                links.append(link)

        our_links = []
        for our_theater in self.our_threaters:
            for link in links:
                if our_theater in link:
                    our_links.append(link)
        return our_links

    def body(self):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-MY,en;q=0.9,ru-RU;q=0.8,ru;q=0.7,en-US;q=0.6',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent
        }
        r = self.session.get(self.url, headers=headers)
        soup = BeautifulSoup(r.text, 'lxml')
        papers = soup.find_all('li', class_='search-pagination__item')
        if papers:
            last_paper = papers[-1]
            pagecount = last_paper.get('data-page-count')
        else:
            pagecount = 1
        for link in self.get_links_teatrs(pagecount):
            print('teatr link', link)
            for event in self.get_events(link):
                print(event)
                self.register_event(event[0], event[1], date=event[2])

