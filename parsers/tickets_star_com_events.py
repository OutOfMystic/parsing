import json
from datetime import datetime
from typing import Union, Any
import secrets
import string
import requests
from bs4 import BeautifulSoup, PageElement
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.instances import ProxySession
from parse_module.utils import utils
from itertools import groupby
import re
import timestring

class Parser(EventParser):

    def __init__(self, controller):
        super().__init__(controller)
        self.delay = 180
        self.driver_source = None
        self.url = 'https://www.tickets-star.com/cat/176/CategoryId/2/'

    def before_body(self):
        self.session = ProxySession(self)

    def r_str(self):
        letters_and_digits = string.ascii_letters + string.digits
        crypt_rand_string = ''.join(secrets.choice(
            letters_and_digits) for i in range(16))
        return (crypt_rand_string)

    def get_edate(self,soup):
        mydate = soup.find('div',class_='date_an_s').get_text()
        mydate = mydate.split(',')[0]+mydate.split(',')[2]
        day, month, y, t = mydate.strip().split(' ')
        if len(day) == 1:
            day = '0' + day
        month = month[:3].capitalize()
        f_d = f'{day} {month} {y} {t}'
        return(f_d)

    def get_uri(self,soup):
        teg_script = soup.find_all('script')
        uri = teg_script[18]
        pattern = re.compile("(\w+): '(.*?)'")
        fields = dict(re.findall(pattern, uri.text))
        p_id = fields['data'].split('=')[1]
        return p_id

    def get_links_events(self):
        response=self.session.get(self.url, headers={'user-agent': self.user_agent})
        soup=BeautifulSoup(response.text,'lxml')
        afishes=soup.find_all('a',class_='btn')
        links=[]
        url='https://www.tickets-star.com'
        for afisha in afishes:
            response_a = self.session.get(url+afisha.get('href'))
            soup_a=BeautifulSoup(response_a.text,'lxml')
            bt_area=soup_a.find_all('div',class_='bt_area')
            if not bt_area:
                continue
            resp_pr=0
            PHPID=self.get_uri(soup_a)
            headers = {'cookie': 'PHPSESSID='f'{self.r_str()}'}
            payload = {'RequestUri':PHPID}
            while bt_area[-1].text=='Показать еще события' or resp_pr>0:
                for bt in bt_area[:-1]:
                    resp_bt=self.session.get(url+bt.find('a',class_='btn').get('href'))
                    soup=BeautifulSoup(resp_bt.text,'lxml')
                    name=soup.find('h1').get_text()
                    edate = self.get_edate(soup)
                    links.append([name,url + bt.find('a', class_='btn').get('href'),edate])
                url_p='https://www.tickets-star.com/Scripts/LoadMoreRepertoire.script.php'
                url_pr='https://www.tickets-star.com/Scripts/LoadMoreRepertoireNextCount.script.php'
                resp_p = self.session.post(url_p,data=payload,headers=headers)
                resp_pr = self.session.post(url_pr,data=payload,headers=headers).text
                resp_pr=int(resp_pr)
                soup_p = BeautifulSoup(resp_p.text,'lxml')
                bt_area = soup_p.find_all('div', class_='bt_area')

            for bt in bt_area:
                resp_bt2 = self.session.get(url + bt.find('a', class_='btn').get('href'))
                soup2 = BeautifulSoup(resp_bt2.text, 'lxml')
                name2=soup2.find('h1').get_text()
                edate2 = self.get_edate(soup2)
                links.append([name2,url + bt.find('a', class_='btn').get('href'),edate2])
        return links

    def body(self):
        for link in self.get_links_events():
            self.register_event(link[0],link[1],date=link[2])
