import os
from tempfile import NamedTemporaryFile

import requests
import codecs


def parse_proxy(proxy):
    proxy_type = 'http'
    if type(proxy).__name__ == 'str':
        proxy_user = ''
        proxy_pass = ''
        if r'://' in proxy:
            proxy_type, proxy = proxy.split(r'://')
        if '@' in proxy:
            proxy, logpass = proxy.split('@')
            proxy_user, proxy_pass = logpass.split(':')
        spl_proxy = proxy.split(':')
        proxy_host = spl_proxy[0]
        proxy_port = int(spl_proxy[1])
    elif len(proxy) == 5:
        proxy_type, proxy_host, proxy_port, proxy_user, proxy_pass = proxy
    elif len(proxy) == 4:
        proxy_host, proxy_port, proxy_user, proxy_pass = proxy
    elif len(proxy) == 3:
        proxy_type, proxy_host, proxy_port = proxy
        proxy_user = ''
        proxy_pass = ''
    elif len(proxy) == 2:
        proxy_host, proxy_port = proxy
        proxy_user = ''
        proxy_pass = ''
    else:
        print('WTF: proxies.json')
        return None
    return proxy_type, proxy_host, proxy_port, proxy_user, proxy_pass


def utf_ignore(str_):
    return str_.encode('cp1251', 'ignore').decode('cp1251', 'ignore')


def double_split(source, lstr, rstr, n=0):
    # Возвращает n-ый эелемент
    SplPage = source.split(lstr, 1)[n + 1]
    SplSplPage = SplPage.split(rstr)[0]
    return SplSplPage


def inclusive_split(source, lstr, rstr, n=0):
    splitted = double_split(source, lstr, rstr, n=n)
    return lstr + splitted + rstr


def lrsplit(source, lstr, rstr, generator=False):
    # Возвращает массив эелементов
    if not lstr in source:
        return []
    cells = source.split(lstr)
    cells.pop(0)
    result = (splitted.split(rstr)[0] for splitted in cells)
    if not generator:
        result = list(result)
    return result


def contains_class(obj, slash='//'):
    xpath = f"{slash}*[contains(@class,'{obj}')]"
    return xpath


def class_names_to_xpath(obj, slash='//'):
    xpath = f"{slash}*[@class='{obj}']"
    return xpath


def html_decode(text):
    return text \
        .replace(u"&amp;", u"&") \
        .replace(u"&quot;", u'"') \
        .replace(u"&#039;", u"'") \
        .replace(u"&lt;", u"<") \
        .replace(u"&gt;", u">")


def download(url, name=None, session=None, save=True, temp=False, **kwargs):
    assert save ^ temp, "Use save or temp keyword arguments, not both of them"
    if save and not temp:
        if not os.path.exists('downloads'):
            os.mkdir('downloads')
    if not session:
        r = requests.get(url, **kwargs)
    else:
        r = session.get(url, **kwargs)
    if not name:
        if 'content-disposition' in r.headers:
            disposition = r.headers['content-disposition']
            disposition += ' '
            name = double_split(disposition, 'filename=', ' ')
            name = name.replace('"', '')
        else:
            name = url.split('/')[-1]
    addition = ''
    name_parts = name.split('.')
    if len(name_parts) > 1:
        format_ = '.' + name_parts.pop()
        name = '.'.join(name_parts)
    else:
        name = name_parts.pop()
        format_ = ''
    if temp:
        fo = NamedTemporaryFile()
        fo.write(r.content)
        return fo
    elif save:
        while os.path.exists(f'downloads\\{addition}{name}{format_}'):
            addition += '#'
        with open(f'downloads\\{addition}{name}{format_}', 'wb+') as f:
            f.write(r.content)
        return r.text
    else:
        return r.content


def decode_unicode_escape(text):
    return codecs.decode(text.encode('UTF-8'), 'unicode-escape')
def get_project_root():
    '''
    Получение main пути проекта
    '''
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_dir, 'requirements.txt')):
        current_dir = os.path.dirname(current_dir)
    return current_dir
