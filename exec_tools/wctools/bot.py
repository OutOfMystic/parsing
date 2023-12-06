import time
import zipfile
from tempfile import TemporaryDirectory

import datetime as dt
import requests
from parse_module.manager import user_agent
from parse_module.utils import utils, parse_utils, provision

LOGIN = 'vi3sa@ya.ru'
PASSWORD = 'Vlad12315914&'
EPOCH_MINSTAMP = 27924300
EPOCH_DT = dt.datetime(year=2023, month=2, day=4)
PACK_SIZE = 3


class WCSession(requests.Session):
    def __init__(self):
        super().__init__()
        self._token = None
        self._organization = None

    def login(self):
        url = 'https://api2.workcomposer.com/security/login'
        data = {
            'username': LOGIN,
            'password': PASSWORD,
            'params': f'{{"username":"{LOGIN}","password":"{PASSWORD}"}}'
        }
        files = params_to_files(data)
        headers = {
            'authority': 'api2.workcomposer.com',
            'method': 'POST',
            'path': '/security/login',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-MY,en;q=0.9',
            'content-length': '404',
            'origin': 'https://www.workcomposer.com',
            'referer': 'https://www.workcomposer.com/',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': user_agent.default
        }
        r = self.post(url, files=files, headers=headers)
        if '"status":1' not in r.text:
            raise RuntimeError(f'WorkComposer login error! Login response:\n{r.text}')
        self._token = r.json()['auth']['token']
        self._organization = r.json()['auth']['_organization']

    def get_screenshots_dir(self, from_date, to_date):
        if self._token is None:
            self.login()
        temp_dir = TemporaryDirectory()
        print(f'Created temp path: {temp_dir.name}')
        from_mins = dt_to_mins(from_date)
        to_mins = dt_to_mins(to_date)

        for from_min in range(from_mins, to_mins, 1440*PACK_SIZE):
            to_min = min(from_min + 1440*PACK_SIZE, to_mins)
            args = (from_min, to_min, temp_dir,)
            provision.multi_try(self._screenshots_pack, name='WC', args=args)
        return temp_dir

    def _screenshots_pack(self, from_mins, to_mins, temp_dir):
        print(f'Getting screenshots from {from_mins} to {to_mins}')
        url = 'https://api2.workcomposer.com/cron-task-instance/create'
        headers = {
            'authority': 'api2.workcomposer.com',
            'method': 'POST',
            'path': '/cron-task-instance/create',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-MY,en;q=0.9',
            'content-length': '404',
            'origin': 'https://www.workcomposer.com',
            'referer': 'https://www.workcomposer.com/',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': user_agent.default
        }
        data = {
            'authToken': self._token,
            'reportName': '/screenshot/download',
            'reportParams': f'{{"authToken":"{self._token}","from":{from_mins},"to":{to_mins},'
                            f'"breakdown":"B-D","tz":"Asia/Bangkok","searchValue":"","team":null}}',
            'params': f'{{"authToken":"{self._token}","reportName":"/screenshot/download",'
                      f'"reportParams":"{{\\"authToken\\":\\"{self._token}\\",\\"from\\":{from_mins},'
                      f'\\"to\\":{to_mins},\\"breakdown\\":\\"B-D\\",\\"tz\\":\\"Asia/Bangkok\\",'
                      f'\\"searchValue\\":\\"\\",\\"team\\":null}}"}}'
        }
        files = params_to_files(data)
        r = requests.post(url, files=files, headers=headers)
        if '"status":1' not in r.text:
            raise RuntimeError(f'Error creating a screenshot task! Task response:\n{r.text}')
        instance_id = r.json()['instanceId']

        try_ = 0
        while not self.retrieve(instance_id):
            try_ += 1
            if try_ == 30:
                raise RuntimeError('Retrieving timeout')
            time.sleep(3)

        url = f'https://api2.workcomposer.com/cron-task-instance/download?' \
              f'authToken={self._token}&instanceId={instance_id}'
        archive = parse_utils.download(url, temp=True)
        with zipfile.ZipFile(archive, 'r') as zip_ref:
            zip_ref.extractall(temp_dir.name)
        archive.close()

    def retrieve(self, instance_id):
        url = 'https://api2.workcomposer.com/cron-task-instance/retrieve'
        headers = {
            'authority': 'api2.workcomposer.com',
            'method': 'POST',
            'path': '/cron-task-instance/retrieve',
            'scheme': 'https',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-MY,en;q=0.9',
            'content-length': '404',
            'origin': 'https://www.workcomposer.com',
            'referer': 'https://www.workcomposer.com/',
            'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': user_agent.default
        }
        data = {
            'authToken': self._token,
            'instanceId': instance_id,
            'params': f'{{"authToken":"{self._token}","instanceId":{instance_id}}}'
        }
        files = params_to_files(data)
        r = requests.post(url, files=files, headers=headers)
        if '"status":1' not in r.text:
            raise RuntimeError(f'Error retrieving a task! Retrieve response:\n{r.text}')
        return r.json()['allInstancesDone']


def params_to_files(params):
    files = {}
    for param, value in params.items():
        files[param] = (None, value)
    return files


def dt_to_mins(datetime):
    delta = datetime - EPOCH_DT
    mins = delta.total_seconds() // 60
    return int(EPOCH_MINSTAMP + mins)


wcsession = WCSession()
