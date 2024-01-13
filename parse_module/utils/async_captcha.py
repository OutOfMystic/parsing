import asyncio
import json
import time

import aiohttp

from parse_module.utils.logger import logger

API_KEY = 'f86fe003c5bc005f93a7516e2973658c'


async def non_selenium_recaptcha(googlekey, url,
                                 print_logs=True, timeout=160,
                                 invisible=False, proxy=None,
                                 user_agent=None):
    start_time = time.time()
    params = {
        'key': API_KEY,
        'method': 'userrecaptcha',
        'googlekey': googlekey,
        'pageurl': url,
        'json': 1
    }
    if invisible:
        params['invisible'] = 1

    if proxy:
        proxy_type = proxy[0].upper()
        proxy_str = f"{proxy[3]}:{proxy[4]}@{proxy[1]}:{proxy[2]}"
        params['proxytype'] = proxy_type
        params['proxy'] = proxy_str

    if user_agent:
        params['userAgent'] = user_agent

    async with aiohttp.ClientSession() as session:
        async with session.post('https://rucaptcha.com/in.php', data=params) as r:
            if print_logs:
                logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
            try:
                response = json.loads(await r.text())
            except:
                raise RuntimeError('Captcha contain error: ' + await r.text())
        status = response['status']
        if status:
            id_ = response['request']
            params = {
                'id': id_,
                'action': 'get',
                'json': '1',
                'key': API_KEY
            }
            await asyncio.sleep(7)
            while (time.time() - start_time) < timeout:
                await asyncio.sleep(5)
                async with session.get('https://rucaptcha.com/res.php', params=params) as r:
                    try:
                        response = json.loads(await r.text())
                    except:
                        raise RuntimeError(f'Captcha error: {await r.text()}')
                status = response['status']
                request = response['request']
                if status:
                    if print_logs:
                        logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
                    return request
                if request != 'CAPCHA_NOT_READY':
                    raise RuntimeError(f'Captcha error: {request}')
        else:
            id_ = response['request']
            raise RuntimeError(f'Captcha init error: {id_}')


async def yandex_smart_captcha(sitekey, url,
                         print_logs=True, timeout=160,
                         invisible=False, proxy=None,
                         user_agent=None, count_error=0):
    start_time = time.time()
    params = {
        'key': API_KEY,
        'method': 'yandex',
        'sitekey': sitekey,
        'pageurl': url,
        'json': 1
    }

    if proxy:
        proxy_type = proxy[0].upper()
        proxy_str = f"{proxy[3]}:{proxy[4]}@{proxy[1]}:{proxy[2]}"
        params['proxytype'] = proxy_type
        params['proxy'] = proxy_str

    if user_agent:
        params['userAgent'] = user_agent

    async with aiohttp.ClientSession() as session:
        async with session.post('https://rucaptcha.com/in.php', data=params) as r:
            if print_logs:
                logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
            try:
                response = json.loads(await r.text())
            except:
                if count_error != 5:
                    return await yandex_smart_captcha(
                        sitekey, url,
                        print_logs, timeout,
                        invisible, proxy,
                        user_agent, count_error=count_error+1
                    )
                raise RuntimeError('Captcha contain error: ' + await r.text())
        status = response['status']
        if status:
            id_ = response['request']
            params = {
                'id': id_,
                'action': 'get',
                'json': '1',
                'key': API_KEY
            }
            await asyncio.sleep(7)
            while (time.time() - start_time) < timeout:
                await asyncio.sleep(5)
                async with session.get('https://rucaptcha.com/res.php', params=params) as r:
                    try:
                        response = json.loads(await r.text())
                    except:
                        if count_error != 5:
                            return await yandex_smart_captcha(
                                sitekey, url,
                                print_logs, timeout,
                                invisible, proxy,
                                user_agent, count_error=count_error+1
                            )
                        raise RuntimeError(f'Captcha error: {r.text}')
                    status = response['status']
                    request = response['request']
                    if status:
                        if print_logs:
                            logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
                        return request
                    if request != 'CAPCHA_NOT_READY':
                        if count_error != 5:
                            return await yandex_smart_captcha(
                                sitekey, url,
                                print_logs, timeout,
                                invisible, proxy,
                                user_agent, count_error=count_error+1
                            )
                        raise RuntimeError(f'Captcha error: {request}')
        else:
            if count_error != 5:
                return await yandex_smart_captcha(
                    sitekey, url,
                    print_logs, timeout,
                    invisible, proxy,
                    user_agent, count_error=count_error+1
                )
            id_ = response['request']
            raise RuntimeError(f'Captcha init error: {id_}')


async def afisha_recaptcha(file,
                           print_logs=True, timeout=160,
                           invisible=False, proxy=None,
                           user_agent=None):
    start_time = time.time()
    params = {
        'key': API_KEY,
        'method': 'post',
        'json': 1
    }
    # if invisible:
    #     params['invisible'] = 1

    if proxy:
        proxy_type = proxy[0].upper()
        proxy_str = f"{proxy[3]}:{proxy[4]}@{proxy[1]}:{proxy[2]}"
        params['proxytype'] = proxy_type
        params['proxy'] = proxy_str

    if user_agent:
        params['userAgent'] = user_agent

    files = {'file': file}
    async with aiohttp.ClientSession() as session:
        async with session.post('https://rucaptcha.com/in.php', files=files, data=params) as r:
            if print_logs:
                logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
            try:
                response = json.loads(await r.text())
            except:
                raise RuntimeError('Captcha contain error: ' + await r.text())
        status = response['status']
        if status:
            id_ = response['request']
            params = {
                'id': id_,
                'action': 'get',
                'json': '1',
                'key': API_KEY
            }
            await asyncio.sleep(7)
            while (time.time() - start_time) < timeout:
                await asyncio.sleep(5)
                async with session.get('https://rucaptcha.com/res.php', params=params) as r:
                    try:
                        response = json.loads(await r.text())
                    except:
                        raise RuntimeError(f'Captcha error: {await r.text()}')
                    status = response['status']
                    request = response['request']
                    if status:
                        if print_logs:
                            logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
                        return request
                    if request != 'CAPCHA_NOT_READY':
                        raise RuntimeError(f'Captcha error: {request}')
        else:
            id_ = response['request']
            raise RuntimeError(f'Captcha init error: {id_}')


async def yandex_afisha_coordinates_captha(image_with_elements, imginstructions, textinstructions,
                                     print_logs=True, timeout=160,
                                     invisible=False, proxy=None,
                                     user_agent=None):
    start_time = time.time()
    params = {
        'key': API_KEY,
        'coordinatescaptcha': 1,
        'method': 'base64',
        'body': image_with_elements,
        'imginstructions': imginstructions,
        'textinstructions': textinstructions,
        'json': 1
    }
    # if invisible:
    #     params['invisible'] = 1

    if proxy:
        proxy_type = proxy[0].upper()
        proxy_str = f"{proxy[3]}:{proxy[4]}@{proxy[1]}:{proxy[2]}"
        params['proxytype'] = proxy_type
        params['proxy'] = proxy_str

    if user_agent:
        params['userAgent'] = user_agent

    async with aiohttp.ClientSession() as session:
        async with session.post('https://rucaptcha.com/in.php', data=params) as r:
            if print_logs:
                logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
            try:
                response = json.loads(await r.text())
            except:
                raise RuntimeError('Captcha contain error: ' + await r.text())
        status = response['status']
        if status:
            id_ = response['request']
            params = {
                'id': id_,
                'action': 'get',
                'json': '1',
                'key': API_KEY
            }
            await asyncio.sleep(7)
            while (time.time() - start_time) < timeout:
                await asyncio.sleep(5)
                async with session.get('https://rucaptcha.com/res.php', params=params) as r:
                    try:
                        response = json.loads(await r.text())
                    except:
                        raise RuntimeError(f'Captcha error: {await r.text()}')
                    status = response['status']
                    request = response['request']
                    if status:
                        if print_logs:
                            logger.info('rucaptcha.com: ' + await r.text(), name='Captcha')
                        return request
                    if request != 'CAPCHA_NOT_READY':
                        raise RuntimeError(f'Captcha error: {request}')
        else:
            id_ = response['request']
            raise RuntimeError(f'Captcha init error: {id_}')
