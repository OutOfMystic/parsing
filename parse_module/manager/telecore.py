import itertools
import os
import time
import json
import random
import threading
from socket import *
from queue import Queue
from typing import Iterable

import telebot

from parse_module.utils import provision
from parse_module.utils.logger import logger


class BotInstance:
    def __init__(self, bot_name, api_key):
        self.bot_name = bot_name
        self.api_key = api_key
        self.telebot = telebot.TeleBot(api_key)


class TeleCore(threading.Thread):

    def __init__(self, profiles_config=None, accordance_config=None,
                 api_key=None, admins=None):
        super().__init__()
        self.__q = Queue()
        self.bots = {}
        if api_key:
            self.add(None, api_key)
        self.tele_profiles = provision.try_open(profiles_config, {}, json_=True)
        self.tele_accordance = provision.try_open(accordance_config, {}, json_=True)
        self.admins = admins if admins else []
        self.start()

    @staticmethod
    def send_to_server(data):
        tcp_socket = socket(AF_INET, SOCK_STREAM)
        tcp_socket.connect(('localhost', 9105))

        data = str.encode(data)
        tcp_socket.send(data)
        tcp_socket.recv(1024)

        tcp_socket.close()

    def _get_bot(self, bot_name):
        if bot_name not in self.bots:
            if bot_name is None:
                raise RuntimeError(f'Specify api_key class example argument '
                                   f'or the bot_name method argument')
            else:
                raise RuntimeError(f'{bot_name} was not added via .add method')
        return self.bots[bot_name]

    def get_tele_ids(self, addresses):
        str_profiles = [address for address in addresses if isinstance(address, str)]
        int_profiles = [address for address in addresses if isinstance(address, int)]
        not_found = [name for name in str_profiles if name not in self.tele_profiles]
        if not_found:
            raise RuntimeError(f'Имена не найдены в TELE_PROFILES: {not_found}')

        id_lists = [self.tele_profiles[profile] for profile in str_profiles]
        id_lists.append(self.admins)
        id_lists.append(int_profiles)
        unique_ids = set(itertools.chain.from_iterable(id_lists))
        return list(unique_ids)

    @staticmethod
    def error(error_message, bot_name):
        message = f'TELEGRAM MESSAGE ERROR on {bot_name}: {error_message}'
        logger.error(message, name='Controller')

    def send_message(self, mes: str, tele_ids: Iterable[int], bot_name: str = None):
        tele_ids = list(tele_ids)
        if tele_ids == self.admins:
            mes = '[Debug mode]\n' + mes
        self.__q.put([mes, tele_ids, bot_name])

    def send_telegram_manually(self, mes, tele_ids, bot_name):
        bot = self.bots[bot_name]
        # print('Notification server is offline! Sending manually...')

        mes_tele_ids = [tele_id for tele_id in tele_ids if tele_id not in self.admins]
        if not mes_tele_ids:
            profiles = ''
        else:
            profiles = '\n['
            for mes_tele_id in mes_tele_ids:
                is_written = False
                for profile, profile_data in self.tele_profiles.items():
                    if mes_tele_id == profile_data[0]:
                        profiles += profile + ', '
                        is_written = True

                if not is_written:
                    profiles += str(mes_tele_id) + ', '
            profiles = profiles[:-2] + ']'

        others_mes = mes
        our_mes = mes + profiles

        for tele_id in tele_ids:
            if tele_id in self.admins:
                mes = our_mes  #
            else:
                mes = others_mes  #
            try:
                bot.telebot.send_message(tele_id, mes, parse_mode="Markdown")
            except Exception as err:
                if 'Forbidden: bot was blocked by the user' in str(err):
                    self.error(f'{tele_id} blocked the bot', bot_name)
                elif 'chat not found' in str(error):
                    self.error(f'{tele_id} did not start chat with the bot', bot_name)
                else:
                    raise RuntimeError('TELEGRAM MESSAGE ERROR ' + str(err))

    def add(self, bot_name, api_key):
        assert bot_name not in self.bots, f'Telebot {bot_name} was already added'
        self.bots[bot_name] = BotInstance(bot_name, api_key)

    def run(self):
        while True:
            to_send = []
            while not self.__q.empty():
                one_message = self.__q.get()
                to_send.append(one_message)
            try:
                data = json.dumps(to_send) + chr(2)
            except Exception as err:
                self.error(f'Error serialising message to JSON ({err})', 'GLOBAL')
                return
            try:
                self.send_to_server(data)
            except:
                for one_message in to_send:
                    try:
                        self.send_telegram_manually(*one_message)
                    except Exception as err:
                        bot_name = one_message[2]
                        self.error(f'Error on sending message to Telegram using two ways: {err}',
                                   bot_name=bot_name)
                    finally:
                        time.sleep(0.1)


if __name__ == '__main__':
    tele_core = TeleCore()
    tele_core.add('notifications', '6002068146:AAHx8JmyW3QhhFK5hhdFIvTXs3XFlsWNraw')
    tele_core.add('bills', '5741231744:AAGHiVougv4uoRia5I_behO9r1oMj1NEMI8')
    for i in range(3):
        test_string = ''.join(str(i % 10) for i in range(random.randint(10, 60)))
        tele_core.send_message(test_string, [454746771], 'notifications')
        tele_core.send_message(test_string + 'bill', [454746771], 'bills')
