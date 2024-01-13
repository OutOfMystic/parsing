import json
from asyncio import sleep

from bs4 import BeautifulSoup
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException
from parse_module.coroutines.parser import AsyncEventParser

from parse_module.manager.proxy.check import NormalConditions
from parse_module.models.parser import EventParser
from parse_module.manager.proxy.sessions import AsyncProxySession, ProxySession
from parse_module.coroutines import AsyncEventParser


class Check_new_websites(AsyncEventParser):
    '''
        Check new domen from ip 179.43.166.54
    '''
    proxy_check = NormalConditions()

    def __init__(self, controller, name):
        super().__init__(controller, name)
        self.delay = 8600
        self.driver_source = None
        self.ip = '179.43.166.54'
        self.BOT_TOKEN = '6002068146:AAHx8JmyW3QhhFK5hhdFIvTXs3XFlsWNraw'
        self.bot = TeleBot(self.BOT_TOKEN)
        self.chat_id =  '-1001982695540'

    async def before_body(self):
        self.session = AsyncProxySession(self)

    @staticmethod
    def reformat_url(box_urls):
        a_sites = set()
        substring = ["widget-frame", "jswidget", "widget-api"]
        for url in box_urls:
            if any([string in url for string in substring]):
                url = url.split('.', 1)[-1]
            a_sites.add(url)
        return sorted(list(a_sites))

    async def seo_auditor(self, ip):
        url = 'https://tools.seo-auditor.com.ru/tools/ip-site/'
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9,ru;q=0.8",
            "cache-control": "max-age=0",
            "sec-ch-ua": '"Not?A_Brand";v="8", "Chromium";v="108", "Yandex";v="23"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://tools.seo-auditor.com.ru",
            "Referer": "https://tools.seo-auditor.com.ru/ip-site/",
            "User-Agent": self.user_agent,
            "X-Requested-With": "XMLHttpRequest"
        }
        data = {'url': ip}
        res = await self.session.post(url, headers=headers, data=data)
        soup = BeautifulSoup(res.text, 'lxml')

        table = soup.find(id='Domain')
        tbody = table.find('tbody')
        tr = tbody.find_all('tr')
        td_all = [ i.find_all('td')[-1].text for i in tr ]

        all_urls = self.reformat_url(td_all)

        return all_urls
    
    async def find_and_check(self, new_urls):
        with open('files/portal_domens/urls.json', 'r', encoding='utf-8') as file:
            old_urls = json.load(file)
            for num, url in enumerate(new_urls, 1):
                if url not in old_urls:
                    await sleep(3.5)  # you can send only 20 messages in 1 minute
                    message = f'New web site \n{url}\n'
                    try:
                        self.bot.send_message(self.chat_id, message, parse_mode='HTML')
                    except ApiTelegramException as ex:
                        self.error(ex)
                        await sleep(60)
        if len(new_urls) > len(old_urls):                
            with open('files/portal_domens/urls.json', 'w', encoding='utf-8') as file1:
                json.dump(new_urls, file1, indent=4, ensure_ascii=False)

    async def body(self):
        a_urls = await self.seo_auditor(self.ip)
        self.find_and_check(a_urls)

